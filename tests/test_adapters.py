from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from oebp import FixedArmAdapter, MobileManipulatorAdapter, MockRuntime, OEBPValidator  # noqa: E402


def load_json(path: str) -> dict:
    with (ROOT / path).open("r", encoding="utf-8") as handle:
        return json.load(handle)


def invocation_request(behavior: dict, profile: dict, invocation_id: str) -> dict:
    return {
        "protocol": "oebp",
        "version": "0.1.0",
        "kind": "InvocationRequest",
        "metadata": {
            "id": f"org.oebp.tests.invocation.{invocation_id}",
            "revision": "1.0.0",
            "created_at": "2026-06-16T09:00:00Z",
        },
        "spec": {
            "invocation_id": invocation_id,
            "behavior_ref": behavior["metadata"]["id"],
            "capability_profile_ref": profile["metadata"]["id"],
            "requested_at": "2026-06-16T09:00:00Z",
            "input": {
                "object": "scene/cup_01",
                "target": "scene/tray_01",
                "effector": profile["spec"]["effectors"][0]["id"],
            },
            "execution_policy": {
                "timeout_ms": 30000,
                "cancellation": "allow",
                "dry_run": True,
                "allow_recovery": True,
                "max_recovery_activations": 1,
                "required_validation_gates": ["schema", "semantic", "capability"],
            },
        },
    }


class AdapterTests(unittest.TestCase):
    def setUp(self) -> None:
        self.behavior = load_json("examples/pick-and-place.behavior.json")
        self.validator = OEBPValidator()

    def test_adapter_capability_profiles_are_schema_valid(self) -> None:
        for adapter in (FixedArmAdapter(), MobileManipulatorAdapter()):
            report = self.validator.validate_document(adapter.capability_profile())
            self.assertTrue(report.ok, report.to_dict())

    def test_same_semantic_behavior_compiles_to_two_robot_ontologies(self) -> None:
        fixed = FixedArmAdapter().compile(copy.deepcopy(self.behavior))
        mobile = MobileManipulatorAdapter().compile(copy.deepcopy(self.behavior))

        self.assertTrue(fixed.ok, fixed.to_dict())
        self.assertTrue(mobile.ok, mobile.to_dict())
        self.assertEqual(
            [step.skill for step in fixed.plan.steps],
            [step.skill for step in mobile.plan.steps],
        )
        self.assertNotEqual(
            [step.adapter.implementation["type"] for step in fixed.plan.steps],
            [step.adapter.implementation["type"] for step in mobile.plan.steps],
        )
        self.assertEqual(fixed.plan.capability_profile_ref, "org.oebp.adapters.fixed-arm.reference")
        self.assertEqual(mobile.plan.capability_profile_ref, "org.oebp.adapters.mobile-manipulator.reference")

    def test_same_semantic_behavior_runs_on_both_mock_adapters(self) -> None:
        for adapter, invocation_id in (
            (FixedArmAdapter(), "fixed-arm-runtime"),
            (MobileManipulatorAdapter(), "mobile-manipulator-runtime"),
        ):
            profile = adapter.capability_profile()
            request = invocation_request(self.behavior, profile, invocation_id)
            execution = MockRuntime().run(copy.deepcopy(self.behavior), profile, request)

            self.assertEqual(execution.terminal_state, "succeeded", execution.to_dict())
            self.assertTrue(execution.trace_spans)

    def test_unsupported_variation_fails_with_precise_capability_error(self) -> None:
        behavior = copy.deepcopy(self.behavior)
        behavior["spec"]["requirements"]["capabilities"].append(
            {"id": "oebp.capability.locomotion.navigate"}
        )

        fixed = FixedArmAdapter().compile(behavior)
        mobile = MobileManipulatorAdapter().compile(behavior)

        self.assertFalse(fixed.ok)
        self.assertIn("OEBP_CAPABILITY_MISSING", {finding.code for finding in fixed.findings})
        self.assertTrue(mobile.ok, mobile.to_dict())


if __name__ == "__main__":
    unittest.main()
