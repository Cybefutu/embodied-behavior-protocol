"""Command line interface for the OEBP reference SDK."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Sequence

from .adapters import FixedArmAdapter, MobileManipulatorAdapter
from .compiler import OEBPCompiler
from .conformance import OEBPConformanceSuite
from .runtime import MockRuntime
from .validator import DEFAULT_PHASES, OEBPValidator


COMMANDS = {"validate", "validate-capability", "compile", "run", "conformance"}


def load_json(path: str) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"OEBP document must be a JSON object: {path}")
    return data


def _add_phase_arg(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--phase",
        action="append",
        choices=["schema", "semantic", "execution"],
        dest="phases",
        help="Validation phase to run. May be provided more than once.",
    )


def _default_profile(adapter: str) -> dict[str, Any]:
    if adapter == "mobile-manipulator":
        return MobileManipulatorAdapter().capability_profile()
    return FixedArmAdapter().capability_profile()


def _load_profile(args: argparse.Namespace) -> dict[str, Any]:
    if getattr(args, "capability", None):
        return load_json(args.capability)
    return _default_profile(getattr(args, "adapter", "mock"))


def _invocation_request(behavior: dict[str, Any], profile: dict[str, Any], timeout_ms: int) -> dict[str, Any]:
    parameters = behavior.get("spec", {}).get("parameters", {})
    parameter_names = parameters.keys() if isinstance(parameters, dict) else []
    effector_id = "effector/default"
    effectors = profile.get("spec", {}).get("effectors", [])
    if isinstance(effectors, list) and effectors and isinstance(effectors[0], dict):
        effector_id = str(effectors[0].get("id", effector_id))
    sample_values = {
        "object": "scene/object_01",
        "target": "scene/target_01",
        "effector": effector_id,
    }
    request_input = {
        name: sample_values.get(str(name), f"example/{name}")
        for name in parameter_names
    }
    return {
        "protocol": "oebp",
        "version": "0.1.0",
        "kind": "InvocationRequest",
        "metadata": {
            "id": "org.oebp.cli.invocation",
            "revision": "1.0.0",
            "created_at": "2026-06-16T09:00:00Z",
        },
        "spec": {
            "invocation_id": "cli-invocation-001",
            "behavior_ref": behavior.get("metadata", {}).get("id", ""),
            "capability_profile_ref": profile.get("metadata", {}).get("id", ""),
            "requested_at": "2026-06-16T09:00:00Z",
            "input": request_input,
            "execution_policy": {
                "timeout_ms": timeout_ms,
                "cancellation": "allow",
                "dry_run": True,
                "allow_recovery": True,
                "max_recovery_activations": 1,
                "required_validation_gates": ["schema", "semantic", "capability"],
            },
        },
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="OEBP reference SDK command line interface.")
    parser.add_argument("--root", help="Repository root. Defaults to the installed package root.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate = subparsers.add_parser("validate", help="Validate an OEBP JSON document.")
    validate.add_argument("document", help="Path to an OEBP JSON document.")
    _add_phase_arg(validate)

    validate_capability = subparsers.add_parser(
        "validate-capability",
        help="Validate an OEBP capability profile.",
    )
    validate_capability.add_argument("capability", help="Path to an OEBP capability profile.")
    _add_phase_arg(validate_capability)

    compile_parser = subparsers.add_parser("compile", help="Compile a behavior against a capability profile.")
    compile_parser.add_argument("behavior", help="Path to an OEBP behavior document.")
    compile_parser.add_argument("--capability", required=True, help="Path to an OEBP capability profile.")

    run_parser = subparsers.add_parser("run", help="Run a behavior through the deterministic mock runtime.")
    run_parser.add_argument("behavior", help="Path to an OEBP behavior document.")
    run_parser.add_argument("--capability", help="Optional capability profile. Defaults to the selected adapter profile.")
    run_parser.add_argument(
        "--adapter",
        choices=["mock", "fixed-arm", "mobile-manipulator"],
        default="mock",
        help="Reference adapter profile to use when --capability is omitted.",
    )
    run_parser.add_argument("--timeout-ms", type=int, default=30000)

    conformance = subparsers.add_parser("conformance", help="Run conformance checks.")
    conformance_subparsers = conformance.add_subparsers(dest="conformance_command", required=True)
    conformance_subparsers.add_parser("run", help="Run the deterministic conformance suite.")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    active_argv = list(sys.argv[1:] if argv is None else argv)
    if active_argv and active_argv[0] not in COMMANDS and not active_argv[0].startswith("-"):
        active_argv = ["validate", *active_argv]

    parser = build_parser()
    args = parser.parse_args(active_argv)
    root = Path(args.root) if args.root else None

    if args.command in {"validate", "validate-capability"}:
        document_path = args.document if args.command == "validate" else args.capability
        validator = OEBPValidator(root)
        report = validator.validate_path(document_path, phases=tuple(args.phases or DEFAULT_PHASES))
        print(json.dumps(report.to_dict(), indent=2, ensure_ascii=False))
        return 0 if report.ok else 1

    if args.command == "compile":
        behavior = load_json(args.behavior)
        capability_profile = load_json(args.capability)
        result = OEBPCompiler(OEBPValidator(root)).compile(behavior, capability_profile)
        print(json.dumps(result.to_dict(), indent=2, ensure_ascii=False))
        return 0 if result.ok else 1

    if args.command == "run":
        behavior = load_json(args.behavior)
        capability_profile = _load_profile(args)
        request = _invocation_request(behavior, capability_profile, args.timeout_ms)
        execution = MockRuntime(compiler=OEBPCompiler(OEBPValidator(root)), validator=OEBPValidator(root)).run(
            behavior,
            capability_profile,
            request,
        )
        print(json.dumps(execution.to_dict(), indent=2, ensure_ascii=False))
        return 0 if execution.ok else 1

    if args.command == "conformance" and args.conformance_command == "run":
        report = OEBPConformanceSuite(root or Path.cwd()).run()
        print(json.dumps(report.to_dict(), indent=2, ensure_ascii=False))
        return 0 if report.passed else 1

    parser.error(f"Unsupported command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
