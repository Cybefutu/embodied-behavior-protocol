#!/usr/bin/env python3
"""Check OEBP schema fixtures declared in conformance/fixtures/manifest.json."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from oebp.schema import JsonSchemaSubsetValidator, SchemaStore  # noqa: E402

DEFAULT_MANIFEST = ROOT / "conformance" / "fixtures" / "manifest.json"


@dataclass
class FixtureResult:
    id: str
    path: str
    schema: str
    expected: str
    passed: bool
    message: str
    reason: str
    expected_error_code: str | None


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def validate(schema_rel: str, instance_rel: str) -> tuple[bool, str]:
    schema = SchemaStore(ROOT).load(schema_rel)
    instance = load_json(ROOT / instance_rel)
    issues = JsonSchemaSubsetValidator().validate(schema, instance)
    if issues:
        issue = issues[0]
        return False, f"{instance_rel} failed schema validation: {issue.pointer}: {issue.message}"
    return True, f"{instance_rel} validates against {schema_rel}"


def run_fixture(entry: dict[str, Any], expected: str) -> FixtureResult:
    schema = str(entry["schema"])
    path = str(entry["path"])
    ok, message = validate(schema, path)
    passed = ok if expected == "valid" else not ok
    return FixtureResult(
        id=str(entry["id"]),
        path=path,
        schema=schema,
        expected=expected,
        passed=passed,
        message=message,
        reason=str(entry["reason"]),
        expected_error_code=entry.get("expected_error_code"),
    )


def evaluate_manifest(manifest_path: Path) -> dict[str, Any]:
    manifest = load_json(manifest_path)
    results: list[FixtureResult] = []
    for entry in manifest.get("valid", []):
        results.append(run_fixture(entry, "valid"))
    for entry in manifest.get("invalid", []):
        results.append(run_fixture(entry, "invalid"))

    invalid_count = len(manifest.get("invalid", []))
    valid_count = len(manifest.get("valid", []))
    missing_reasons = [
        str(entry.get("id", "<unknown>"))
        for entry in manifest.get("invalid", [])
        if not str(entry.get("reason", "")).strip()
    ]
    missing_error_codes = [
        str(entry.get("id", "<unknown>"))
        for entry in manifest.get("invalid", [])
        if not str(entry.get("expected_error_code", "")).strip()
    ]
    passed = (
        all(result.passed for result in results)
        and valid_count >= 20
        and invalid_count >= 50
        and not missing_reasons
        and not missing_error_codes
    )
    return {
        "schema_version": "1.0",
        "manifest": str(manifest_path.relative_to(ROOT)),
        "passed": passed,
        "valid_count": valid_count,
        "invalid_count": invalid_count,
        "missing_invalid_reasons": missing_reasons,
        "missing_invalid_error_codes": missing_error_codes,
        "results": [asdict(result) for result in results],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", default=str(DEFAULT_MANIFEST))
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args()

    report = evaluate_manifest(Path(args.manifest))
    if args.as_json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        marker = "PASS" if report["passed"] else "FAIL"
        print(f"[{marker}] {report['manifest']}")
        print(f"Valid fixtures: {report['valid_count']}")
        print(f"Invalid fixtures: {report['invalid_count']}")
        for result in report["results"]:
            result_marker = "PASS" if result["passed"] else "FAIL"
            print(f"[{result_marker}] {result['id']}: {result['message']}")
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
