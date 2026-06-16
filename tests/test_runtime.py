from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from oebp import AdapterOutcome, MockRuntime, OEBPValidator, RuntimeControls  # noqa: E402


ROOT_SKILLS = [
    "oebp.skill.perception.estimate_pose@1",
    "oebp.skill.manipulation.reach@1",
    "oebp.skill.manipulation.grasp@1",
    "oebp.skill.manipulation.lift@1",
    "oebp.skill.manipulation.place@1",
    "oebp.skill.meta.verify@1",
    "oebp.skill.manipulation.release@1",
]


def load_json(path: str) -> dict:
    with (ROOT / path).open("r", encoding="utf-8") as handle:
        return json.load(handle)


def complete_profile() -> dict:
    profile = load_json("examples/generic-mobile-manipulator.capability.json")
    profile["spec"]["adapter_bindings"] = [
        {
            "skill": skill,
            "implementation": {"type": "local_function", "name": skill.replace(".", "_").replace("@", "_")},
            "parameter_map": {},
            "result_map": {"ok": "succeeded"},
        }
        for skill in ROOT_SKILLS
    ]
    return profile


def invocation_request(behavior: dict, profile: dict, timeout_ms: int = 30000) -> dict:
    return {
        "protocol": "oebp",
        "version": "0.1.0",
        "kind": "InvocationRequest",
        "metadata": {
            "id": "org.oebp.tests.invocation.runtime",
            "revision": "1.0.0",
            "created_at": "2026-06-16T09:00:00Z",
        },
        "spec": {
            "invocation_id": "runtime-test-001",
            "behavior_ref": behavior["metadata"]["id"],
            "capability_profile_ref": profile["metadata"]["id"],
            "requested_at": "2026-06-16T09:00:00Z",
            "input": {
                "object": "scene/cup_01",
                "target": "scene/tray_01",
                "effector": "robot/right_gripper",
            },
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


class MockRuntimeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.validator = OEBPValidator()
        self.behavior = load_json("examples/pick-and-place.behavior.json")
        self.profile = complete_profile()
        self.request = invocation_request(self.behavior, self.profile)

    def assert_runtime_documents_are_valid(self, execution) -> None:
        documents = list(execution.feedback) + [execution.result] + list(execution.trace_spans)
        self.assertTrue(documents)
        for document in documents:
            report = self.validator.validate_document(document)
            self.assertTrue(report.ok, report.to_dict())

    def test_successful_run_is_deterministic_and_traced(self) -> None:
        runtime = MockRuntime()

        first = runtime.run(copy.deepcopy(self.behavior), copy.deepcopy(self.profile), copy.deepcopy(self.request))
        second = runtime.run(copy.deepcopy(self.behavior), copy.deepcopy(self.profile), copy.deepcopy(self.request))

        self.assertTrue(first.ok, first.to_dict())
        self.assertEqual(first.to_dict(), second.to_dict())
        self.assertEqual(first.feedback[0]["spec"]["state"], "accepted")
        traced_nodes = {span["spec"]["node_id"] for span in first.trace_spans}
        self.assertTrue(
            {
                "pick-place-sequence",
                "estimate-object-pose",
                "reach-object",
                "retry-grasp",
                "grasp-object",
                "lift-object",
                "place-object",
                "verify-result",
            }.issubset(traced_nodes)
        )
        self.assert_runtime_documents_are_valid(first)

    def test_cancellation_terminates_accepted_goal(self) -> None:
        execution = MockRuntime().run(
            copy.deepcopy(self.behavior),
            copy.deepcopy(self.profile),
            copy.deepcopy(self.request),
            controls=RuntimeControls(cancel_at_node_id="grasp-object"),
        )

        self.assertEqual(execution.terminal_state, "canceled")
        self.assertIn("canceling", {feedback["spec"]["state"] for feedback in execution.feedback})
        self.assertIn("OEBP_RUNTIME_CANCELED", {finding.code for finding in execution.findings})
        self.assert_runtime_documents_are_valid(execution)

    def test_preemption_has_distinct_terminal_result(self) -> None:
        execution = MockRuntime().run(
            copy.deepcopy(self.behavior),
            copy.deepcopy(self.profile),
            copy.deepcopy(self.request),
            controls=RuntimeControls(preempt_at_node_id="place-object"),
        )

        self.assertEqual(execution.terminal_state, "preempted")
        self.assertIn("OEBP_RUNTIME_PREEMPTED", {finding.code for finding in execution.findings})
        self.assert_runtime_documents_are_valid(execution)

    def test_timeout_enforces_invocation_deadline(self) -> None:
        request = invocation_request(self.behavior, self.profile, timeout_ms=5000)
        runtime = MockRuntime(
            adapter_outcomes={
                "estimate-object-pose": [AdapterOutcome.succeeded(duration_ms=6000)],
            }
        )

        execution = runtime.run(copy.deepcopy(self.behavior), copy.deepcopy(self.profile), request)

        self.assertEqual(execution.terminal_state, "timeout")
        self.assertIn("OEBP_RUNTIME_TIMEOUT", {finding.code for finding in execution.findings})
        self.assert_runtime_documents_are_valid(execution)

    def test_bounded_recovery_can_restore_failed_behavior(self) -> None:
        runtime = MockRuntime(
            adapter_outcomes={
                "grasp-object": [
                    AdapterOutcome.failed(
                        code="oebp.error.manipulation.object_slipped@1",
                        message="Object slipped during grasp.",
                        recoverable=True,
                    ),
                    AdapterOutcome.failed(
                        code="oebp.error.manipulation.object_slipped@1",
                        message="Object slipped during grasp.",
                        recoverable=True,
                    ),
                    AdapterOutcome.succeeded({"ok": True, "after_recovery": True}),
                ],
            }
        )

        execution = runtime.run(copy.deepcopy(self.behavior), copy.deepcopy(self.profile), copy.deepcopy(self.request))

        self.assertEqual(execution.terminal_state, "succeeded", execution.to_dict())
        self.assertTrue(execution.result["spec"]["recovery_summary"]["attempted"])
        self.assertEqual(execution.result["spec"]["recovery_summary"]["activation_count"], 1)
        self.assertIn("recovering", {feedback["spec"]["state"] for feedback in execution.feedback})
        self.assertIn("safe-release", {span["spec"]["node_id"] for span in execution.trace_spans})
        self.assert_runtime_documents_are_valid(execution)


if __name__ == "__main__":
    unittest.main()
