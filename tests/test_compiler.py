from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from oebp import OEBPCompiler  # noqa: E402


def load_json(path: str) -> dict:
    with (ROOT / path).open("r", encoding="utf-8") as handle:
        return json.load(handle)


def complete_profile() -> dict:
    profile = load_json("examples/generic-mobile-manipulator.capability.json")
    skills = [
        "oebp.skill.perception.estimate_pose@1",
        "oebp.skill.manipulation.reach@1",
        "oebp.skill.manipulation.grasp@1",
        "oebp.skill.manipulation.lift@1",
        "oebp.skill.manipulation.place@1",
        "oebp.skill.meta.verify@1",
    ]
    profile["spec"]["adapter_bindings"] = [
        {
            "skill": skill,
            "implementation": {"type": "local_function", "name": skill.replace(".", "_").replace("@", "_")},
            "parameter_map": {},
            "result_map": {"ok": "succeeded"},
        }
        for skill in skills
    ]
    return profile


class CompilerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.compiler = OEBPCompiler()

    def test_compile_selects_bindings_deterministically(self) -> None:
        behavior = load_json("examples/pick-and-place.behavior.json")
        profile = complete_profile()

        first = self.compiler.compile(behavior, profile)
        second = self.compiler.compile(behavior, profile)

        self.assertTrue(first.ok, first.to_dict())
        self.assertEqual(first.to_dict(), second.to_dict())
        self.assertEqual(len(first.plan.steps), 6)
        self.assertTrue(all(step.adapter.implementation["type"] == "local_function" for step in first.plan.steps))

    def test_compile_fails_when_adapter_binding_is_missing(self) -> None:
        behavior = load_json("examples/pick-and-place.behavior.json")
        profile = complete_profile()
        profile["spec"]["adapter_bindings"] = [
            binding
            for binding in profile["spec"]["adapter_bindings"]
            if binding["skill"] != "oebp.skill.manipulation.lift@1"
        ]

        result = self.compiler.compile(behavior, profile)
        codes = {finding.code for finding in result.findings}

        self.assertFalse(result.ok)
        self.assertIn("OEBP_COMPILER_ADAPTER_BINDING_MISSING", codes)

    def test_resource_conflict_is_reported_before_execution(self) -> None:
        behavior = load_json("examples/pick-and-place.behavior.json")
        behavior["spec"]["root"] = {
            "type": "parallel",
            "node_id": "parallel-conflict",
            "children": [
                {
                    "type": "invoke",
                    "node_id": "left",
                    "skill": "oebp.skill.manipulation.grasp@1",
                    "args": {},
                    "resources": ["arm/gripper"],
                },
                {
                    "type": "invoke",
                    "node_id": "right",
                    "skill": "oebp.skill.manipulation.place@1",
                    "args": {},
                    "resources": ["arm/gripper"],
                },
            ],
        }

        result = self.compiler.compile(behavior, complete_profile())

        self.assertIn("OEBP_COMPILER_RESOURCE_CONFLICT", {finding.code for finding in result.findings})

    def test_risk_gate_blocks_unapproved_risk_class(self) -> None:
        behavior = load_json("examples/pick-and-place.behavior.json")
        behavior["spec"]["requirements"]["risk_class"] = "R4"

        result = self.compiler.compile(behavior, complete_profile())

        self.assertIn("OEBP_COMPILER_RISK_REQUIRES_APPROVAL", {finding.code for finding in result.findings})

    def test_unit_constraint_mismatch_is_reported(self) -> None:
        behavior = load_json("examples/pick-and-place.behavior.json")
        behavior["spec"]["requirements"]["capabilities"][0]["constraints"] = {"unit": "cm"}
        profile = complete_profile()
        profile["spec"]["capabilities"][0]["parameters"]["unit"] = "m"

        result = self.compiler.compile(behavior, profile)

        self.assertIn("OEBP_COMPILER_UNIT_CONSTRAINT_MISMATCH", {finding.code for finding in result.findings})


if __name__ == "__main__":
    unittest.main()
