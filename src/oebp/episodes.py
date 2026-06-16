"""Trace-linked episode annotation helpers for OEBP datasets."""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
from typing import Any, Mapping

from .models import Finding
from .runtime import RuntimeExecution
from .validator import OEBPValidator


TERMINAL_TO_EPISODE_OUTCOME = {
    "succeeded": "succeeded",
    "failed": "failed",
    "canceled": "canceled",
    "preempted": "preempted",
    "timeout": "failed",
    "unsafe": "unsafe",
    "internal_error": "failed",
}


@dataclass(frozen=True)
class EpisodeAnnotationResult:
    annotation: dict[str, Any]
    findings: tuple[Finding, ...] = field(default_factory=tuple)

    @property
    def ok(self) -> bool:
        return not any(finding.severity in {"error", "fatal"} for finding in self.findings)

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "annotation": copy.deepcopy(self.annotation),
            "findings": [finding.to_dict() for finding in self.findings],
        }


class EpisodeAnnotationBuilder:
    def __init__(self, validator: OEBPValidator | None = None) -> None:
        self.validator = validator or OEBPValidator()

    def build(
        self,
        behavior: dict[str, Any],
        capability_profile: dict[str, Any],
        runtime_execution: RuntimeExecution,
        provenance_record: dict[str, Any],
        episode_id: str,
        source_dataset: str,
        observation_ref: str,
        action_ref: str,
        action_codec: str,
        quality: Mapping[str, float] | None = None,
    ) -> EpisodeAnnotationResult:
        annotation = {
            "protocol": "oebp",
            "version": "0.1.0",
            "kind": "EpisodeAnnotation",
            "metadata": {
                "id": f"episode.{episode_id}",
                "revision": "1.0.0",
                "created_at": "2026-06-16T09:00:00Z",
            },
            "spec": {
                "episode_id": episode_id,
                "behavior_ref": str(behavior.get("metadata", {}).get("id", "")),
                "capability_profile_ref": str(capability_profile.get("metadata", {}).get("id", "")),
                "source_dataset": source_dataset,
                "outcome": self._episode_outcome(runtime_execution.terminal_state),
                "trace_ref": str(runtime_execution.result.get("spec", {}).get("trace_ref", "")),
                "observation_ref": observation_ref,
                "action_ref": action_ref,
                "action_codec": action_codec,
                "quality": dict(quality or {"semantic_alignment": 1.0}),
                "provenance": self._provenance_summary(provenance_record),
            },
        }
        error_code = self._error_code(runtime_execution)
        if error_code:
            annotation["spec"]["error_code"] = error_code

        findings = list(self.validator.validate_document(annotation).findings)
        findings.extend(self._reference_only_findings(annotation))
        return EpisodeAnnotationResult(annotation=annotation, findings=tuple(findings))

    def _episode_outcome(self, terminal_state: str) -> str:
        return TERMINAL_TO_EPISODE_OUTCOME.get(terminal_state, "unknown")

    def _error_code(self, runtime_execution: RuntimeExecution) -> str | None:
        if runtime_execution.terminal_state == "succeeded":
            return None
        findings = runtime_execution.result.get("spec", {}).get("findings", [])
        for finding in findings:
            if isinstance(finding, dict) and finding.get("code"):
                return str(finding["code"])
        return runtime_execution.terminal_state

    def _provenance_summary(self, provenance_record: dict[str, Any]) -> dict[str, Any]:
        spec = provenance_record.get("spec", {}) if isinstance(provenance_record.get("spec"), dict) else {}
        summary = {
            "generator_type": spec.get("generator_type", "other"),
            "seed": int(spec.get("seed", 0)),
            "validator_versions": list(spec.get("validator_versions", ["oebp-episode-builder/0.1.0"])),
            "human_review": spec.get("human_review", "not_reviewed"),
        }
        for optional in ("model", "prompt_template_hash", "simulator", "adapter_version"):
            if optional in spec:
                summary[optional] = spec[optional]
        return summary

    def _reference_only_findings(self, annotation: dict[str, Any]) -> list[Finding]:
        spec = annotation.get("spec", {}) if isinstance(annotation.get("spec"), dict) else {}
        findings: list[Finding] = []
        if not spec.get("observation_ref"):
            findings.append(
                self._finding(
                    "OEBP_EPISODE_OBSERVATION_REF_REQUIRED",
                    "/spec/observation_ref",
                    "EpisodeAnnotation must reference observations instead of embedding them.",
                )
            )
        if not spec.get("action_ref"):
            findings.append(
                self._finding(
                    "OEBP_EPISODE_ACTION_REF_REQUIRED",
                    "/spec/action_ref",
                    "EpisodeAnnotation must reference actions instead of embedding them.",
                )
            )
        for forbidden in ("observations", "actions", "frames", "video", "raw_actions"):
            if forbidden in spec:
                findings.append(
                    self._finding(
                        "OEBP_EPISODE_RAW_DATA_EMBEDDED",
                        f"/spec/{forbidden}",
                        f"EpisodeAnnotation must not embed raw {forbidden} data.",
                    )
                )
        return findings

    def _finding(self, code: str, pointer: str, message: str) -> Finding:
        return Finding(
            severity="error",
            code=code,
            pointer=pointer,
            message=message,
            phase="episode",
            remediation="Store raw data externally and keep only stable references in the annotation.",
        )
