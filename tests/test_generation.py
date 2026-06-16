from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from oebp import (  # noqa: E402
    FixedArmAdapter,
    GeneratedBehaviorCandidate,
    LLMGenerationGate,
    OEBPValidator,
)


def load_json(path: str) -> dict:
    with (ROOT / path).open("r", encoding="utf-8") as handle:
        return json.load(handle)


class GenerationGateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.behavior = load_json("examples/pick-and-place.behavior.json")
        self.profile = FixedArmAdapter().capability_profile()
        self.gate = LLMGenerationGate()
        self.validator = OEBPValidator()

    def test_valid_generated_behavior_passes_all_gates(self) -> None:
        candidate = GeneratedBehaviorCandidate(
            document=copy.deepcopy(self.behavior),
            source_refs=("prompt://tests/pick-place", "spec/v0.1/core.md"),
            model="offline-test-model",
            prompt_template_hash="sha256:test",
            seed=42,
        )

        result = self.gate.evaluate_behavior(candidate, self.profile)

        self.assertTrue(result.accepted, result.to_dict())
        self.assertTrue(result.execution_allowed)
        self.assertEqual(result.gate_statuses["mock_runtime"], "passed")
        self.assertEqual(result.provenance_record["spec"]["trust_level"], "validated")
        self.assertTrue(result.runtime_execution.ok)
        self.assertTrue(self.validator.validate_document(result.provenance_record).ok)

    def test_schema_failure_is_untrusted_and_not_executed(self) -> None:
        invalid = copy.deepcopy(self.behavior)
        invalid["protocol"] = "not-oebp"
        candidate = GeneratedBehaviorCandidate(document=invalid, seed=7)

        result = self.gate.evaluate_behavior(candidate, self.profile)

        self.assertFalse(result.accepted)
        self.assertFalse(result.execution_allowed)
        self.assertEqual(result.gate_statuses["schema"], "failed")
        self.assertEqual(result.gate_statuses["mock_runtime"], "skipped")
        self.assertIsNone(result.runtime_execution)
        self.assertEqual(result.provenance_record["spec"]["trust_level"], "untrusted")
        self.assertIn("OEBP_SCHEMA_PROTOCOL_CONST", {finding.code for finding in result.findings})

    def test_capability_failure_blocks_mock_execution(self) -> None:
        unsupported = copy.deepcopy(self.behavior)
        unsupported["spec"]["requirements"]["capabilities"].append(
            {"id": "oebp.capability.locomotion.navigate"}
        )
        candidate = GeneratedBehaviorCandidate(document=unsupported, seed=9)

        result = self.gate.evaluate_behavior(candidate, self.profile)

        self.assertFalse(result.accepted)
        self.assertFalse(result.execution_allowed)
        self.assertEqual(result.gate_statuses["schema"], "passed")
        self.assertEqual(result.gate_statuses["semantic"], "passed")
        self.assertEqual(result.gate_statuses["capability"], "failed")
        self.assertEqual(result.gate_statuses["mock_runtime"], "skipped")
        self.assertIsNone(result.runtime_execution)
        self.assertIn("OEBP_CAPABILITY_MISSING", {finding.code for finding in result.findings})


if __name__ == "__main__":
    unittest.main()
