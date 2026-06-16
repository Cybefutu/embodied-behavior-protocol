from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from oebp import (  # noqa: E402
    EpisodeAnnotationBuilder,
    FixedArmAdapter,
    GeneratedBehaviorCandidate,
    LLMGenerationGate,
    OEBPValidator,
)


def load_json(path: str) -> dict:
    with (ROOT / path).open("r", encoding="utf-8") as handle:
        return json.load(handle)


class EpisodeAnnotationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.behavior = load_json("examples/pick-and-place.behavior.json")
        self.profile = FixedArmAdapter().capability_profile()
        self.validator = OEBPValidator()

    def test_builder_links_runtime_trace_and_provenance(self) -> None:
        gate_result = LLMGenerationGate().evaluate_behavior(
            GeneratedBehaviorCandidate(document=copy.deepcopy(self.behavior), seed=42),
            self.profile,
        )
        self.assertTrue(gate_result.accepted, gate_result.to_dict())

        result = EpisodeAnnotationBuilder().build(
            behavior=self.behavior,
            capability_profile=self.profile,
            runtime_execution=gate_result.runtime_execution,
            provenance_record=gate_result.provenance_record,
            episode_id="synthetic-pick-place-fixed-arm-001",
            source_dataset="org.oebp.datasets.synthetic.v0_1",
            observation_ref="synthetic://observations/pick-place-fixed-arm-001",
            action_ref="synthetic://actions/pick-place-fixed-arm-001",
            action_codec="oebp.synthetic.reference-actions.v1",
            quality={"semantic_alignment": 1.0, "trace_alignment": 1.0},
        )

        self.assertTrue(result.ok, result.to_dict())
        annotation = result.annotation
        self.assertEqual(annotation["spec"]["trace_ref"], gate_result.runtime_execution.result["spec"]["trace_ref"])
        self.assertEqual(annotation["spec"]["provenance"]["generator_type"], "llm_assisted_simulation")
        self.assertNotIn("observations", annotation["spec"])
        self.assertNotIn("actions", annotation["spec"])
        self.assertTrue(self.validator.validate_document(annotation).ok)

    def test_builder_rejects_embedded_or_missing_data_refs(self) -> None:
        gate_result = LLMGenerationGate().evaluate_behavior(
            GeneratedBehaviorCandidate(document=copy.deepcopy(self.behavior), seed=43),
            self.profile,
        )
        result = EpisodeAnnotationBuilder().build(
            behavior=self.behavior,
            capability_profile=self.profile,
            runtime_execution=gate_result.runtime_execution,
            provenance_record=gate_result.provenance_record,
            episode_id="missing-refs",
            source_dataset="org.oebp.datasets.synthetic.v0_1",
            observation_ref="",
            action_ref="",
            action_codec="oebp.synthetic.reference-actions.v1",
        )

        self.assertFalse(result.ok)
        self.assertIn("OEBP_EPISODE_OBSERVATION_REF_REQUIRED", {finding.code for finding in result.findings})
        self.assertIn("OEBP_EPISODE_ACTION_REF_REQUIRED", {finding.code for finding in result.findings})

    def test_synthetic_dataset_manifest_and_episode_fixture_are_valid(self) -> None:
        manifest = load_json("datasets/synthetic/v0.1/manifest.json")
        self.assertFalse(manifest["storage_policy"]["raw_media_embedded"])
        self.assertEqual(manifest["storage_policy"]["observations"], "external_refs_only")
        self.assertEqual(manifest["storage_policy"]["actions"], "external_refs_only")

        episode_rel = "datasets/synthetic/v0.1/" + manifest["episodes"][0]["annotation"]
        episode = load_json(episode_rel)
        report = self.validator.validate_document(episode)

        self.assertTrue(report.ok, report.to_dict())
        self.assertEqual(episode["spec"]["observation_ref"], manifest["episodes"][0]["observation_ref"])
        self.assertEqual(episode["spec"]["action_ref"], manifest["episodes"][0]["action_ref"])
        self.assertNotIn("observations", episode["spec"])
        self.assertNotIn("actions", episode["spec"])


if __name__ == "__main__":
    unittest.main()
