"""Deterministic capability matcher and compiler for OEBP behavior graphs."""

from __future__ import annotations

import copy
import json
from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping

from .models import Finding
from .validator import OEBPValidator


IMPLEMENTATION_PRIORITY = {
    "local_function": 0,
    "motion_planner": 1,
    "ros2_action": 2,
    "grpc_action": 3,
    "behavior_tree": 4,
    "policy_model": 5,
    "vendor_sdk": 6,
    "continuous_action_chunk": 7,
    "action_token_codec": 8,
}


@dataclass(frozen=True)
class AdapterSelection:
    skill: str
    implementation: dict[str, Any]
    parameter_map: dict[str, str]
    result_map: dict[str, str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "skill": self.skill,
            "implementation": copy.deepcopy(self.implementation),
            "parameter_map": dict(self.parameter_map),
            "result_map": dict(self.result_map),
        }


@dataclass(frozen=True)
class CompiledStep:
    node_id: str
    skill: str
    args: dict[str, Any]
    resources: tuple[str, ...]
    adapter: AdapterSelection

    def to_dict(self) -> dict[str, Any]:
        return {
            "node_id": self.node_id,
            "skill": self.skill,
            "args": copy.deepcopy(self.args),
            "resources": list(self.resources),
            "adapter": self.adapter.to_dict(),
        }


@dataclass(frozen=True)
class CompiledPlan:
    behavior_ref: str
    capability_profile_ref: str
    steps: tuple[CompiledStep, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "behavior_ref": self.behavior_ref,
            "capability_profile_ref": self.capability_profile_ref,
            "steps": [step.to_dict() for step in self.steps],
        }


@dataclass(frozen=True)
class CompilationResult:
    plan: CompiledPlan | None
    findings: tuple[Finding, ...] = field(default_factory=tuple)

    @property
    def ok(self) -> bool:
        return self.plan is not None and not any(
            finding.severity in {"error", "fatal"} for finding in self.findings
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "plan": self.plan.to_dict() if self.plan else None,
            "findings": [finding.to_dict() for finding in self.findings],
        }


class CapabilityMatcher:
    def __init__(self, validator: OEBPValidator | None = None) -> None:
        self.validator = validator or OEBPValidator()

    def match(self, behavior: dict[str, Any], capability_profile: dict[str, Any]) -> tuple[Finding, ...]:
        return tuple(self.validator.validate_capability_match(behavior, capability_profile))


class OEBPCompiler:
    def __init__(
        self,
        validator: OEBPValidator | None = None,
        approved_risk_classes: tuple[str, ...] = ("R0", "R1", "R2"),
    ) -> None:
        self.validator = validator or OEBPValidator()
        self.approved_risk_classes = approved_risk_classes

    def compile(self, behavior: dict[str, Any], capability_profile: dict[str, Any]) -> CompilationResult:
        findings: list[Finding] = []
        findings.extend(self.validator.validate_document(behavior).findings)
        findings.extend(self.validator.validate_document(capability_profile).findings)
        findings.extend(self.validator.validate_capability_match(behavior, capability_profile))
        findings.extend(self._validate_pre_execution_constraints(behavior, capability_profile))

        steps: list[CompiledStep] = []
        if not any(finding.severity in {"error", "fatal"} for finding in findings):
            bindings = self._bindings_by_skill(capability_profile)
            for pointer, node in self._iter_invoke_nodes(behavior.get("spec", {}).get("root", {}), "/spec/root"):
                skill = str(node["skill"])
                adapter = self._select_binding(skill, bindings.get(skill, []))
                if adapter is None:
                    findings.append(
                        Finding(
                            severity="error",
                            code="OEBP_COMPILER_ADAPTER_BINDING_MISSING",
                            pointer=f"{pointer}/skill",
                            message=f"No adapter binding is available for invoked skill {skill}.",
                            phase="capability",
                            context={"skill": skill},
                            remediation="Add an adapter binding for the invoked skill.",
                        )
                    )
                    continue
                steps.append(
                    CompiledStep(
                        node_id=str(node["node_id"]),
                        skill=skill,
                        args=copy.deepcopy(node.get("args", {})),
                        resources=tuple(node.get("resources", [])),
                        adapter=adapter,
                    )
                )

        if any(finding.severity in {"error", "fatal"} for finding in findings):
            return CompilationResult(plan=None, findings=tuple(findings))

        plan = CompiledPlan(
            behavior_ref=str(behavior.get("metadata", {}).get("id", "")),
            capability_profile_ref=str(capability_profile.get("metadata", {}).get("id", "")),
            steps=tuple(steps),
        )
        return CompilationResult(plan=plan, findings=tuple(findings))

    def _validate_pre_execution_constraints(
        self,
        behavior: dict[str, Any],
        capability_profile: dict[str, Any],
    ) -> list[Finding]:
        findings: list[Finding] = []
        risk_class = behavior.get("spec", {}).get("requirements", {}).get("risk_class")
        if risk_class not in self.approved_risk_classes:
            findings.append(
                Finding(
                    severity="error",
                    code="OEBP_COMPILER_RISK_REQUIRES_APPROVAL",
                    pointer="/spec/requirements/risk_class",
                    message=f"Risk class {risk_class} is not approved for compilation.",
                    phase="capability",
                    context={"risk_class": risk_class, "approved_risk_classes": list(self.approved_risk_classes)},
                    remediation="Approve the risk class through deployment policy or lower the behavior risk.",
                )
            )
        findings.extend(self._check_graph_bounds(behavior.get("spec", {}).get("root", {}), "/spec/root"))
        findings.extend(self._check_resource_conflicts(behavior.get("spec", {}).get("root", {}), "/spec/root"))
        findings.extend(self._check_requirement_constraints(behavior, capability_profile))
        return findings

    def _check_graph_bounds(self, node: Any, pointer: str) -> list[Finding]:
        findings: list[Finding] = []
        if not isinstance(node, dict):
            return findings
        if node.get("type") == "retry" and int(node.get("max_attempts", 0)) > 10:
            findings.append(
                Finding(
                    severity="error",
                    code="OEBP_COMPILER_RETRY_BOUND_EXCEEDED",
                    pointer=f"{pointer}/max_attempts",
                    message="Retry max_attempts exceeds the v0.1 bound.",
                    phase="capability",
                    remediation="Set max_attempts to 10 or less.",
                )
            )
        if node.get("type") == "timeout":
            timeout = int(node.get("timeout_ms", 0))
            if timeout < 1 or timeout > 86400000:
                findings.append(
                    Finding(
                        severity="error",
                        code="OEBP_COMPILER_TIMEOUT_INVALID",
                        pointer=f"{pointer}/timeout_ms",
                        message="Timeout must be between 1 ms and 86400000 ms.",
                        phase="capability",
                        context={"timeout_ms": timeout},
                        remediation="Use a bounded positive timeout.",
                    )
                )
        if "child" in node:
            findings.extend(self._check_graph_bounds(node["child"], f"{pointer}/child"))
        for index, child in enumerate(node.get("children", []) if isinstance(node.get("children"), list) else []):
            findings.extend(self._check_graph_bounds(child, f"{pointer}/children/{index}"))
        return findings

    def _check_resource_conflicts(self, node: Any, pointer: str) -> list[Finding]:
        findings: list[Finding] = []
        if not isinstance(node, dict):
            return findings
        if node.get("type") == "parallel":
            seen: dict[str, int] = {}
            for index, child in enumerate(node.get("children", [])):
                for resource in self._resources_for_node(child):
                    if resource in seen:
                        findings.append(
                            Finding(
                                severity="error",
                                code="OEBP_COMPILER_RESOURCE_CONFLICT",
                                pointer=f"{pointer}/children/{index}/resources",
                                message=f"Parallel children require the same resource {resource}.",
                                phase="capability",
                                context={"resource": resource, "first_child": seen[resource], "conflicting_child": index},
                                remediation="Serialize the children or use distinct resources.",
                            )
                        )
                    else:
                        seen[resource] = index
        if "child" in node:
            findings.extend(self._check_resource_conflicts(node["child"], f"{pointer}/child"))
        for index, child in enumerate(node.get("children", []) if isinstance(node.get("children"), list) else []):
            findings.extend(self._check_resource_conflicts(child, f"{pointer}/children/{index}"))
        return findings

    def _check_requirement_constraints(
        self,
        behavior: dict[str, Any],
        capability_profile: dict[str, Any],
    ) -> list[Finding]:
        findings: list[Finding] = []
        profile_caps = {
            capability.get("id"): capability
            for capability in capability_profile.get("spec", {}).get("capabilities", [])
            if isinstance(capability, Mapping)
        }
        for index, requirement in enumerate(behavior.get("spec", {}).get("requirements", {}).get("capabilities", [])):
            if not isinstance(requirement, Mapping):
                continue
            capability_id = requirement.get("id")
            profile_capability = profile_caps.get(capability_id)
            constraints = requirement.get("constraints", {})
            if not isinstance(profile_capability, Mapping) or not isinstance(constraints, Mapping):
                continue
            parameters = profile_capability.get("parameters", {})
            if not isinstance(parameters, Mapping):
                parameters = {}
            for key in ("unit", "frame"):
                if key in constraints and parameters.get(key) != constraints[key]:
                    findings.append(
                        Finding(
                            severity="error",
                            code=f"OEBP_COMPILER_{key.upper()}_CONSTRAINT_MISMATCH",
                            pointer=f"/spec/requirements/capabilities/{index}/constraints/{key}",
                            message=f"Capability {capability_id} does not satisfy required {key} constraint.",
                            phase="capability",
                            context={
                                "capability": capability_id,
                                "required": constraints[key],
                                "actual": parameters.get(key),
                            },
                            remediation=f"Select a capability profile with matching {key} support.",
                        )
                    )
        return findings

    def _bindings_by_skill(self, capability_profile: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
        bindings: dict[str, list[dict[str, Any]]] = {}
        for binding in capability_profile.get("spec", {}).get("adapter_bindings", []):
            if isinstance(binding, dict) and isinstance(binding.get("skill"), str):
                bindings.setdefault(binding["skill"], []).append(binding)
        return bindings

    def _select_binding(self, skill: str, bindings: list[dict[str, Any]]) -> AdapterSelection | None:
        if not bindings:
            return None
        ordered = sorted(bindings, key=self._binding_sort_key)
        selected = ordered[0]
        return AdapterSelection(
            skill=skill,
            implementation=copy.deepcopy(selected["implementation"]),
            parameter_map=dict(selected.get("parameter_map", {})),
            result_map=dict(selected.get("result_map", {})),
        )

    def _binding_sort_key(self, binding: dict[str, Any]) -> tuple[int, str]:
        implementation = binding.get("implementation", {})
        implementation_type = implementation.get("type", "") if isinstance(implementation, dict) else ""
        priority = IMPLEMENTATION_PRIORITY.get(str(implementation_type), 100)
        stable = json.dumps(binding, sort_keys=True, separators=(",", ":"))
        return priority, stable

    def _iter_invoke_nodes(self, node: Any, pointer: str) -> Iterable[tuple[str, dict[str, Any]]]:
        if not isinstance(node, dict):
            return
        if node.get("type") == "invoke":
            yield pointer, node
        if "child" in node:
            yield from self._iter_invoke_nodes(node["child"], f"{pointer}/child")
        for index, child in enumerate(node.get("children", []) if isinstance(node.get("children"), list) else []):
            yield from self._iter_invoke_nodes(child, f"{pointer}/children/{index}")

    def _resources_for_node(self, node: Any) -> set[str]:
        resources: set[str] = set()
        if not isinstance(node, dict):
            return resources
        for resource in node.get("resources", []) if isinstance(node.get("resources"), list) else []:
            resources.add(str(resource))
        if "child" in node:
            resources.update(self._resources_for_node(node["child"]))
        for child in node.get("children", []) if isinstance(node.get("children"), list) else []:
            resources.update(self._resources_for_node(child))
        return resources
