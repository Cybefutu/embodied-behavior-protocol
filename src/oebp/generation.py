"""Offline gates for LLM-assisted OEBP behavior generation."""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
from typing import Any, Mapping

from .compiler import CompilationResult, OEBPCompiler
from .models import Finding
from .runtime import MockRuntime, RuntimeExecution
from .validator import OEBPValidator


GATE_ORDER = ("schema", "semantic", "capability", "mock_runtime", "provenance")
WIRE_VALIDATION_GATES = {"schema", "semantic", "capability", "risk", "mock_runtime", "human_review"}


@dataclass(frozen=True)
class GeneratedBehaviorCandidate:
    document: dict[str, Any]
    source_refs: tuple[str, ...] = ("llm://offline-candidate",)
    model: str = "offline-llm-candidate"
    prompt_template_hash: str = "offline-template"
    seed: int = 0


@dataclass(frozen=True)
class GenerationGateResult:
    candidate: GeneratedBehaviorCandidate
    gate_statuses: dict[str, str]
    findings: tuple[Finding, ...]
    provenance_record: dict[str, Any]
    compilation: CompilationResult | None = None
    runtime_execution: RuntimeExecution | None = None

    @property
    def accepted(self) -> bool:
        return all(self.gate_statuses.get(gate) == "passed" for gate in GATE_ORDER)

    @property
    def execution_allowed(self) -> bool:
        return self.accepted

    def to_dict(self) -> dict[str, Any]:
        return {
            "accepted": self.accepted,
            "execution_allowed": self.execution_allowed,
            "gate_statuses": dict(self.gate_statuses),
            "findings": [finding.to_dict() for finding in self.findings],
            "provenance_record": copy.deepcopy(self.provenance_record),
            "compilation": self.compilation.to_dict() if self.compilation else None,
            "runtime_execution": self.runtime_execution.to_dict() if self.runtime_execution else None,
        }


class LLMGenerationGate:
    def __init__(
        self,
        validator: OEBPValidator | None = None,
        compiler: OEBPCompiler | None = None,
        runtime: MockRuntime | None = None,
    ) -> None:
        self.validator = validator or OEBPValidator()
        self.compiler = compiler or OEBPCompiler()
        self.runtime = runtime or MockRuntime(compiler=self.compiler, validator=self.validator)

    def evaluate_behavior(
        self,
        candidate: GeneratedBehaviorCandidate,
        capability_profile: dict[str, Any],
        invocation_input: Mapping[str, Any] | None = None,
    ) -> GenerationGateResult:
        behavior = copy.deepcopy(candidate.document)
        profile = copy.deepcopy(capability_profile)
        findings: list[Finding] = []
        gate_statuses = {gate: "skipped" for gate in GATE_ORDER}
        compilation: CompilationResult | None = None
        runtime_execution: RuntimeExecution | None = None

        schema_report = self.validator.validate_document(behavior, phases=("schema",))
        findings.extend(schema_report.findings)
        gate_statuses["schema"] = self._status_for_findings(schema_report.findings)

        if gate_statuses["schema"] == "passed":
            semantic_report = self.validator.validate_document(behavior, phases=("semantic",))
            findings.extend(semantic_report.findings)
            gate_statuses["semantic"] = self._status_for_findings(semantic_report.findings)

        if gate_statuses["semantic"] == "passed":
            compilation = self.compiler.compile(behavior, profile)
            findings.extend(compilation.findings)
            gate_statuses["capability"] = "passed" if compilation.ok else "failed"

        if gate_statuses["capability"] == "passed":
            request = self._invocation_request(candidate, behavior, profile, invocation_input or {})
            runtime_execution = self.runtime.run(behavior, profile, request)
            findings.extend(runtime_execution.findings)
            gate_statuses["mock_runtime"] = "passed" if runtime_execution.ok else "failed"

        provenance = self._provenance_record(candidate, behavior, gate_statuses)
        provenance_report = self.validator.validate_document(provenance)
        findings.extend(provenance_report.findings)
        gate_statuses["provenance"] = self._status_for_findings(provenance_report.findings)

        if any(finding.severity in {"error", "fatal"} for finding in findings):
            provenance["spec"]["trust_level"] = "untrusted"

        return GenerationGateResult(
            candidate=candidate,
            gate_statuses=gate_statuses,
            findings=tuple(findings),
            provenance_record=provenance,
            compilation=compilation,
            runtime_execution=runtime_execution,
        )

    def _status_for_findings(self, findings: tuple[Finding, ...] | list[Finding]) -> str:
        return "failed" if any(finding.severity in {"error", "fatal"} for finding in findings) else "passed"

    def _invocation_request(
        self,
        candidate: GeneratedBehaviorCandidate,
        behavior: dict[str, Any],
        capability_profile: dict[str, Any],
        invocation_input: Mapping[str, Any],
    ) -> dict[str, Any]:
        default_input = {
            "object": "scene/generated_object",
            "target": "scene/generated_target",
            "effector": self._default_effector(capability_profile),
        }
        default_input.update(dict(invocation_input))
        behavior_ref = str(behavior.get("metadata", {}).get("id", "generated.behavior"))
        profile_ref = str(capability_profile.get("metadata", {}).get("id", "generated.profile"))
        return {
            "protocol": "oebp",
            "version": "0.1.0",
            "kind": "InvocationRequest",
            "metadata": {
                "id": f"{behavior_ref}.generated.invocation",
                "revision": "1.0.0",
                "created_at": "2026-06-16T09:00:00Z",
            },
            "spec": {
                "invocation_id": f"generated-{candidate.seed}",
                "behavior_ref": behavior_ref,
                "capability_profile_ref": profile_ref,
                "requested_at": "2026-06-16T09:00:00Z",
                "input": default_input,
                "execution_policy": {
                    "timeout_ms": int(behavior.get("spec", {}).get("contract", {}).get("timeout_ms", 30000)),
                    "cancellation": "allow",
                    "dry_run": True,
                    "allow_recovery": True,
                    "max_recovery_activations": 1,
                    "required_validation_gates": ["schema", "semantic", "capability", "mock_runtime"],
                },
                "provenance_ref": f"provenance.{behavior_ref}.{candidate.seed}",
            },
        }

    def _provenance_record(
        self,
        candidate: GeneratedBehaviorCandidate,
        behavior: dict[str, Any],
        gate_statuses: dict[str, str],
    ) -> dict[str, Any]:
        behavior_ref = str(behavior.get("metadata", {}).get("id", "generated.behavior"))
        validation_gates = [
            {
                "gate": gate,
                "status": status,
                "tool": "oebp.LLMGenerationGate",
                "version": "0.1.0",
                "completed_at": "2026-06-16T09:00:00Z",
            }
            for gate, status in gate_statuses.items()
            if gate in WIRE_VALIDATION_GATES
        ]
        trusted = all(gate_statuses.get(gate) == "passed" for gate in ("schema", "semantic", "capability", "mock_runtime"))
        return {
            "protocol": "oebp",
            "version": "0.1.0",
            "kind": "ProvenanceRecord",
            "metadata": {
                "id": f"provenance.{behavior_ref}.{candidate.seed}",
                "revision": "1.0.0",
                "created_at": "2026-06-16T09:00:00Z",
            },
            "spec": {
                "record_id": f"provenance.{behavior_ref}.{candidate.seed}",
                "generator_type": "llm_assisted_simulation",
                "created_at": "2026-06-16T09:00:00Z",
                "source_refs": list(candidate.source_refs),
                "model": candidate.model,
                "prompt_template_hash": candidate.prompt_template_hash,
                "seed": candidate.seed,
                "validator_versions": ["oebp-generation-gate/0.1.0"],
                "validation_gates": validation_gates,
                "human_review": "not_reviewed",
                "trust_level": "validated" if trusted else "untrusted",
            },
        }

    def _default_effector(self, capability_profile: dict[str, Any]) -> str:
        effectors = capability_profile.get("spec", {}).get("effectors", [])
        if isinstance(effectors, list) and effectors and isinstance(effectors[0], dict):
            return str(effectors[0].get("id", "$effector"))
        return "$effector"
