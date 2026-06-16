"""Deterministic conformance suite for the OEBP reference implementation."""

from __future__ import annotations

import copy
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from .adapters import FixedArmAdapter, MobileManipulatorAdapter
from .compiler import OEBPCompiler
from .generation import GeneratedBehaviorCandidate, LLMGenerationGate
from .runtime import AdapterOutcome, MockRuntime, RuntimeControls
from .validator import OEBPValidator


@dataclass(frozen=True)
class ConformanceCheck:
    id: str
    category: str
    passed: bool
    message: str
    evidence: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "category": self.category,
            "passed": self.passed,
            "message": self.message,
            "evidence": dict(self.evidence),
        }


@dataclass(frozen=True)
class ConformanceReport:
    checks: tuple[ConformanceCheck, ...]
    lifecycle_scenarios: int
    failure_recovery_scenarios: int

    @property
    def passed(self) -> bool:
        return all(check.passed for check in self.checks)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": "1.0",
            "passed": self.passed,
            "lifecycle_scenarios": self.lifecycle_scenarios,
            "failure_recovery_scenarios": self.failure_recovery_scenarios,
            "checks": [check.to_dict() for check in self.checks],
        }


class OEBPConformanceSuite:
    def __init__(self, root: Path | None = None) -> None:
        self.root = root or Path(__file__).resolve().parents[2]
        self.validator = OEBPValidator(self.root)
        self.compiler = OEBPCompiler(self.validator)

    def run(self) -> ConformanceReport:
        checks: list[ConformanceCheck] = []
        checks.extend(self._schema_and_semantic_checks())
        checks.extend(self._capability_and_compilation_checks())
        lifecycle_checks = self._lifecycle_checks()
        failure_checks = self._failure_recovery_checks()
        checks.extend(lifecycle_checks)
        checks.extend(failure_checks)
        checks.extend(self._trace_roundtrip_and_provenance_checks())
        return ConformanceReport(
            checks=tuple(checks),
            lifecycle_scenarios=len(lifecycle_checks),
            failure_recovery_scenarios=len(failure_checks),
        )

    def _schema_and_semantic_checks(self) -> list[ConformanceCheck]:
        behavior = self._behavior()
        profile = FixedArmAdapter().capability_profile()
        episode = self._load("datasets/synthetic/v0.1/episodes/pick-place-fixed-arm.episode.json")
        valid = [
            ("schema.behavior", behavior),
            ("schema.profile", profile),
            ("schema.episode", episode),
        ]
        checks = [
            self._check(
                check_id,
                "schema",
                self.validator.validate_document(document).ok,
                "Document validates against its schema.",
                {"kind": document.get("kind")},
            )
            for check_id, document in valid
        ]
        duplicate = copy.deepcopy(behavior)
        duplicate["spec"]["root"]["children"][1]["node_id"] = duplicate["spec"]["root"]["children"][0]["node_id"]
        report = self.validator.validate_document(duplicate)
        checks.append(
            self._check(
                "semantic.duplicate_node_id",
                "semantic-validator",
                "OEBP_SEMANTIC_DUPLICATE_NODE_ID" in {finding.code for finding in report.findings},
                "Semantic validator reports duplicate node ids.",
                {"codes": [finding.code for finding in report.findings]},
            )
        )
        return checks

    def _capability_and_compilation_checks(self) -> list[ConformanceCheck]:
        behavior = self._behavior()
        fixed = FixedArmAdapter().compile(copy.deepcopy(behavior), self.compiler)
        mobile = MobileManipulatorAdapter().compile(copy.deepcopy(behavior), self.compiler)
        unsupported = copy.deepcopy(behavior)
        unsupported["spec"]["requirements"]["capabilities"].append({"id": "oebp.capability.locomotion.navigate"})
        unsupported_fixed = FixedArmAdapter().compile(unsupported, self.compiler)
        return [
            self._check(
                "capability.fixed_arm_compile",
                "capability-matching",
                fixed.ok,
                "Fixed-arm adapter compiles pick-and-place.",
                {"findings": [finding.code for finding in fixed.findings]},
            ),
            self._check(
                "capability.mobile_manipulator_compile",
                "cross-embodiment",
                mobile.ok,
                "Mobile-manipulator adapter compiles pick-and-place.",
                {"findings": [finding.code for finding in mobile.findings]},
            ),
            self._check(
                "capability.unsupported_variation",
                "capability-matching",
                "OEBP_CAPABILITY_MISSING" in {finding.code for finding in unsupported_fixed.findings},
                "Unsupported capability variation fails with a precise code.",
                {"findings": [finding.code for finding in unsupported_fixed.findings]},
            ),
        ]

    def _lifecycle_checks(self) -> list[ConformanceCheck]:
        return [
            self._lifecycle("lifecycle.success_fixed_arm", lambda: self._runtime_result(FixedArmAdapter()).terminal_state == "succeeded"),
            self._lifecycle("lifecycle.success_mobile_manipulator", lambda: self._runtime_result(MobileManipulatorAdapter()).terminal_state == "succeeded"),
            self._lifecycle("lifecycle.cancel_estimate", lambda: self._runtime_result(FixedArmAdapter(), controls=RuntimeControls(cancel_at_node_id="estimate-object-pose")).terminal_state == "canceled"),
            self._lifecycle("lifecycle.cancel_grasp", lambda: self._runtime_result(FixedArmAdapter(), controls=RuntimeControls(cancel_at_node_id="grasp-object")).terminal_state == "canceled"),
            self._lifecycle("lifecycle.preempt_place", lambda: self._runtime_result(FixedArmAdapter(), controls=RuntimeControls(preempt_at_node_id="place-object")).terminal_state == "preempted"),
            self._lifecycle("lifecycle.timeout", lambda: self._runtime_result(FixedArmAdapter(), timeout_ms=5000, outcomes={"estimate-object-pose": [AdapterOutcome.succeeded(duration_ms=6000)]}).terminal_state == "timeout"),
            self._lifecycle("lifecycle.recovery_success", self._recovery_success),
            self._lifecycle("lifecycle.guard_skip", self._guard_skip_success),
            self._lifecycle("lifecycle.fallback_success", self._fallback_success),
            self._lifecycle("lifecycle.parallel_success", self._parallel_success),
        ]

    def _failure_recovery_checks(self) -> list[ConformanceCheck]:
        return [
            self._failure("failure.schema_invalid", self._schema_invalid),
            self._failure("failure.semantic_duplicate_node", self._semantic_duplicate_node),
            self._failure("failure.capability_missing", self._capability_missing),
            self._failure("failure.adapter_binding_missing", self._adapter_binding_missing),
            self._failure("failure.resource_conflict", self._resource_conflict),
            self._failure("failure.risk_rejected", self._risk_rejected),
            self._failure("failure.unit_mismatch", self._unit_mismatch),
            self._failure("failure.runtime_adapter_failed", self._runtime_adapter_failed),
            self._failure("failure.runtime_timeout", self._runtime_timeout),
            self._failure("failure.cancellation_denied", self._cancellation_denied),
            self._failure("failure.recovery_exhausted", self._recovery_exhausted),
        ]

    def _trace_roundtrip_and_provenance_checks(self) -> list[ConformanceCheck]:
        execution = self._runtime_result(FixedArmAdapter())
        behavior_node_ids = set(self._iter_node_ids(self._behavior().get("spec", {}).get("root", {})))
        trace_node_ids = {span["spec"]["node_id"] for span in execution.trace_spans}
        round_trip = json.loads(json.dumps(execution.result, sort_keys=True))
        generation = LLMGenerationGate().evaluate_behavior(
            GeneratedBehaviorCandidate(document=copy.deepcopy(self._behavior()), seed=101),
            FixedArmAdapter().capability_profile(),
        )
        return [
            self._check(
                "trace.node_alignment",
                "trace-alignment",
                behavior_node_ids.issubset(trace_node_ids),
                "Runtime trace spans cover semantic behavior nodes.",
                {"missing": sorted(behavior_node_ids - trace_node_ids)},
            ),
            self._check(
                "json.round_trip_result",
                "json-round-trip",
                round_trip == execution.result,
                "InvocationResult survives deterministic JSON round trip.",
                {"terminal_state": execution.terminal_state},
            ),
            self._check(
                "provenance.generation_gate",
                "provenance",
                generation.accepted and generation.provenance_record["spec"]["trust_level"] == "validated",
                "Generation gate emits validated provenance only after all gates pass.",
                {"gate_statuses": generation.gate_statuses},
            ),
        ]

    def _runtime_result(
        self,
        adapter: FixedArmAdapter | MobileManipulatorAdapter,
        controls: RuntimeControls | None = None,
        timeout_ms: int = 30000,
        outcomes: dict[str, list[AdapterOutcome]] | None = None,
        behavior: dict[str, Any] | None = None,
        cancellation: str = "allow",
    ):
        behavior_doc = copy.deepcopy(behavior or self._behavior())
        profile = adapter.capability_profile()
        request = self._request(behavior_doc, profile, timeout_ms=timeout_ms, cancellation=cancellation)
        return MockRuntime(adapter_outcomes=outcomes).run(behavior_doc, profile, request, controls=controls)

    def _recovery_success(self) -> bool:
        execution = self._runtime_result(
            FixedArmAdapter(),
            outcomes={
                "grasp-object": [
                    AdapterOutcome.failed("oebp.error.manipulation.object_slipped@1", recoverable=True),
                    AdapterOutcome.failed("oebp.error.manipulation.object_slipped@1", recoverable=True),
                    AdapterOutcome.succeeded(),
                ]
            },
        )
        return execution.terminal_state == "succeeded" and execution.result["spec"]["recovery_summary"]["activation_count"] == 1

    def _guard_skip_success(self) -> bool:
        behavior = self._single_wrapper_behavior(
            {
                "type": "guard",
                "node_id": "guard-missing-object",
                "condition": {"op": "exists", "path": "$missing"},
                "on_false": "skip",
                "child": self._invoke("estimate-object-pose", "oebp.skill.perception.estimate_pose@1"),
            }
        )
        return self._runtime_result(FixedArmAdapter(), behavior=behavior).terminal_state == "succeeded"

    def _fallback_success(self) -> bool:
        behavior = self._single_wrapper_behavior(
            {
                "type": "fallback",
                "node_id": "fallback-estimate-or-verify",
                "children": [
                    self._invoke("estimate-object-pose", "oebp.skill.perception.estimate_pose@1"),
                    self._invoke("verify-result", "oebp.skill.meta.verify@1"),
                ],
            }
        )
        execution = self._runtime_result(
            FixedArmAdapter(),
            behavior=behavior,
            outcomes={"estimate-object-pose": [AdapterOutcome.failed()]},
        )
        return execution.terminal_state == "succeeded"

    def _parallel_success(self) -> bool:
        behavior = self._single_wrapper_behavior(
            {
                "type": "parallel",
                "node_id": "parallel-perception-verify",
                "children": [
                    self._invoke("estimate-object-pose", "oebp.skill.perception.estimate_pose@1"),
                    self._invoke("verify-result", "oebp.skill.meta.verify@1"),
                ],
            }
        )
        return self._runtime_result(FixedArmAdapter(), behavior=behavior).terminal_state == "succeeded"

    def _schema_invalid(self) -> bool:
        document = self._behavior()
        document["protocol"] = "bad"
        return "OEBP_SCHEMA_PROTOCOL_CONST" in {finding.code for finding in self.validator.validate_document(document).findings}

    def _semantic_duplicate_node(self) -> bool:
        document = self._behavior()
        document["spec"]["root"]["children"][1]["node_id"] = document["spec"]["root"]["children"][0]["node_id"]
        return "OEBP_SEMANTIC_DUPLICATE_NODE_ID" in {finding.code for finding in self.validator.validate_document(document).findings}

    def _capability_missing(self) -> bool:
        document = self._behavior()
        document["spec"]["requirements"]["capabilities"].append({"id": "oebp.capability.unavailable"})
        return "OEBP_CAPABILITY_MISSING" in {finding.code for finding in FixedArmAdapter().compile(document).findings}

    def _adapter_binding_missing(self) -> bool:
        profile = FixedArmAdapter().capability_profile()
        profile["spec"]["adapter_bindings"] = []
        return "OEBP_COMPILER_ADAPTER_BINDING_MISSING" in {finding.code for finding in self.compiler.compile(self._behavior(), profile).findings}

    def _resource_conflict(self) -> bool:
        document = self._single_wrapper_behavior(
            {
                "type": "parallel",
                "node_id": "parallel-conflict",
                "children": [
                    {**self._invoke("grasp-left", "oebp.skill.manipulation.grasp@1"), "resources": ["arm/gripper"]},
                    {**self._invoke("place-right", "oebp.skill.manipulation.place@1"), "resources": ["arm/gripper"]},
                ],
            }
        )
        return "OEBP_COMPILER_RESOURCE_CONFLICT" in {finding.code for finding in FixedArmAdapter().compile(document).findings}

    def _risk_rejected(self) -> bool:
        document = self._behavior()
        document["spec"]["requirements"]["risk_class"] = "R4"
        return "OEBP_COMPILER_RISK_REQUIRES_APPROVAL" in {finding.code for finding in FixedArmAdapter().compile(document).findings}

    def _unit_mismatch(self) -> bool:
        document = self._behavior()
        document["spec"]["requirements"]["capabilities"][0]["constraints"] = {"unit": "cm"}
        return "OEBP_COMPILER_UNIT_CONSTRAINT_MISMATCH" in {finding.code for finding in FixedArmAdapter().compile(document).findings}

    def _runtime_adapter_failed(self) -> bool:
        execution = self._runtime_result(
            FixedArmAdapter(),
            outcomes={"estimate-object-pose": [AdapterOutcome.failed("OEBP_RUNTIME_TEST_FAILURE")]},
        )
        return execution.terminal_state == "failed"

    def _runtime_timeout(self) -> bool:
        return self._runtime_result(
            FixedArmAdapter(),
            timeout_ms=5000,
            outcomes={"estimate-object-pose": [AdapterOutcome.succeeded(duration_ms=6000)]},
        ).terminal_state == "timeout"

    def _cancellation_denied(self) -> bool:
        execution = self._runtime_result(
            FixedArmAdapter(),
            controls=RuntimeControls(cancel_at_node_id="estimate-object-pose"),
            cancellation="deny",
        )
        return "OEBP_RUNTIME_CANCELLATION_DENIED" in {finding.code for finding in execution.findings}

    def _recovery_exhausted(self) -> bool:
        execution = self._runtime_result(
            FixedArmAdapter(),
            outcomes={
                "grasp-object": [
                    AdapterOutcome.failed("oebp.error.manipulation.object_slipped@1", recoverable=True),
                    AdapterOutcome.failed("oebp.error.manipulation.object_slipped@1", recoverable=True),
                    AdapterOutcome.failed("oebp.error.manipulation.object_slipped@1", recoverable=True),
                    AdapterOutcome.failed("oebp.error.manipulation.object_slipped@1", recoverable=True),
                ]
            },
        )
        return execution.terminal_state == "failed" and execution.result["spec"]["recovery_summary"]["activation_count"] == 1

    def _lifecycle(self, check_id: str, fn: Callable[[], bool]) -> ConformanceCheck:
        category = "cancellation" if ".cancel_" in check_id else "lifecycle"
        return self._call_check(check_id, category, fn)

    def _failure(self, check_id: str, fn: Callable[[], bool]) -> ConformanceCheck:
        category = "failure-recovery"
        if "resource_conflict" in check_id:
            category = "resource-conflict"
        elif "capability_missing" in check_id or "adapter_binding_missing" in check_id:
            category = "capability-matching"
        elif "semantic" in check_id:
            category = "semantic-validator"
        elif "schema" in check_id:
            category = "schema"
        elif "cancellation" in check_id:
            category = "cancellation"
        return self._call_check(check_id, category, fn)

    def _call_check(self, check_id: str, category: str, fn: Callable[[], bool]) -> ConformanceCheck:
        try:
            passed = bool(fn())
            return self._check(check_id, category, passed, "Scenario passed." if passed else "Scenario failed.", {})
        except Exception as exc:  # noqa: BLE001 - conformance report captures failures
            return self._check(check_id, category, False, "Scenario raised an exception.", {"error": str(exc)})

    def _check(
        self,
        check_id: str,
        category: str,
        passed: bool,
        message: str,
        evidence: dict[str, Any],
    ) -> ConformanceCheck:
        return ConformanceCheck(check_id, category, passed, message, evidence)

    def _request(
        self,
        behavior: dict[str, Any],
        profile: dict[str, Any],
        timeout_ms: int = 30000,
        cancellation: str = "allow",
    ) -> dict[str, Any]:
        return {
            "protocol": "oebp",
            "version": "0.1.0",
            "kind": "InvocationRequest",
            "metadata": {"id": "conformance.invocation", "revision": "1.0.0", "created_at": "2026-06-16T09:00:00Z"},
            "spec": {
                "invocation_id": "conformance-invocation",
                "behavior_ref": behavior["metadata"]["id"],
                "capability_profile_ref": profile["metadata"]["id"],
                "requested_at": "2026-06-16T09:00:00Z",
                "input": {"object": "scene/cup", "target": "scene/tray", "effector": profile["spec"]["effectors"][0]["id"]},
                "execution_policy": {
                    "timeout_ms": timeout_ms,
                    "cancellation": cancellation,
                    "dry_run": True,
                    "allow_recovery": True,
                    "max_recovery_activations": 1,
                    "required_validation_gates": ["schema", "semantic", "capability"],
                },
            },
        }

    def _single_wrapper_behavior(self, root: dict[str, Any]) -> dict[str, Any]:
        behavior = self._behavior()
        behavior["spec"]["root"] = root
        return behavior

    def _invoke(self, node_id: str, skill: str) -> dict[str, Any]:
        return {"type": "invoke", "node_id": node_id, "skill": skill, "args": {}}

    def _behavior(self) -> dict[str, Any]:
        return self._load("examples/pick-and-place.behavior.json")

    def _load(self, path: str) -> dict[str, Any]:
        with (self.root / path).open("r", encoding="utf-8") as handle:
            return json.load(handle)

    def _iter_node_ids(self, node: Any):
        if not isinstance(node, dict):
            return
        if isinstance(node.get("node_id"), str):
            yield node["node_id"]
        if "child" in node:
            yield from self._iter_node_ids(node["child"])
        for child in node.get("children", []) if isinstance(node.get("children"), list) else []:
            yield from self._iter_node_ids(child)
