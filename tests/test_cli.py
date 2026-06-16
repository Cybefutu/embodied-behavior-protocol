from __future__ import annotations

import contextlib
import io
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from oebp.cli import main  # noqa: E402


class CliTests(unittest.TestCase):
    def run_cli(self, *args: str) -> tuple[int, dict]:
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            code = main(list(args))
        return code, json.loads(stdout.getvalue())

    def test_legacy_document_argument_still_validates(self) -> None:
        code, payload = self.run_cli("examples/pick-and-place.behavior.json")

        self.assertEqual(code, 0, payload)
        self.assertTrue(payload["ok"])

    def test_compile_command_succeeds_with_example_profile(self) -> None:
        code, payload = self.run_cli(
            "compile",
            "examples/pick-and-place.behavior.json",
            "--capability",
            "examples/generic-mobile-manipulator.capability.json",
        )

        self.assertEqual(code, 0, payload)
        self.assertTrue(payload["ok"])
        self.assertEqual(len(payload["plan"]["steps"]), 6)

    def test_run_command_succeeds_with_mock_adapter(self) -> None:
        code, payload = self.run_cli(
            "run",
            "examples/pick-and-place.behavior.json",
            "--adapter",
            "mock",
        )

        self.assertEqual(code, 0, payload)
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["result"]["spec"]["terminal_state"], "succeeded")

    def test_conformance_command_runs_suite(self) -> None:
        code, payload = self.run_cli("conformance", "run")

        self.assertEqual(code, 0, payload)
        self.assertTrue(payload["passed"])
        self.assertGreaterEqual(payload["lifecycle_scenarios"], 10)
        self.assertGreaterEqual(payload["failure_recovery_scenarios"], 10)


if __name__ == "__main__":
    unittest.main()
