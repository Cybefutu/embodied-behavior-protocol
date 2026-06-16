"""Deterministic mock runtime for OEBP compiled behavior graphs."""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any, Mapping

from .compiler import OEBPCompiler
from .models import Finding
from .validator import OEBPValidator


TERMINAL_TRACE_STATUS = {
    "succeeded": "succeeded",
    "failed": "failed",
    "canceled": "canceled",
    "preempted": "canceled",
    "timeout": "timeout",
    "unsafe": "unsafe",
    "internal_error": "internal_error",
}


@dataclass(frozen=True)
class AdapterOutcome:
    terminal_state: str = "succeeded"
    output: dict[str, Any] = field(default_factory=dict)
    duration_ms: int = 10
    finding_code: str | None = None
    message: str | None = None
    recoverable: bool = False
    metrics: dict[str, float] = field(default_factory=dict)

    @classmethod
    def succeeded(cls, output: Mapping[str, Any] | None = None, duration_ms: int = 10) -> "AdapterOutcome":
        return cls(terminal_state="succeeded", output=dict(output or {"ok": True}), duration_ms=duration_ms)

    @classmethod
    def failed(
        cls,
        code: str = "OEBP_RUNTIME_ADAPTER_FAILED",
        message: str = "Mock adapter reported failure.",
        recoverable: bool = False,
        duration_ms: int = 10,
        output: Mapping[str, Any] | None = None,
    ) -> "AdapterOutcome":
        return cls(
            terminal_state="failed",
            output=dict(output or {}),
            duration_ms=duration_ms,
            finding_code=code,
            message=message,
            recoverable=recoverable,
        )

    @classmethod
    def timed_out(cls, duration_ms: int = 10) -> "AdapterOutcome":
        return cls(
            terminal_state="timeout",
            duration_ms=duration_ms,
            finding_code="OEBP_RUNTIME_TIMEOUT",
            message="Mock adapter exceeded its timeout.",
        )


@dataclass(frozen=True)
class RuntimeControls:
    cancel_at_node_id: str | None = None
    preempt_at_node_id: str | None = None


@dataclass(frozen=True)
class RuntimeExecution:
    accepted: bool
    feedback: tuple[dict[str, Any], ...]
    result: dict[str, Any]
    trace_spans: tuple[dict[str, Any], ...]
    findings: tuple[Finding, ...]

    @property
    def ok(self) -> bool:
        return self.terminal_state == "succeeded"

    @property
    def terminal_state(self) -> str:
        return str(self.result.get("spec", {}).get("terminal_state", "internal_error"))

    def to_dict(self) -> dict[str, Any]:
        return {
            "accepted": self.accepted,
            "ok": self.ok,
            "feedback": copy.deepcopy(list(self.feedback)),
            "result": copy.deepcopy(self.result),
            "trace_spans": copy.deepcopy(list(self.trace_spans)),
            "findings": [finding.to_dict() for finding in self.findings],
        }


@dataclass(frozen=True)
class MockClock:
    start_at: datetime = datetime(2026, 6, 16, 9, 0, tzinfo=UTC)
    elapsed_ms: int = 0

    def copy(self) -> "MockClock":
        return MockClock(start_at=self.start_at, elapsed_ms=self.elapsed_ms)

    def iso_now(self) -> str:
        current = self.start_at + timedelta(milliseconds=self.elapsed_ms)
        return current.isoformat(timespec="milliseconds").replace("+00:00", "Z")

    def advance(self, duration_ms: int) -> "MockClock":
        return MockClock(start_at=self.start_at, elapsed_ms=self.elapsed_ms + max(0, int(duration_ms)))


@dataclass
class _RuntimeState:
    behavior: dict[str, Any]
    capability_profile: dict[str, Any]
    request: dict[str, Any]
    plan_by_node_id: dict[str, Any]
    adapter_queues: dict[str, list[AdapterOutcome]]
    bindings_by_skill: dict[str, list[dict[str, Any]]]
    controls: RuntimeControls
    clock: MockClock
    feedback: list[dict[str, Any]] = field(default_factory=list)
    trace_spans: list[dict[str, Any]] = field(default_factory=list)
    findings: list[Finding] = field(default_factory=list)
    sequence: int = 0
    span_counter: int = 0
    completed_invokes: int = 0
    recovery_activation_count: int = 0
    recovery_succeeded: bool = False

    @property
    def invocation_id(self) -> str:
        return str(self.request.get("spec", {}).get("invocation_id", "invocation"))

    @property
    def behavior_ref(self) -> str:
        return str(self.behavior.get("metadata", {}).get("id", ""))

    @property
    def profile_ref(self) -> str:
        return str(self.capability_profile.get("metadata", {}).get("id", ""))

    @property
    def trace_id(self) -> str:
        return f"trace.{self.invocation_id}"

    @property
    def deadline_ms(self) -> int:
        request_timeout = int(self.request.get("spec", {}).get("execution_policy", {}).get("timeout_ms", 86400000))
        contract_timeout = int(self.behavior.get("spec", {}).get("contract", {}).get("timeout_ms", 86400000))
        return min(request_timeout, contract_timeout)

    @property
    def policy(self) -> dict[str, Any]:
        policy = self.request.get("spec", {}).get("execution_policy", {})
        return policy if isinstance(policy, dict) else {}


@dataclass(frozen=True)
class _NodeResult:
    terminal_state: str
    output: dict[str, Any] = field(default_factory=dict)
    findings: tuple[Finding, ...] = field(default_factory=tuple)
    error_code: str | None = None
    recoverable: bool = False

    @property
    def succeeded(self) -> bool:
        return self.terminal_state == "succeeded"


class MockRuntime:
    def __init__(
        self,
        compiler: OEBPCompiler | None = None,
        validator: OEBPValidator | None = None,
        clock: MockClock | None = None,
        adapter_outcomes: Mapping[str, list[AdapterOutcome]] | None = None,
    ) -> None:
        self.compiler = compiler or OEBPCompiler()
        self.validator = validator or OEBPValidator()
        self.clock = clock or MockClock()
        self.adapter_outcomes = {
            key: tuple(value)
            for key, value in (adapter_outcomes or {}).items()
        }

    def run(
        self,
        behavior: dict[str, Any],
        capability_profile: dict[str, Any],
        request: dict[str, Any],
        controls: RuntimeControls | None = None,
    ) -> RuntimeExecution:
        controls = controls or RuntimeControls()
        request_report = self.validator.validate_document(request, phases=("schema", "semantic", "execution"))
        compile_result = self.compiler.compile(behavior, capability_profile)
        findings = list(request_report.findings) + list(compile_result.findings)
        findings.extend(self._check_request_refs(behavior, capability_profile, request))

        if any(finding.severity in {"error", "fatal"} for finding in findings) or compile_result.plan is None:
            return self._rejected_execution(behavior, capability_profile, request, findings)

        state = _RuntimeState(
            behavior=copy.deepcopy(behavior),
            capability_profile=copy.deepcopy(capability_profile),
            request=copy.deepcopy(request),
            plan_by_node_id={step.node_id: step for step in compile_result.plan.steps},
            adapter_queues={key: list(value) for key, value in self.adapter_outcomes.items()},
            bindings_by_skill=self._bindings_by_skill(capability_profile),
            controls=controls,
            clock=self.clock.copy(),
            findings=findings,
        )
        self._emit_feedback(state, "accepted", message="Invocation accepted.")
        outcome = self._execute_node(state.behavior.get("spec", {}).get("root", {}), state, parent_span_id=None)
        state.findings.extend(outcome.findings)
        terminal_state = outcome.terminal_state
        if terminal_state == "succeeded" and state.clock.elapsed_ms > state.deadline_ms:
            timeout_finding = self._finding(
                "OEBP_RUNTIME_TIMEOUT",
                "/spec/execution_policy/timeout_ms",
                "Invocation exceeded its deadline.",
                {"deadline_ms": state.deadline_ms, "elapsed_ms": state.clock.elapsed_ms},
            )
            state.findings.append(timeout_finding)
            terminal_state = "timeout"

        result = self._result_document(
            state,
            terminal_state=terminal_state,
            output={
                "done": terminal_state == "succeeded",
                "nodes_completed": state.completed_invokes,
                "node_output": outcome.output,
            },
        )
        return RuntimeExecution(
            accepted=True,
            feedback=tuple(state.feedback),
            result=result,
            trace_spans=tuple(state.trace_spans),
            findings=tuple(state.findings),
        )

    def _execute_node(self, node: Any, state: _RuntimeState, parent_span_id: str | None) -> _NodeResult:
        if not isinstance(node, dict):
            return self._failed_node("OEBP_RUNTIME_NODE_TYPE", "Runtime node must be an object.", recoverable=False)

        node_id = str(node.get("node_id", "node"))
        node_type = str(node.get("type", "unknown"))
        if state.clock.elapsed_ms > state.deadline_ms:
            return self._failed_node("OEBP_RUNTIME_TIMEOUT", "Invocation exceeded its deadline.", terminal="timeout")
        control_result = self._apply_controls(node_id, state)
        if control_result is not None:
            span = self._open_span(state, parent_span_id, node_id, f"node.{node_type}", {"controlled": True})
            self._close_span(state, span, TERMINAL_TRACE_STATUS[control_result.terminal_state], control_result.findings)
            return control_result

        span = self._open_span(state, parent_span_id, node_id, f"node.{node_type}", self._node_attributes(node))
        self._emit_feedback(state, "running", current_node_id=node_id, trace_span_refs=[span["span_id"]])

        if node_type == "invoke":
            outcome = self._execute_invoke(node, state)
        elif node_type == "sequence":
            outcome = self._execute_sequence(node, state, span["span_id"])
        elif node_type == "fallback":
            outcome = self._execute_fallback(node, state, span["span_id"])
        elif node_type == "parallel":
            outcome = self._execute_parallel(node, state, span["span_id"])
        elif node_type == "retry":
            outcome = self._execute_retry(node, state, span["span_id"])
        elif node_type == "timeout":
            outcome = self._execute_timeout(node, state, span["span_id"])
        elif node_type == "guard":
            outcome = self._execute_guard(node, state, span["span_id"])
        else:
            outcome = self._failed_node(
                "OEBP_RUNTIME_NODE_TYPE_UNKNOWN",
                f"Unknown runtime node type {node_type}.",
                recoverable=False,
            )

        trace_status = TERMINAL_TRACE_STATUS.get(outcome.terminal_state, "internal_error")
        self._close_span(state, span, trace_status, outcome.findings)
        return outcome

    def _execute_invoke(self, node: dict[str, Any], state: _RuntimeState) -> _NodeResult:
        node_id = str(node["node_id"])
        skill = str(node["skill"])
        if node_id not in state.plan_by_node_id and skill not in state.bindings_by_skill:
            finding = self._finding(
                "OEBP_RUNTIME_ADAPTER_BINDING_MISSING",
                f"/spec/root/{node_id}",
                f"No adapter binding is available for invoked skill {skill}.",
                {"node_id": node_id, "skill": skill},
            )
            return _NodeResult("failed", findings=(finding,), error_code=finding.code, recoverable=False)

        adapter_outcome = self._next_adapter_outcome(state, node_id, skill)
        state.clock = state.clock.advance(adapter_outcome.duration_ms)
        if adapter_outcome.terminal_state == "succeeded":
            state.completed_invokes += 1
            return _NodeResult("succeeded", output={node_id: copy.deepcopy(adapter_outcome.output)})

        finding = self._finding(
            adapter_outcome.finding_code or self._default_runtime_code(adapter_outcome.terminal_state),
            f"/spec/root/{node_id}",
            adapter_outcome.message or f"Mock adapter returned {adapter_outcome.terminal_state}.",
            {
                "node_id": node_id,
                "skill": skill,
                "recoverable": adapter_outcome.recoverable,
            },
        )
        return _NodeResult(
            adapter_outcome.terminal_state,
            output={node_id: copy.deepcopy(adapter_outcome.output)},
            findings=(finding,),
            error_code=finding.code,
            recoverable=adapter_outcome.recoverable,
        )

    def _execute_sequence(self, node: dict[str, Any], state: _RuntimeState, parent_span_id: str) -> _NodeResult:
        merged: dict[str, Any] = {}
        all_findings: list[Finding] = []
        for child in node.get("children", []):
            outcome = self._execute_node(child, state, parent_span_id)
            merged.update(outcome.output)
            all_findings.extend(outcome.findings)
            if not outcome.succeeded:
                if self._try_recovery(outcome, state, parent_span_id):
                    retry_outcome = self._execute_node(child, state, parent_span_id)
                    merged.update(retry_outcome.output)
                    all_findings.extend(retry_outcome.findings)
                    if retry_outcome.succeeded:
                        continue
                    return self._with_findings(retry_outcome, all_findings)
                return self._with_findings(outcome, all_findings)
        return _NodeResult("succeeded", output=merged, findings=tuple(all_findings))

    def _execute_fallback(self, node: dict[str, Any], state: _RuntimeState, parent_span_id: str) -> _NodeResult:
        all_findings: list[Finding] = []
        for child in node.get("children", []):
            outcome = self._execute_node(child, state, parent_span_id)
            all_findings.extend(outcome.findings)
            if outcome.succeeded:
                return _NodeResult("succeeded", output=outcome.output, findings=tuple(all_findings))
            if outcome.terminal_state in {"canceled", "preempted", "timeout", "unsafe", "internal_error"}:
                return self._with_findings(outcome, all_findings)
        return _NodeResult("failed", findings=tuple(all_findings), error_code="OEBP_RUNTIME_FALLBACK_EXHAUSTED")

    def _execute_parallel(self, node: dict[str, Any], state: _RuntimeState, parent_span_id: str) -> _NodeResult:
        success_policy = node.get("success_policy", "all")
        failure_policy = node.get("failure_policy", "any")
        outcomes = [self._execute_node(child, state, parent_span_id) for child in node.get("children", [])]
        merged: dict[str, Any] = {}
        findings: list[Finding] = []
        for outcome in outcomes:
            merged.update(outcome.output)
            findings.extend(outcome.findings)
            if outcome.terminal_state in {"canceled", "preempted", "timeout", "unsafe", "internal_error"}:
                return self._with_findings(outcome, findings)
        successes = sum(1 for outcome in outcomes if outcome.succeeded)
        if success_policy == "any" and successes > 0:
            return _NodeResult("succeeded", output=merged, findings=tuple(findings))
        if success_policy == "all" and successes == len(outcomes):
            return _NodeResult("succeeded", output=merged, findings=tuple(findings))
        if failure_policy == "all" and successes > 0:
            return _NodeResult("succeeded", output=merged, findings=tuple(findings))
        return _NodeResult("failed", output=merged, findings=tuple(findings), error_code="OEBP_RUNTIME_PARALLEL_FAILED")

    def _execute_retry(self, node: dict[str, Any], state: _RuntimeState, parent_span_id: str) -> _NodeResult:
        max_attempts = int(node.get("max_attempts", 1))
        backoff_ms = int(node.get("backoff_ms", 0))
        findings: list[Finding] = []
        last_outcome = _NodeResult("failed", error_code="OEBP_RUNTIME_RETRY_EXHAUSTED")
        for attempt in range(max_attempts):
            outcome = self._execute_node(node.get("child"), state, parent_span_id)
            findings.extend(outcome.findings)
            if outcome.succeeded:
                return _NodeResult("succeeded", output=outcome.output, findings=tuple(findings))
            if outcome.terminal_state in {"canceled", "preempted", "timeout", "unsafe", "internal_error"}:
                return self._with_findings(outcome, findings)
            last_outcome = outcome
            if attempt < max_attempts - 1 and backoff_ms:
                state.clock = state.clock.advance(backoff_ms)
        return self._with_findings(last_outcome, findings)

    def _execute_timeout(self, node: dict[str, Any], state: _RuntimeState, parent_span_id: str) -> _NodeResult:
        start_ms = state.clock.elapsed_ms
        outcome = self._execute_node(node.get("child"), state, parent_span_id)
        elapsed = state.clock.elapsed_ms - start_ms
        if elapsed <= int(node.get("timeout_ms", 0)):
            return outcome
        finding = self._finding(
            "OEBP_RUNTIME_TIMEOUT",
            f"/spec/root/{node.get('node_id', 'timeout')}/timeout_ms",
            "Timeout node exceeded its deadline.",
            {"timeout_ms": int(node.get("timeout_ms", 0)), "elapsed_ms": elapsed},
        )
        return _NodeResult("timeout", output=outcome.output, findings=(*outcome.findings, finding), error_code=finding.code)

    def _execute_guard(self, node: dict[str, Any], state: _RuntimeState, parent_span_id: str) -> _NodeResult:
        if self._evaluate_expression(node.get("condition"), state):
            return self._execute_node(node.get("child"), state, parent_span_id)
        on_false = node.get("on_false", "fail")
        if on_false == "skip":
            return _NodeResult("succeeded", output={str(node.get("node_id", "guard")): {"skipped": True}})
        finding = self._finding(
            "OEBP_RUNTIME_GUARD_FALSE",
            f"/spec/root/{node.get('node_id', 'guard')}/condition",
            "Guard condition evaluated false.",
            {"on_false": on_false},
        )
        return _NodeResult("failed", findings=(finding,), error_code=finding.code)

    def _try_recovery(self, outcome: _NodeResult, state: _RuntimeState, parent_span_id: str) -> bool:
        if not outcome.recoverable or not outcome.error_code or not state.policy.get("allow_recovery", False):
            return False
        policy_limit = int(state.policy.get("max_recovery_activations", 0))
        if state.recovery_activation_count >= policy_limit:
            return False
        for recovery in state.behavior.get("spec", {}).get("recoveries", []):
            if not isinstance(recovery, dict) or outcome.error_code not in recovery.get("on", []):
                continue
            if state.recovery_activation_count >= int(recovery.get("max_activations", 0)):
                return False
            state.recovery_activation_count += 1
            self._emit_feedback(state, "recovering", message=f"Activating recovery for {outcome.error_code}.")
            recovery_result = self._execute_node(recovery.get("behavior"), state, parent_span_id)
            state.findings.extend(recovery_result.findings)
            state.recovery_succeeded = recovery_result.succeeded
            return recovery_result.succeeded
        return False

    def _apply_controls(self, node_id: str, state: _RuntimeState) -> _NodeResult | None:
        if state.controls.preempt_at_node_id == node_id:
            finding = self._finding(
                "OEBP_RUNTIME_PREEMPTED",
                f"/spec/root/{node_id}",
                "Invocation was preempted before executing this node.",
                {"node_id": node_id},
                severity="warning",
            )
            return _NodeResult("preempted", findings=(finding,), error_code=finding.code)
        if state.controls.cancel_at_node_id == node_id:
            if state.policy.get("cancellation") == "deny":
                finding = self._finding(
                    "OEBP_RUNTIME_CANCELLATION_DENIED",
                    "/spec/execution_policy/cancellation",
                    "Cancellation was requested but the invocation policy denies cancellation.",
                    {"node_id": node_id},
                )
                return _NodeResult("failed", findings=(finding,), error_code=finding.code)
            self._emit_feedback(state, "canceling", current_node_id=node_id, message="Cancellation requested.")
            finding = self._finding(
                "OEBP_RUNTIME_CANCELED",
                f"/spec/root/{node_id}",
                "Invocation was canceled before executing this node.",
                {"node_id": node_id},
                severity="warning",
            )
            return _NodeResult("canceled", findings=(finding,), error_code=finding.code)
        return None

    def _next_adapter_outcome(self, state: _RuntimeState, node_id: str, skill: str) -> AdapterOutcome:
        for key in (node_id, skill):
            queue = state.adapter_queues.get(key)
            if queue:
                return queue.pop(0)
        return AdapterOutcome.succeeded()

    def _emit_feedback(
        self,
        state: _RuntimeState,
        runtime_state: str,
        current_node_id: str | None = None,
        message: str | None = None,
        trace_span_refs: list[str] | None = None,
    ) -> None:
        ratio = 0.0
        total_invokes = max(1, self._count_invokes(state.behavior.get("spec", {}).get("root", {})))
        if runtime_state in {"running", "recovering"}:
            ratio = min(1.0, state.completed_invokes / total_invokes)
        document = {
            "protocol": "oebp",
            "version": "0.1.0",
            "kind": "InvocationFeedback",
            "metadata": {
                "id": f"{state.invocation_id}.feedback.{state.sequence}",
                "revision": "1.0.0",
                "created_at": state.clock.iso_now(),
            },
            "spec": {
                "invocation_id": state.invocation_id,
                "sequence": state.sequence,
                "emitted_at": state.clock.iso_now(),
                "state": runtime_state,
                "progress": {
                    "ratio": ratio,
                    "message": message or runtime_state,
                },
            },
        }
        if current_node_id:
            document["spec"]["current_node_id"] = current_node_id
        if trace_span_refs:
            document["spec"]["trace_span_refs"] = list(trace_span_refs)
        state.feedback.append(document)
        state.sequence += 1

    def _open_span(
        self,
        state: _RuntimeState,
        parent_span_id: str | None,
        node_id: str,
        operation: str,
        attributes: Mapping[str, Any],
    ) -> dict[str, Any]:
        state.span_counter += 1
        span_id = f"{state.trace_id}.{state.span_counter:04d}.{node_id}"
        return {
            "span_id": span_id,
            "parent_span_id": parent_span_id,
            "node_id": node_id,
            "operation": operation,
            "started_at": state.clock.iso_now(),
            "start_ms": state.clock.elapsed_ms,
            "attributes": dict(attributes),
        }

    def _close_span(
        self,
        state: _RuntimeState,
        span: dict[str, Any],
        status: str,
        findings: tuple[Finding, ...] = (),
    ) -> None:
        duration_ms = state.clock.elapsed_ms - int(span["start_ms"])
        spec: dict[str, Any] = {
            "trace_id": state.trace_id,
            "span_id": span["span_id"],
            "operation": span["operation"],
            "behavior_ref": state.behavior_ref,
            "node_id": span["node_id"],
            "invocation_id": state.invocation_id,
            "started_at": span["started_at"],
            "ended_at": state.clock.iso_now(),
            "duration_ms": duration_ms,
            "status": status,
            "attributes": dict(span["attributes"]),
            "events": [
                {
                    "name": "started",
                    "timestamp": span["started_at"],
                },
                {
                    "name": "ended",
                    "timestamp": state.clock.iso_now(),
                },
            ],
            "findings": [self._wire_finding(finding) for finding in findings],
        }
        if span["parent_span_id"]:
            spec["parent_span_id"] = span["parent_span_id"]
        state.trace_spans.append(
            {
                "protocol": "oebp",
                "version": "0.1.0",
                "kind": "TraceSpan",
                "metadata": {
                    "id": span["span_id"],
                    "revision": "1.0.0",
                    "created_at": span["started_at"],
                },
                "spec": spec,
            }
        )

    def _result_document(self, state: _RuntimeState, terminal_state: str, output: Mapping[str, Any]) -> dict[str, Any]:
        return {
            "protocol": "oebp",
            "version": "0.1.0",
            "kind": "InvocationResult",
            "metadata": {
                "id": f"{state.invocation_id}.result",
                "revision": "1.0.0",
                "created_at": state.clock.iso_now(),
            },
            "spec": {
                "invocation_id": state.invocation_id,
                "completed_at": state.clock.iso_now(),
                "terminal_state": terminal_state,
                "output": copy.deepcopy(dict(output)),
                "trace_ref": state.trace_id,
                "findings": [self._wire_finding(finding) for finding in state.findings],
                "recovery_summary": {
                    "attempted": state.recovery_activation_count > 0,
                    "activation_count": state.recovery_activation_count,
                    "succeeded": state.recovery_succeeded,
                },
            },
        }

    def _rejected_execution(
        self,
        behavior: dict[str, Any],
        capability_profile: dict[str, Any],
        request: dict[str, Any],
        findings: list[Finding],
    ) -> RuntimeExecution:
        state = _RuntimeState(
            behavior=behavior,
            capability_profile=capability_profile,
            request=request,
            plan_by_node_id={},
            adapter_queues={},
            bindings_by_skill={},
            controls=RuntimeControls(),
            clock=self.clock.copy(),
            findings=findings,
        )
        result = self._result_document(state, terminal_state="failed", output={"done": False})
        return RuntimeExecution(
            accepted=False,
            feedback=(),
            result=result,
            trace_spans=(),
            findings=tuple(findings),
        )

    def _check_request_refs(
        self,
        behavior: dict[str, Any],
        capability_profile: dict[str, Any],
        request: dict[str, Any],
    ) -> list[Finding]:
        findings: list[Finding] = []
        spec = request.get("spec", {}) if isinstance(request.get("spec"), dict) else {}
        if spec.get("behavior_ref") != behavior.get("metadata", {}).get("id"):
            findings.append(
                self._finding(
                    "OEBP_RUNTIME_BEHAVIOR_REF_MISMATCH",
                    "/spec/behavior_ref",
                    "InvocationRequest behavior_ref does not match the supplied behavior.",
                    {"requested": spec.get("behavior_ref"), "actual": behavior.get("metadata", {}).get("id")},
                )
            )
        if spec.get("capability_profile_ref") != capability_profile.get("metadata", {}).get("id"):
            findings.append(
                self._finding(
                    "OEBP_RUNTIME_CAPABILITY_PROFILE_REF_MISMATCH",
                    "/spec/capability_profile_ref",
                    "InvocationRequest capability_profile_ref does not match the supplied capability profile.",
                    {
                        "requested": spec.get("capability_profile_ref"),
                        "actual": capability_profile.get("metadata", {}).get("id"),
                    },
                )
            )
        return findings

    def _bindings_by_skill(self, capability_profile: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
        bindings: dict[str, list[dict[str, Any]]] = {}
        for binding in capability_profile.get("spec", {}).get("adapter_bindings", []):
            if isinstance(binding, dict) and isinstance(binding.get("skill"), str):
                bindings.setdefault(str(binding["skill"]), []).append(binding)
        return bindings

    def _evaluate_expression(self, expression: Any, state: _RuntimeState) -> bool:
        if not isinstance(expression, dict):
            return False
        op = expression.get("op")
        if op == "all":
            return all(self._evaluate_expression(arg, state) for arg in expression.get("args", []))
        if op == "any":
            return any(self._evaluate_expression(arg, state) for arg in expression.get("args", []))
        if op == "not":
            return not self._evaluate_expression(expression.get("arg"), state)
        if op == "exists":
            path = str(expression.get("path", ""))
            if path.startswith("$"):
                return path[1:] in state.request.get("spec", {}).get("input", {})
            return bool(path)
        if op == "predicate":
            predicates = state.request.get("spec", {}).get("input", {}).get("predicates", {})
            if isinstance(predicates, dict) and expression.get("name") in predicates:
                return bool(predicates[expression.get("name")])
            return True
        return False

    def _count_invokes(self, node: Any) -> int:
        if not isinstance(node, dict):
            return 0
        count = 1 if node.get("type") == "invoke" else 0
        if "child" in node:
            count += self._count_invokes(node["child"])
        for child in node.get("children", []) if isinstance(node.get("children"), list) else []:
            count += self._count_invokes(child)
        return count

    def _node_attributes(self, node: dict[str, Any]) -> dict[str, Any]:
        attributes: dict[str, Any] = {"node_type": str(node.get("type", "unknown"))}
        if "skill" in node:
            attributes["skill"] = str(node["skill"])
        if "resources" in node:
            attributes["resources"] = list(node.get("resources", []))
        return attributes

    def _wire_finding(self, finding: Finding) -> dict[str, Any]:
        result: dict[str, Any] = {
            "severity": finding.severity,
            "code": finding.code,
            "message": finding.message,
        }
        if finding.pointer:
            result["pointer"] = finding.pointer
        if finding.context:
            result["context"] = dict(finding.context)
        if finding.remediation:
            result["remediation"] = finding.remediation
        return result

    def _finding(
        self,
        code: str,
        pointer: str,
        message: str,
        context: Mapping[str, Any] | None = None,
        severity: str = "error",
    ) -> Finding:
        return Finding(
            severity=severity,
            code=code,
            pointer=pointer,
            message=message,
            phase="runtime",
            context=dict(context or {}),
            remediation="Inspect the runtime trace and adapter outcome.",
        )

    def _failed_node(
        self,
        code: str,
        message: str,
        terminal: str = "failed",
        recoverable: bool = False,
    ) -> _NodeResult:
        finding = self._finding(code, "/spec/root", message, {"recoverable": recoverable})
        return _NodeResult(terminal, findings=(finding,), error_code=code, recoverable=recoverable)

    def _with_findings(self, outcome: _NodeResult, findings: list[Finding]) -> _NodeResult:
        return _NodeResult(
            terminal_state=outcome.terminal_state,
            output=outcome.output,
            findings=tuple(findings),
            error_code=outcome.error_code,
            recoverable=outcome.recoverable,
        )

    def _default_runtime_code(self, terminal_state: str) -> str:
        if terminal_state == "timeout":
            return "OEBP_RUNTIME_TIMEOUT"
        if terminal_state == "unsafe":
            return "OEBP_RUNTIME_UNSAFE"
        if terminal_state == "internal_error":
            return "OEBP_RUNTIME_INTERNAL_ERROR"
        return "OEBP_RUNTIME_ADAPTER_FAILED"
