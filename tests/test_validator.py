from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from oebp import BehaviorSpecDocument, OEBPValidator, document_from_mapping  # noqa: E402


def load_json(path: str) -> dict:
    with (ROOT / path).open("r", encoding="utf-8") as handle:
        return json.load(handle)


class ValidatorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.validator = OEBPValidator(ROOT)

    def test_valid_behavior_schema_and_typed_document(self) -> None:
        document = load_json("examples/pick-and-place.behavior.json")
        typed = document_from_mapping(document)
        self.assertIsInstance(typed, BehaviorSpecDocument)

        report = self.validator.validate_document(document)

        self.assertTrue(report.ok, report.to_dict())
        self.assertEqual(report.kind, "BehaviorSpec")
        self.assertEqual(report.findings_for_phase("schema"), ())

    def test_invalid_schema_returns_stable_finding_shape(self) -> None:
        report = self.validator.validate_path("conformance/fixtures/invalid/behavior-wrong-protocol.json")

        self.assertFalse(report.ok)
        finding = report.findings[0]
        self.assertEqual(finding.severity, "error")
        self.assertEqual(finding.code, "OEBP_SCHEMA_PROTOCOL_CONST")
        self.assertEqual(finding.pointer, "/protocol")
        self.assertEqual(finding.phase, "schema")
        self.assertIn("keyword", finding.context)
        self.assertIsNotNone(finding.remediation)

    def test_semantic_duplicate_node_id_is_separate_from_schema(self) -> None:
        document = load_json("examples/pick-and-place.behavior.json")
        duplicate = copy.deepcopy(document)
        duplicate["spec"]["root"]["children"][1]["node_id"] = "estimate-object-pose"

        report = self.validator.validate_document(duplicate, phases=("schema", "semantic"))

        self.assertTrue(any(finding.code == "OEBP_SEMANTIC_DUPLICATE_NODE_ID" for finding in report.findings))
        self.assertEqual(report.findings_for_phase("schema"), ())

    def test_capability_match_reports_missing_capabilities(self) -> None:
        behavior = load_json("examples/pick-and-place.behavior.json")
        profile = load_json("conformance/fixtures/valid/capability-fixed-arm.json")

        findings = self.validator.validate_capability_match(behavior, profile)
        codes = {finding.code for finding in findings}

        self.assertIn("OEBP_CAPABILITY_MISSING", codes)
        self.assertTrue(all(finding.phase == "capability" for finding in findings))

    def test_execution_gate_is_separate(self) -> None:
        request = load_json("conformance/fixtures/valid/invocation-request.json")
        request["spec"]["execution_policy"]["required_validation_gates"] = ["semantic"]

        findings = self.validator.validate_execution(request)

        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].code, "OEBP_EXECUTION_SCHEMA_GATE_REQUIRED")
        self.assertEqual(findings[0].phase, "execution")


if __name__ == "__main__":
    unittest.main()
