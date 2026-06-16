"""Typed SDK models for OEBP documents and validation results."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping


JsonObject = dict[str, Any]


@dataclass(frozen=True)
class CoreDocument:
    protocol: str
    version: str
    kind: str
    metadata: JsonObject
    spec: JsonObject
    raw: JsonObject = field(repr=False)

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> "CoreDocument":
        kind = str(data.get("kind", ""))
        target = DOCUMENT_CLASS_BY_KIND.get(kind, CoreDocument)
        return target(
            protocol=str(data.get("protocol", "")),
            version=str(data.get("version", "")),
            kind=kind,
            metadata=dict(data.get("metadata", {}) if isinstance(data.get("metadata"), Mapping) else {}),
            spec=dict(data.get("spec", {}) if isinstance(data.get("spec"), Mapping) else {}),
            raw=dict(data),
        )


@dataclass(frozen=True)
class ProtocolEnvelopeDocument(CoreDocument):
    pass


@dataclass(frozen=True)
class ContextSnapshotDocument(CoreDocument):
    pass


@dataclass(frozen=True)
class PredicateExpressionDocument(CoreDocument):
    pass


@dataclass(frozen=True)
class SkillContractDocument(CoreDocument):
    pass


@dataclass(frozen=True)
class BehaviorSpecDocument(CoreDocument):
    pass


@dataclass(frozen=True)
class CapabilityProfileDocument(CoreDocument):
    pass


@dataclass(frozen=True)
class InvocationRequestDocument(CoreDocument):
    pass


@dataclass(frozen=True)
class InvocationFeedbackDocument(CoreDocument):
    pass


@dataclass(frozen=True)
class InvocationResultDocument(CoreDocument):
    pass


@dataclass(frozen=True)
class TraceSpanDocument(CoreDocument):
    pass


@dataclass(frozen=True)
class EpisodeAnnotationDocument(CoreDocument):
    pass


@dataclass(frozen=True)
class ProvenanceRecordDocument(CoreDocument):
    pass


DOCUMENT_CLASS_BY_KIND: dict[str, type[CoreDocument]] = {
    "ProtocolEnvelope": ProtocolEnvelopeDocument,
    "ContextSnapshot": ContextSnapshotDocument,
    "PredicateExpression": PredicateExpressionDocument,
    "SkillContract": SkillContractDocument,
    "BehaviorSpec": BehaviorSpecDocument,
    "CapabilityProfile": CapabilityProfileDocument,
    "InvocationRequest": InvocationRequestDocument,
    "InvocationFeedback": InvocationFeedbackDocument,
    "InvocationResult": InvocationResultDocument,
    "TraceSpan": TraceSpanDocument,
    "EpisodeAnnotation": EpisodeAnnotationDocument,
    "ProvenanceRecord": ProvenanceRecordDocument,
}


def document_from_mapping(data: Mapping[str, Any]) -> CoreDocument:
    return CoreDocument.from_mapping(data)


@dataclass(frozen=True)
class Finding:
    severity: str
    code: str
    pointer: str
    message: str
    phase: str
    context: JsonObject = field(default_factory=dict)
    remediation: str | None = None

    def to_dict(self) -> JsonObject:
        result: JsonObject = {
            "severity": self.severity,
            "code": self.code,
            "pointer": self.pointer,
            "message": self.message,
            "phase": self.phase,
            "context": dict(self.context),
        }
        if self.remediation:
            result["remediation"] = self.remediation
        return result


@dataclass(frozen=True)
class ValidationReport:
    source: str | None
    kind: str | None
    findings: tuple[Finding, ...]

    @property
    def ok(self) -> bool:
        return not any(finding.severity in {"error", "fatal"} for finding in self.findings)

    def findings_for_phase(self, phase: str) -> tuple[Finding, ...]:
        return tuple(finding for finding in self.findings if finding.phase == phase)

    def to_dict(self) -> JsonObject:
        return {
            "source": self.source,
            "kind": self.kind,
            "ok": self.ok,
            "findings": [finding.to_dict() for finding in self.findings],
        }
