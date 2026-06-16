from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


class TrainingDataScriptTests(unittest.TestCase):
    def test_create_training_data_outputs_reference_only_views(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            completed = subprocess.run(
                [
                    sys.executable,
                    "scripts/create_training_data.py",
                    "--output-dir",
                    tempdir,
                ],
                cwd=ROOT,
                check=True,
                capture_output=True,
                text=True,
            )

            index = json.loads(completed.stdout)
            self.assertEqual(index["schema_version"], "oebp.training.v0.1")
            self.assertEqual(index["source_manifest"], "datasets/synthetic/v0.1/manifest.json")
            self.assertEqual(index["files"]["planner.jsonl"], 1)
            self.assertEqual(index["files"]["next_skill.jsonl"], 6)
            self.assertGreaterEqual(index["files"]["contract.jsonl"], 1)
            self.assertEqual(index["files"]["recovery.jsonl"], 1)
            self.assertEqual(index["files"]["success_estimation.jsonl"], 1)

            output_dir = Path(tempdir)
            planner = read_jsonl(output_dir / "planner.jsonl")[0]
            next_skill = read_jsonl(output_dir / "next_skill.jsonl")[0]
            success = read_jsonl(output_dir / "success_estimation.jsonl")[0]

            for row in (planner, next_skill, success):
                self.assertIn("observation_ref", row["metadata"])
                self.assertIn("action_ref", row["metadata"])
                encoded = json.dumps(row)
                self.assertNotIn('"observations"', encoded)
                self.assertNotIn('"actions"', encoded)
                self.assertNotIn('"raw_actions"', encoded)
                self.assertNotIn('"video"', encoded)

            self.assertEqual(planner["view"], "planner")
            self.assertEqual(next_skill["view"], "next_skill")
            self.assertTrue(success["target"]["succeeded"])


if __name__ == "__main__":
    unittest.main()
