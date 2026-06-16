#!/usr/bin/env python3
"""Create JSONL training views from OEBP episode annotations.

The script emits semantic training records only. It never embeds raw
observations, media, or low-level action streams; it keeps the original
`observation_ref` and `action_ref` values from EpisodeAnnotation documents.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[1]


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"Expected a JSON object: {path}")
    return data


def display_path(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> int:
    count = 0
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n")
            count += 1
    return count


def iter_invoke_nodes(node: Any) -> Iterable[dict[str, Any]]:
    if not isinstance(node, dict):
        return
    if node.get("type") == "invoke":
        yield node
    if "child" in node:
        yield from iter_invoke_nodes(node["child"])
    children = node.get("children", [])
    if isinstance(children, list):
        for child in children:
            yield from iter_invoke_nodes(child)


def common_metadata(annotation: dict[str, Any]) -> dict[str, Any]:
    spec = annotation["spec"]
    return {
        "episode_id": spec["episode_id"],
        "behavior_ref": spec["behavior_ref"],
        "capability_profile_ref": spec["capability_profile_ref"],
        "source_dataset": spec["source_dataset"],
        "observation_ref": spec["observation_ref"],
        "action_ref": spec["action_ref"],
        "trace_ref": spec["trace_ref"],
        "outcome": spec["outcome"],
        "quality": spec.get("quality", {}),
        "provenance": spec.get("provenance", {}),
    }


def planner_rows(annotations: list[dict[str, Any]], behavior: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for annotation in annotations:
        meta = common_metadata(annotation)
        rows.append(
            {
                "schema_version": "oebp.training.v0.1",
                "view": "planner",
                "input": {
                    "observation_ref": meta["observation_ref"],
                    "capability_profile_ref": meta["capability_profile_ref"],
                    "goal": {
                        "behavior_ref": meta["behavior_ref"],
                        "success_conditions": behavior["spec"]["contract"]["success_conditions"],
                    },
                },
                "target": {
                    "behavior_ref": meta["behavior_ref"],
                    "behavior_graph": behavior["spec"]["root"],
                    "contract": behavior["spec"]["contract"],
                },
                "metadata": meta,
            }
        )
    return rows


def next_skill_rows(annotations: list[dict[str, Any]], behavior: dict[str, Any]) -> list[dict[str, Any]]:
    invoke_nodes = list(iter_invoke_nodes(behavior["spec"]["root"]))
    rows = []
    for annotation in annotations:
        meta = common_metadata(annotation)
        history: list[str] = []
        for node in invoke_nodes:
            rows.append(
                {
                    "schema_version": "oebp.training.v0.1",
                    "view": "next_skill",
                    "input": {
                        "observation_ref": meta["observation_ref"],
                        "capability_profile_ref": meta["capability_profile_ref"],
                        "behavior_ref": meta["behavior_ref"],
                        "history_node_ids": list(history),
                    },
                    "target": {
                        "node_id": node["node_id"],
                        "skill": node["skill"],
                        "args": node.get("args", {}),
                    },
                    "metadata": meta,
                }
            )
            history.append(str(node["node_id"]))
    return rows


def contract_rows(annotations: list[dict[str, Any]], behavior: dict[str, Any]) -> list[dict[str, Any]]:
    contract = behavior["spec"]["contract"]
    groups = [
        ("precondition", contract.get("preconditions", [])),
        ("invariant", contract.get("invariants", [])),
        ("success_condition", contract.get("success_conditions", [])),
        ("failure_condition", contract.get("failure_conditions", [])),
    ]
    rows = []
    for annotation in annotations:
        meta = common_metadata(annotation)
        for group, conditions in groups:
            for index, condition in enumerate(conditions):
                rows.append(
                    {
                        "schema_version": "oebp.training.v0.1",
                        "view": "contract",
                        "input": {
                            "observation_ref": meta["observation_ref"],
                            "behavior_ref": meta["behavior_ref"],
                            "condition_group": group,
                            "condition_index": index,
                            "condition": condition,
                        },
                        "target": {
                            "required_by_contract": True,
                            "outcome": meta["outcome"],
                        },
                        "metadata": meta,
                    }
                )
    return rows


def recovery_rows(annotations: list[dict[str, Any]], behavior: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for annotation in annotations:
        meta = common_metadata(annotation)
        for recovery in behavior["spec"].get("recoveries", []):
            rows.append(
                {
                    "schema_version": "oebp.training.v0.1",
                    "view": "recovery",
                    "input": {
                        "trace_ref": meta["trace_ref"],
                        "behavior_ref": meta["behavior_ref"],
                        "error_codes": recovery.get("on", []),
                    },
                    "target": {
                        "max_activations": recovery.get("max_activations"),
                        "recovery_behavior": recovery.get("behavior"),
                    },
                    "metadata": meta,
                }
            )
    return rows


def success_estimation_rows(annotations: list[dict[str, Any]], behavior: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for annotation in annotations:
        meta = common_metadata(annotation)
        rows.append(
            {
                "schema_version": "oebp.training.v0.1",
                "view": "success_estimation",
                "input": {
                    "observation_ref": meta["observation_ref"],
                    "behavior_ref": meta["behavior_ref"],
                    "contract": behavior["spec"]["contract"],
                },
                "target": {
                    "outcome": meta["outcome"],
                    "succeeded": meta["outcome"] == "succeeded",
                    "quality": meta["quality"],
                },
                "metadata": meta,
            }
        )
    return rows


def load_annotations(manifest_path: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    manifest = load_json(manifest_path)
    dataset_root = manifest_path.parent
    annotations = []
    for episode in manifest.get("episodes", []):
        annotation_path = dataset_root / episode["annotation"]
        annotations.append(load_json(annotation_path))
    return manifest, annotations


def create_training_data(
    manifest_path: Path,
    behavior_path: Path,
    capability_path: Path,
    output_dir: Path,
) -> dict[str, Any]:
    manifest, annotations = load_annotations(manifest_path)
    behavior = load_json(behavior_path)
    capability = load_json(capability_path)
    output_dir.mkdir(parents=True, exist_ok=True)

    view_rows = {
        "planner.jsonl": planner_rows(annotations, behavior),
        "next_skill.jsonl": next_skill_rows(annotations, behavior),
        "contract.jsonl": contract_rows(annotations, behavior),
        "recovery.jsonl": recovery_rows(annotations, behavior),
        "success_estimation.jsonl": success_estimation_rows(annotations, behavior),
    }
    counts = {
        filename: write_jsonl(output_dir / filename, rows)
        for filename, rows in view_rows.items()
    }
    index = {
        "schema_version": "oebp.training.v0.1",
        "source_manifest": display_path(manifest_path),
        "dataset_id": manifest.get("dataset_id"),
        "behavior_ref": behavior.get("metadata", {}).get("id"),
        "capability_profile_ref": capability.get("metadata", {}).get("id"),
        "storage_policy": manifest.get("storage_policy", {}),
        "files": counts,
    }
    (output_dir / "index.json").write_text(json.dumps(index, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return index


def main() -> int:
    parser = argparse.ArgumentParser(description="Create OEBP JSONL training-data views.")
    parser.add_argument("--manifest", default="datasets/synthetic/v0.1/manifest.json")
    parser.add_argument("--behavior", default="examples/pick-and-place.behavior.json")
    parser.add_argument("--capability", default="examples/generic-mobile-manipulator.capability.json")
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()

    index = create_training_data(
        manifest_path=(ROOT / args.manifest).resolve() if not Path(args.manifest).is_absolute() else Path(args.manifest),
        behavior_path=(ROOT / args.behavior).resolve() if not Path(args.behavior).is_absolute() else Path(args.behavior),
        capability_path=(ROOT / args.capability).resolve() if not Path(args.capability).is_absolute() else Path(args.capability),
        output_dir=Path(args.output_dir),
    )
    print(json.dumps(index, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
