from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from oebp import OEBPConformanceSuite  # noqa: E402


class ConformanceSuiteTests(unittest.TestCase):
    def test_conformance_suite_passes_required_categories(self) -> None:
        report = OEBPConformanceSuite(ROOT).run()
        payload = report.to_dict()
        categories = {check["category"] for check in payload["checks"]}

        self.assertTrue(report.passed, payload)
        self.assertGreaterEqual(report.lifecycle_scenarios, 10)
        self.assertGreaterEqual(report.failure_recovery_scenarios, 10)
        self.assertTrue(
            {
                "schema",
                "semantic-validator",
                "lifecycle",
                "cancellation",
                "resource-conflict",
                "capability-matching",
                "cross-embodiment",
                "trace-alignment",
                "json-round-trip",
                "provenance",
            }.issubset(categories)
        )

    def test_conformance_report_is_json_round_trip_safe(self) -> None:
        payload = OEBPConformanceSuite(ROOT).run().to_dict()
        self.assertEqual(json.loads(json.dumps(payload, sort_keys=True)), payload)


if __name__ == "__main__":
    unittest.main()
