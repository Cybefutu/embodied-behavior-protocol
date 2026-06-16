#!/usr/bin/env python3
"""Generate the core schema fixture corpus for OEBP v0.1."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
FIXTURE_ROOT = ROOT / "conformance" / "fixtures"
VALID_ROOT = FIXTURE_ROOT / "valid"
INVALID_ROOT = FIXTURE_ROOT / "invalid"
MANIFEST = FIXTURE_ROOT / "manifest.json"


def envelope(kind: str, spec: dict[str, Any], fixture_id: str) -> dict[str, Any]:
    return {
        "protocol": "oebp",
        "version": "0.1.0",
        "kind": kind,
        "metadata": {
            "id": f"org.oebp.fixtures.{fixture_id}",
            "revision": "1.0.0",
            "created_at": "2026-06-16T09:00:00Z",
        },
        "spec": spec,
    }


def expression_exists(path: str = "$object") -> dict[str, Any]:
    return {"op": "exists", "path": path}


def expression_predicate(name: str = "oebp.state.ready", subject: str = "$robot") -> dict[str, Any]:
    return {"op": "predicate", "name": name, "subject": subject}


def minimal_behavior(fixture_id: str = "behavior.minimal") -> dict[str, Any]:
    return envelope(
        "BehaviorSpec",
        {
            "summary": "Minimal schema-valid behavior fixture.",
            "parameters": {},
            "requirements": {"capabilities": [], "risk_class": "R1"},
            "contract": {
                "preconditions": [],
                "invariants": [],
                "success_conditions": [expression_predicate("oebp.state.complete", "$task")],
                "failure_conditions": [],
                "timeout_ms": 1000,
                "cancel_policy": "adapter_defined",
            },
            "root": {
                "type": "invoke",
                "node_id": "noop",
                "skill": "oebp.skill.meta.noop@1",
                "args": {},
            },
        },
        fixture_id,
    )


def fixed_arm_profile(fixture_id: str = "capability.fixed_arm") -> dict[str, Any]:
    return envelope(
        "CapabilityProfile",
        {
            "embodiment_id": "org.oebp.robot.fixture-fixed-arm",
            "embodiment_class": "fixed_manipulator",
            "effectors": [
                {
                    "id": "arm/gripper",
                    "type": "parallel_gripper",
                    "frame": "arm/tool",
                    "max_payload_kg": 2.0,
                    "max_aperture_m": 0.08,
                    "force_feedback": False,
                }
            ],
            "sensors": [{"id": "arm/rgbd", "type": "depth_camera", "frame": "arm/camera", "rate_hz": 30}],
            "frames": [{"id": "world"}, {"id": "arm/base", "parent": "world"}, {"id": "arm/tool", "parent": "arm/base"}],
            "capabilities": [
                {"id": "oebp.capability.manipulation.grasp", "support": "planned", "parameters": {}}
            ],
            "adapter_bindings": [],
        },
        fixture_id,
    )


def skill_contract(fixture_id: str = "skill_contract.grasp") -> dict[str, Any]:
    return envelope(
        "SkillContract",
        {
            "skill": "oebp.skill.manipulation.grasp@1",
            "parameters": {
                "object": {"type": "EntityRef", "required": True},
                "effector": {"type": "EffectorRef", "required": True},
            },
            "preconditions": [expression_exists("$object")],
            "invariants": [expression_predicate("oebp.state.safety_envelope_ok", "$robot")],
            "success_conditions": [expression_predicate("oebp.relation.held_by", "$object")],
            "failure_conditions": [],
            "timeout_ms": 5000,
            "cancel_policy": "reach_safe_state",
            "risk_class": "R2",
        },
        fixture_id,
    )


def context_snapshot(fixture_id: str = "context.basic") -> dict[str, Any]:
    evidence = {
        "source": "fixture.perception",
        "timestamp": "2026-06-16T09:00:00Z",
        "confidence": 0.9,
        "freshness_ms": 100,
    }
    return envelope(
        "ContextSnapshot",
        {
            "snapshot_id": "snapshot-001",
            "observed_at": "2026-06-16T09:00:00Z",
            "robot_ref": "$robot",
            "frame": "world",
            "entities": [
                {"id": "$robot", "type": "robot", "properties": {"ready": True}, "evidence": [evidence]},
                {"id": "$object", "type": "object", "properties": {"mass_kg": 0.2}, "evidence": [evidence]},
            ],
            "relations": [
                {
                    "predicate": "oebp.relation.visible_to",
                    "subject": "$object",
                    "object": "$robot",
                    "evidence": [evidence],
                }
            ],
            "facts": [{"name": "oebp.state.ready", "subject": "$robot", "value": True, "evidence": [evidence]}],
        },
        fixture_id,
    )


def provenance_record(fixture_id: str = "provenance.manual", generator_type: str = "manual_authoring") -> dict[str, Any]:
    return envelope(
        "ProvenanceRecord",
        {
            "record_id": fixture_id,
            "generator_type": generator_type,
            "created_at": "2026-06-16T09:00:00Z",
            "source_refs": ["spec/v0.1/core.md"],
            "validator_versions": ["oebp-fixture-validator/0.1.0"],
            "validation_gates": [
                {"gate": "schema", "status": "passed", "tool": "scripts/check_fixtures.py", "version": "0.1.0"}
            ],
            "human_review": "not_reviewed",
            "trust_level": "untrusted",
        },
        fixture_id,
    )


def trace_span(fixture_id: str = "trace.running", status: str = "running") -> dict[str, Any]:
    spec: dict[str, Any] = {
        "trace_id": "trace-001",
        "span_id": fixture_id,
        "operation": "runtime.invoke",
        "behavior_ref": "org.oebp.fixtures.behavior.minimal",
        "node_id": "noop",
        "invocation_id": "invocation-001",
        "started_at": "2026-06-16T09:00:00Z",
        "status": status,
        "attributes": {"adapter": "mock"},
        "events": [{"name": "accepted", "timestamp": "2026-06-16T09:00:00Z"}],
        "findings": [],
    }
    if status != "running":
        spec["ended_at"] = "2026-06-16T09:00:01Z"
        spec["duration_ms"] = 1000
    if status == "failed":
        spec["findings"] = [{"severity": "error", "code": "OEBP_RUNTIME_FIXTURE_FAILURE", "message": "Fixture failure."}]
    return envelope("TraceSpan", spec, fixture_id)


def invocation_request(fixture_id: str = "invocation.request") -> dict[str, Any]:
    return envelope(
        "InvocationRequest",
        {
            "invocation_id": "invocation-001",
            "behavior_ref": "org.oebp.fixtures.behavior.minimal",
            "capability_profile_ref": "org.oebp.fixtures.capability.fixed_arm",
            "context_ref": "org.oebp.fixtures.context.basic",
            "requested_at": "2026-06-16T09:00:00Z",
            "input": {"object": "$object", "effector": "arm/gripper"},
            "execution_policy": {
                "timeout_ms": 5000,
                "cancellation": "allow",
                "dry_run": True,
                "allow_recovery": True,
                "max_recovery_activations": 1,
                "required_validation_gates": ["schema", "semantic", "capability"],
            },
        },
        fixture_id,
    )


def invocation_feedback(fixture_id: str = "invocation.feedback") -> dict[str, Any]:
    return envelope(
        "InvocationFeedback",
        {
            "invocation_id": "invocation-001",
            "sequence": 1,
            "emitted_at": "2026-06-16T09:00:01Z",
            "state": "running",
            "current_node_id": "noop",
            "progress": {"ratio": 0.5, "message": "Executing fixture node."},
            "metrics": {"elapsed_ms": 1000},
            "trace_span_refs": ["trace.running"],
        },
        fixture_id,
    )


def invocation_result(fixture_id: str = "invocation.result", terminal_state: str = "succeeded") -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    if terminal_state != "succeeded":
        findings.append({"severity": "error", "code": "OEBP_RUNTIME_FIXTURE_FAILURE", "message": "Fixture failure."})
    return envelope(
        "InvocationResult",
        {
            "invocation_id": "invocation-001",
            "completed_at": "2026-06-16T09:00:02Z",
            "terminal_state": terminal_state,
            "output": {"done": terminal_state == "succeeded"},
            "trace_ref": "trace-001",
            "findings": findings,
            "recovery_summary": {"attempted": False, "activation_count": 0, "succeeded": False},
        },
        fixture_id,
    )


def episode_annotation(fixture_id: str = "episode.synthetic") -> dict[str, Any]:
    return envelope(
        "EpisodeAnnotation",
        {
            "episode_id": "episode-001",
            "behavior_ref": "org.oebp.fixtures.behavior.minimal",
            "capability_profile_ref": "org.oebp.fixtures.capability.fixed_arm",
            "source_dataset": "fixture",
            "outcome": "succeeded",
            "trace_ref": "trace-001",
            "observation_ref": "observations/episode-001",
            "action_ref": "actions/episode-001",
            "action_codec": "fixture.none",
            "quality": {"semantic_alignment": 1.0},
            "provenance": {
                "generator_type": "scripted_expert",
                "seed": 1,
                "validator_versions": ["oebp-fixture-validator/0.1.0"],
                "human_review": "not_reviewed",
            },
        },
        fixture_id,
    )


def invalid_copy(base: dict[str, Any], mutator: Any) -> dict[str, Any]:
    item = copy.deepcopy(base)
    mutator(item)
    return item


def remove_path(item: dict[str, Any], path: list[str]) -> None:
    current: Any = item
    for key in path[:-1]:
        current = current[key]
    del current[path[-1]]


def set_path(item: dict[str, Any], path: list[str], value: Any) -> None:
    current: Any = item
    for key in path[:-1]:
        current = current[key]
    current[path[-1]] = value


def too_many_strings(count: int) -> list[str]:
    return [f"item-{index:03d}" for index in range(count)]


def valid_fixtures() -> list[dict[str, Any]]:
    valid_docs = [
        ("valid.protocol.envelope.behavior", "schemas/v0.1/protocol-envelope.schema.json", "conformance/fixtures/valid/protocol-envelope-behavior.json", envelope("BehaviorSpec", {}, "protocol.envelope.behavior")),
        ("valid.protocol.envelope.context", "schemas/v0.1/protocol-envelope.schema.json", "conformance/fixtures/valid/protocol-envelope-context.json", envelope("ContextSnapshot", {}, "protocol.envelope.context")),
        ("valid.predicate.exists", "schemas/v0.1/predicate-expression.schema.json", "conformance/fixtures/valid/predicate-exists.json", envelope("PredicateExpression", expression_exists("$object"), "predicate.exists")),
        ("valid.predicate.predicate", "schemas/v0.1/predicate-expression.schema.json", "conformance/fixtures/valid/predicate-predicate.json", envelope("PredicateExpression", {"op": "predicate", "name": "oebp.state.ready", "subject": "$robot", "value": True}, "predicate.predicate")),
        ("valid.predicate.all", "schemas/v0.1/predicate-expression.schema.json", "conformance/fixtures/valid/predicate-all.json", envelope("PredicateExpression", {"op": "all", "args": [expression_exists("$object"), expression_predicate()]}, "predicate.all")),
        ("valid.predicate.compare", "schemas/v0.1/predicate-expression.schema.json", "conformance/fixtures/valid/predicate-compare.json", envelope("PredicateExpression", {"op": "compare", "left": "$object.mass_kg", "operator": "lt", "right": 1.0}, "predicate.compare")),
        ("valid.skill_contract.grasp", "schemas/v0.1/skill-contract.schema.json", "conformance/fixtures/valid/skill-contract-grasp.json", skill_contract("skill_contract.grasp")),
        ("valid.skill_contract.place", "schemas/v0.1/skill-contract.schema.json", "conformance/fixtures/valid/skill-contract-place.json", skill_contract("skill_contract.place")),
        ("valid.context.basic", "schemas/v0.1/context-snapshot.schema.json", "conformance/fixtures/valid/context-basic.json", context_snapshot("context.basic")),
        ("valid.context.updated", "schemas/v0.1/context-snapshot.schema.json", "conformance/fixtures/valid/context-updated.json", context_snapshot("context.updated")),
        ("valid.provenance.manual", "schemas/v0.1/provenance-record.schema.json", "conformance/fixtures/valid/provenance-manual.json", provenance_record("provenance.manual", "manual_authoring")),
        ("valid.provenance.llm_untrusted", "schemas/v0.1/provenance-record.schema.json", "conformance/fixtures/valid/provenance-llm-untrusted.json", provenance_record("provenance.llm_untrusted", "llm_assisted_simulation")),
        ("valid.trace.running", "schemas/v0.1/trace-span.schema.json", "conformance/fixtures/valid/trace-running.json", trace_span("trace.running", "running")),
        ("valid.trace.failed", "schemas/v0.1/trace-span.schema.json", "conformance/fixtures/valid/trace-failed.json", trace_span("trace.failed", "failed")),
        ("valid.invocation.request", "schemas/v0.1/invocation-request.schema.json", "conformance/fixtures/valid/invocation-request.json", invocation_request("invocation.request")),
        ("valid.invocation.feedback", "schemas/v0.1/invocation-feedback.schema.json", "conformance/fixtures/valid/invocation-feedback.json", invocation_feedback("invocation.feedback")),
        ("valid.invocation.result_succeeded", "schemas/v0.1/invocation-result.schema.json", "conformance/fixtures/valid/invocation-result-succeeded.json", invocation_result("invocation.result_succeeded", "succeeded")),
        ("valid.invocation.result_failed", "schemas/v0.1/invocation-result.schema.json", "conformance/fixtures/valid/invocation-result-failed.json", invocation_result("invocation.result_failed", "failed")),
        ("valid.capability.fixed_arm", "schemas/v0.1/capability-profile.schema.json", "conformance/fixtures/valid/capability-fixed-arm.json", fixed_arm_profile("capability.fixed_arm")),
        ("valid.behavior.minimal", "schemas/v0.1/behavior-spec.schema.json", "conformance/fixtures/valid/behavior-minimal.json", minimal_behavior("behavior.minimal")),
        ("valid.episode.synthetic", "schemas/v0.1/episode-annotation.schema.json", "conformance/fixtures/valid/episode-synthetic.json", episode_annotation("episode.synthetic")),
    ]
    return [
        {"id": fixture_id, "schema": schema, "path": path, "reason": "Generated valid core fixture.", "document": document}
        for fixture_id, schema, path, document in valid_docs
    ]


def invalid_fixtures() -> list[dict[str, Any]]:
    protocol_base = envelope("BehaviorSpec", {}, "protocol.invalid")
    predicate_base = envelope("PredicateExpression", expression_exists("$object"), "predicate.invalid")
    contract_base = skill_contract("skill_contract.invalid")
    context_base = context_snapshot("context.invalid")
    provenance_base = provenance_record("provenance.invalid")
    trace_base = trace_span("trace.invalid", "running")
    request_base = invocation_request("invocation.request.invalid")
    feedback_base = invocation_feedback("invocation.feedback.invalid")
    result_base = invocation_result("invocation.result.invalid", "succeeded")
    behavior_base = minimal_behavior("behavior.invalid")

    cases: list[tuple[str, str, str, str, str, dict[str, Any]]] = [
        ("invalid.protocol.missing_metadata", "schemas/v0.1/protocol-envelope.schema.json", "protocol-missing-metadata.json", "OEBP_SCHEMA_METADATA_REQUIRED", "ProtocolEnvelope requires metadata.", invalid_copy(protocol_base, lambda item: remove_path(item, ["metadata"]))),
        ("invalid.protocol.unknown_kind", "schemas/v0.1/protocol-envelope.schema.json", "protocol-unknown-kind.json", "OEBP_SCHEMA_KIND_ENUM", "ProtocolEnvelope kind must be a known OEBP kind.", invalid_copy(protocol_base, lambda item: set_path(item, ["kind"], "UnknownKind"))),
        ("invalid.protocol.bad_protocol", "schemas/v0.1/protocol-envelope.schema.json", "protocol-bad-protocol.json", "OEBP_SCHEMA_PROTOCOL_CONST", "ProtocolEnvelope protocol must be oebp.", invalid_copy(protocol_base, lambda item: set_path(item, ["protocol"], "other"))),
        ("invalid.protocol.spec_not_object", "schemas/v0.1/protocol-envelope.schema.json", "protocol-spec-not-object.json", "OEBP_SCHEMA_SPEC_TYPE", "ProtocolEnvelope spec must be an object.", invalid_copy(protocol_base, lambda item: set_path(item, ["spec"], []))),
        ("invalid.predicate.missing_op", "schemas/v0.1/predicate-expression.schema.json", "predicate-missing-op.json", "OEBP_SCHEMA_PREDICATE_ONEOF", "PredicateExpression must match one AST form.", invalid_copy(predicate_base, lambda item: remove_path(item, ["spec", "op"]))),
        ("invalid.predicate.all_empty_args", "schemas/v0.1/predicate-expression.schema.json", "predicate-all-empty-args.json", "OEBP_SCHEMA_ARGS_MIN_ITEMS", "Compound predicate args must not be empty.", invalid_copy(predicate_base, lambda item: set_path(item, ["spec"], {"op": "all", "args": []}))),
        ("invalid.predicate.missing_subject", "schemas/v0.1/predicate-expression.schema.json", "predicate-missing-subject.json", "OEBP_SCHEMA_SUBJECT_REQUIRED", "Predicate form requires subject.", invalid_copy(predicate_base, lambda item: set_path(item, ["spec"], {"op": "predicate", "name": "oebp.state.ready"}))),
        ("invalid.predicate.bad_operator", "schemas/v0.1/predicate-expression.schema.json", "predicate-bad-operator.json", "OEBP_SCHEMA_OPERATOR_ENUM", "Compare predicate operator must be enumerated.", invalid_copy(predicate_base, lambda item: set_path(item, ["spec"], {"op": "compare", "left": "$x", "operator": "near", "right": 1}))),
        ("invalid.skill_contract.missing_skill", "schemas/v0.1/skill-contract.schema.json", "skill-contract-missing-skill.json", "OEBP_SCHEMA_SKILL_REQUIRED", "SkillContract requires skill.", invalid_copy(contract_base, lambda item: remove_path(item, ["spec", "skill"]))),
        ("invalid.skill_contract.empty_success", "schemas/v0.1/skill-contract.schema.json", "skill-contract-empty-success.json", "OEBP_SCHEMA_SUCCESS_CONDITIONS_MIN_ITEMS", "SkillContract requires at least one success condition.", invalid_copy(contract_base, lambda item: set_path(item, ["spec", "success_conditions"], []))),
        ("invalid.skill_contract.timeout_zero", "schemas/v0.1/skill-contract.schema.json", "skill-contract-timeout-zero.json", "OEBP_SCHEMA_TIMEOUT_MINIMUM", "SkillContract timeout must be positive.", invalid_copy(contract_base, lambda item: set_path(item, ["spec", "timeout_ms"], 0))),
        ("invalid.skill_contract.bad_cancel_policy", "schemas/v0.1/skill-contract.schema.json", "skill-contract-bad-cancel-policy.json", "OEBP_SCHEMA_CANCEL_POLICY_ENUM", "SkillContract cancel policy must be enumerated.", invalid_copy(contract_base, lambda item: set_path(item, ["spec", "cancel_policy"], "never"))),
        ("invalid.context.missing_entities", "schemas/v0.1/context-snapshot.schema.json", "context-missing-entities.json", "OEBP_SCHEMA_ENTITIES_REQUIRED", "ContextSnapshot requires entities.", invalid_copy(context_base, lambda item: remove_path(item, ["spec", "entities"]))),
        ("invalid.context.entities_empty", "schemas/v0.1/context-snapshot.schema.json", "context-entities-empty.json", "OEBP_SCHEMA_ENTITIES_MIN_ITEMS", "ContextSnapshot requires at least one entity.", invalid_copy(context_base, lambda item: set_path(item, ["spec", "entities"], []))),
        ("invalid.context.entity_missing_type", "schemas/v0.1/context-snapshot.schema.json", "context-entity-missing-type.json", "OEBP_SCHEMA_ENTITY_TYPE_REQUIRED", "Context entity requires type.", invalid_copy(context_base, lambda item: remove_path(item, ["spec", "entities", 0, "type"]))),
        ("invalid.context.relation_missing_subject", "schemas/v0.1/context-snapshot.schema.json", "context-relation-missing-subject.json", "OEBP_SCHEMA_RELATION_SUBJECT_REQUIRED", "Context relation requires subject.", invalid_copy(context_base, lambda item: remove_path(item, ["spec", "relations", 0, "subject"]))),
        ("invalid.provenance.missing_source_refs", "schemas/v0.1/provenance-record.schema.json", "provenance-missing-source-refs.json", "OEBP_SCHEMA_SOURCE_REFS_REQUIRED", "ProvenanceRecord requires source refs.", invalid_copy(provenance_base, lambda item: remove_path(item, ["spec", "source_refs"]))),
        ("invalid.provenance.source_refs_empty", "schemas/v0.1/provenance-record.schema.json", "provenance-source-refs-empty.json", "OEBP_SCHEMA_SOURCE_REFS_MIN_ITEMS", "ProvenanceRecord source refs must not be empty.", invalid_copy(provenance_base, lambda item: set_path(item, ["spec", "source_refs"], []))),
        ("invalid.provenance.bad_trust_level", "schemas/v0.1/provenance-record.schema.json", "provenance-bad-trust-level.json", "OEBP_SCHEMA_TRUST_LEVEL_ENUM", "ProvenanceRecord trust level must be enumerated.", invalid_copy(provenance_base, lambda item: set_path(item, ["spec", "trust_level"], "magic"))),
        ("invalid.provenance.gate_bad_status", "schemas/v0.1/provenance-record.schema.json", "provenance-gate-bad-status.json", "OEBP_SCHEMA_GATE_STATUS_ENUM", "Validation gate status must be enumerated.", invalid_copy(provenance_base, lambda item: set_path(item, ["spec", "validation_gates", 0, "status"], "maybe"))),
        ("invalid.trace.missing_span_id", "schemas/v0.1/trace-span.schema.json", "trace-missing-span-id.json", "OEBP_SCHEMA_SPAN_ID_REQUIRED", "TraceSpan requires span_id.", invalid_copy(trace_base, lambda item: remove_path(item, ["spec", "span_id"]))),
        ("invalid.trace.bad_status", "schemas/v0.1/trace-span.schema.json", "trace-bad-status.json", "OEBP_SCHEMA_TRACE_STATUS_ENUM", "TraceSpan status must be enumerated.", invalid_copy(trace_base, lambda item: set_path(item, ["spec", "status"], "halfway"))),
        ("invalid.trace.event_missing_timestamp", "schemas/v0.1/trace-span.schema.json", "trace-event-missing-timestamp.json", "OEBP_SCHEMA_TRACE_EVENT_TIMESTAMP_REQUIRED", "Trace event requires timestamp.", invalid_copy(trace_base, lambda item: remove_path(item, ["spec", "events", 0, "timestamp"]))),
        ("invalid.trace.finding_missing_code", "schemas/v0.1/trace-span.schema.json", "trace-finding-missing-code.json", "OEBP_SCHEMA_FINDING_CODE_REQUIRED", "Trace finding requires code.", invalid_copy(trace_span("trace.invalid.finding", "failed"), lambda item: remove_path(item, ["spec", "findings", 0, "code"]))),
        ("invalid.invocation_request.missing_execution_policy", "schemas/v0.1/invocation-request.schema.json", "invocation-request-missing-policy.json", "OEBP_SCHEMA_EXECUTION_POLICY_REQUIRED", "InvocationRequest requires execution_policy.", invalid_copy(request_base, lambda item: remove_path(item, ["spec", "execution_policy"]))),
        ("invalid.invocation_request.timeout_zero", "schemas/v0.1/invocation-request.schema.json", "invocation-request-timeout-zero.json", "OEBP_SCHEMA_TIMEOUT_MINIMUM", "InvocationRequest timeout must be positive.", invalid_copy(request_base, lambda item: set_path(item, ["spec", "execution_policy", "timeout_ms"], 0))),
        ("invalid.invocation_request.bad_cancellation", "schemas/v0.1/invocation-request.schema.json", "invocation-request-bad-cancellation.json", "OEBP_SCHEMA_CANCELLATION_ENUM", "InvocationRequest cancellation must be enumerated.", invalid_copy(request_base, lambda item: set_path(item, ["spec", "execution_policy", "cancellation"], "panic"))),
        ("invalid.invocation_request.empty_required_gates", "schemas/v0.1/invocation-request.schema.json", "invocation-request-empty-required-gates.json", "OEBP_SCHEMA_REQUIRED_GATES_MIN_ITEMS", "InvocationRequest required gates must not be empty.", invalid_copy(request_base, lambda item: set_path(item, ["spec", "execution_policy", "required_validation_gates"], []))),
        ("invalid.invocation_feedback.missing_sequence", "schemas/v0.1/invocation-feedback.schema.json", "invocation-feedback-missing-sequence.json", "OEBP_SCHEMA_SEQUENCE_REQUIRED", "InvocationFeedback requires sequence.", invalid_copy(feedback_base, lambda item: remove_path(item, ["spec", "sequence"]))),
        ("invalid.invocation_feedback.sequence_negative", "schemas/v0.1/invocation-feedback.schema.json", "invocation-feedback-sequence-negative.json", "OEBP_SCHEMA_SEQUENCE_MINIMUM", "InvocationFeedback sequence must not be negative.", invalid_copy(feedback_base, lambda item: set_path(item, ["spec", "sequence"], -1))),
        ("invalid.invocation_feedback.bad_state", "schemas/v0.1/invocation-feedback.schema.json", "invocation-feedback-bad-state.json", "OEBP_SCHEMA_FEEDBACK_STATE_ENUM", "InvocationFeedback state must be enumerated.", invalid_copy(feedback_base, lambda item: set_path(item, ["spec", "state"], "paused"))),
        ("invalid.invocation_feedback.too_many_trace_refs", "schemas/v0.1/invocation-feedback.schema.json", "invocation-feedback-too-many-trace-refs.json", "OEBP_SCHEMA_TRACE_REFS_MAX_ITEMS", "InvocationFeedback trace refs are bounded.", invalid_copy(feedback_base, lambda item: set_path(item, ["spec", "trace_span_refs"], too_many_strings(129)))),
        ("invalid.invocation_result.missing_terminal_state", "schemas/v0.1/invocation-result.schema.json", "invocation-result-missing-terminal-state.json", "OEBP_SCHEMA_TERMINAL_STATE_REQUIRED", "InvocationResult requires terminal_state.", invalid_copy(result_base, lambda item: remove_path(item, ["spec", "terminal_state"]))),
        ("invalid.invocation_result.bad_terminal_state", "schemas/v0.1/invocation-result.schema.json", "invocation-result-bad-terminal-state.json", "OEBP_SCHEMA_TERMINAL_STATE_ENUM", "InvocationResult terminal_state must be enumerated.", invalid_copy(result_base, lambda item: set_path(item, ["spec", "terminal_state"], "maybe"))),
        ("invalid.invocation_result.finding_missing_message", "schemas/v0.1/invocation-result.schema.json", "invocation-result-finding-missing-message.json", "OEBP_SCHEMA_FINDING_MESSAGE_REQUIRED", "InvocationResult finding requires message.", invalid_copy(invocation_result("invocation.result.invalid.finding", "failed"), lambda item: remove_path(item, ["spec", "findings", 0, "message"]))),
        ("invalid.invocation_result.activation_count_too_high", "schemas/v0.1/invocation-result.schema.json", "invocation-result-activation-count-too-high.json", "OEBP_SCHEMA_RECOVERY_ACTIVATION_MAXIMUM", "InvocationResult recovery activation count is bounded.", invalid_copy(result_base, lambda item: set_path(item, ["spec", "recovery_summary", "activation_count"], 11))),
        ("invalid.behavior.bad_revision", "schemas/v0.1/behavior-spec.schema.json", "behavior-bad-revision.json", "OEBP_SCHEMA_REVISION_PATTERN", "BehaviorSpec metadata revision must be semver.", invalid_copy(behavior_base, lambda item: set_path(item, ["metadata", "revision"], "one"))),
        ("invalid.behavior.bad_parameter_type", "schemas/v0.1/behavior-spec.schema.json", "behavior-bad-parameter-type.json", "OEBP_SCHEMA_PARAMETER_TYPE_ENUM", "BehaviorSpec parameter type must be enumerated.", invalid_copy(behavior_base, lambda item: set_path(item, ["spec", "parameters"], {"object": {"type": "RobotSoul", "required": True}}))),
        ("invalid.behavior.empty_children", "schemas/v0.1/behavior-spec.schema.json", "behavior-empty-children.json", "OEBP_SCHEMA_CHILDREN_MIN_ITEMS", "BehaviorSpec composite nodes require children.", invalid_copy(behavior_base, lambda item: set_path(item, ["spec", "root"], {"type": "sequence", "node_id": "empty", "children": []}))),
        ("invalid.behavior.duplicate_resources", "schemas/v0.1/behavior-spec.schema.json", "behavior-duplicate-resources.json", "OEBP_SCHEMA_RESOURCES_UNIQUE_ITEMS", "BehaviorSpec node resources must be unique.", invalid_copy(behavior_base, lambda item: set_path(item, ["spec", "root", "resources"], ["arm/gripper", "arm/gripper"]))),
    ]
    return [
        {
            "id": fixture_id,
            "schema": schema,
            "path": f"conformance/fixtures/invalid/{file_name}",
            "reason": reason,
            "expected_error_code": code,
            "document": document,
        }
        for fixture_id, schema, file_name, code, reason, document in cases
    ]


def existing_invalid_entries() -> list[dict[str, str]]:
    return [
        {
            "id": "invalid.behavior.wrong_protocol",
            "schema": "schemas/v0.1/behavior-spec.schema.json",
            "path": "conformance/fixtures/invalid/behavior-wrong-protocol.json",
            "reason": "The protocol field must be the constant string oebp.",
            "expected_error_code": "OEBP_SCHEMA_PROTOCOL_CONST",
        },
        {
            "id": "invalid.behavior.bad_version",
            "schema": "schemas/v0.1/behavior-spec.schema.json",
            "path": "conformance/fixtures/invalid/behavior-bad-version.json",
            "reason": "BehaviorSpec version must match the v0.1 patch-version pattern.",
            "expected_error_code": "OEBP_SCHEMA_VERSION_PATTERN",
        },
        {
            "id": "invalid.behavior.missing_spec",
            "schema": "schemas/v0.1/behavior-spec.schema.json",
            "path": "conformance/fixtures/invalid/behavior-missing-spec.json",
            "reason": "BehaviorSpec requires a top-level spec object.",
            "expected_error_code": "OEBP_SCHEMA_SPEC_REQUIRED",
        },
        {
            "id": "invalid.behavior.empty_success_conditions",
            "schema": "schemas/v0.1/behavior-spec.schema.json",
            "path": "conformance/fixtures/invalid/behavior-empty-success-conditions.json",
            "reason": "Behavior contracts require at least one success condition.",
            "expected_error_code": "OEBP_SCHEMA_SUCCESS_CONDITIONS_MIN_ITEMS",
        },
        {
            "id": "invalid.behavior.retry_too_many_attempts",
            "schema": "schemas/v0.1/behavior-spec.schema.json",
            "path": "conformance/fixtures/invalid/behavior-retry-too-many-attempts.json",
            "reason": "Retry nodes cap max_attempts at 10.",
            "expected_error_code": "OEBP_SCHEMA_RETRY_MAX_ATTEMPTS",
        },
        {
            "id": "invalid.capability.bad_kind",
            "schema": "schemas/v0.1/capability-profile.schema.json",
            "path": "conformance/fixtures/invalid/capability-bad-kind.json",
            "reason": "CapabilityProfile documents must use kind CapabilityProfile.",
            "expected_error_code": "OEBP_SCHEMA_KIND_CONST",
        },
        {
            "id": "invalid.capability.unknown_embodiment_class",
            "schema": "schemas/v0.1/capability-profile.schema.json",
            "path": "conformance/fixtures/invalid/capability-unknown-embodiment-class.json",
            "reason": "Embodiment class must be one of the enumerated schema values.",
            "expected_error_code": "OEBP_SCHEMA_EMBODIMENT_CLASS_ENUM",
        },
        {
            "id": "invalid.capability.empty_capabilities",
            "schema": "schemas/v0.1/capability-profile.schema.json",
            "path": "conformance/fixtures/invalid/capability-empty-capabilities.json",
            "reason": "CapabilityProfile requires at least one capability.",
            "expected_error_code": "OEBP_SCHEMA_CAPABILITIES_MIN_ITEMS",
        },
        {
            "id": "invalid.episode.bad_outcome",
            "schema": "schemas/v0.1/episode-annotation.schema.json",
            "path": "conformance/fixtures/invalid/episode-bad-outcome.json",
            "reason": "Episode outcome must be one of the enumerated values.",
            "expected_error_code": "OEBP_SCHEMA_OUTCOME_ENUM",
        },
        {
            "id": "invalid.episode.missing_provenance_seed",
            "schema": "schemas/v0.1/episode-annotation.schema.json",
            "path": "conformance/fixtures/invalid/episode-missing-provenance-seed.json",
            "reason": "Episode provenance requires a seed.",
            "expected_error_code": "OEBP_SCHEMA_PROVENANCE_SEED_REQUIRED",
        },
    ]


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")


def main() -> int:
    valid_entries = [
        {
            "id": "valid.behavior.pick_and_place",
            "schema": "schemas/v0.1/behavior-spec.schema.json",
            "path": "examples/pick-and-place.behavior.json",
            "reason": "Published behavior example must remain schema-valid.",
        },
        {
            "id": "valid.capability.generic_mobile_manipulator",
            "schema": "schemas/v0.1/capability-profile.schema.json",
            "path": "examples/generic-mobile-manipulator.capability.json",
            "reason": "Published capability example must remain schema-valid.",
        },
    ]

    generated_valid = valid_fixtures()
    generated_invalid = invalid_fixtures()

    for entry in generated_valid + generated_invalid:
        document = entry.pop("document")
        write_json(ROOT / entry["path"], document)

    manifest = {
        "schema_version": "1.0",
        "valid": valid_entries + generated_valid,
        "invalid": existing_invalid_entries() + generated_invalid,
    }
    write_json(MANIFEST, manifest)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
