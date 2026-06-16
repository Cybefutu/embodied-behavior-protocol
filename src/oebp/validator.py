"""Deterministic OEBP validation entry points."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable, Sequence

from .models import Finding, ValidationReport
from .schema import CORE_SCHEMA_BY_KIND, JsonSchemaSubsetValidator, SchemaIssue, SchemaStore


DEFAULT_PHASES = ("schema", "semantic")


class OEBPValidator:
    def __init__(self, root: Path | None = None) -> None:
        self.root = root or Path(__file__).resolve().parents[2]
        self.schema_store = SchemaStore(self.root)
        self.schema_validator = JsonSchemaSubsetValidator()

    def validate_path(self, path: str | Path, phases: Sequence[str] = DEFAULT_PHASES) -> ValidationReport:
        source = Path(path)
        if not source.is_absolute():
            source = self.root / source
        with source.open("r", encoding="utf-8") as handle:
            document = json.load(handle)
        return self.validate_document(document, source=str(source.relative_to(self.root)), phases=phases)

    def validate_document(
        self,
        document: Any,
        source: str | None = None,
        phases: Sequence[str] = DEFAULT_PHASES,
    ) -> ValidationReport:
        kind = document.get("kind") if isinstance(document, dict) else None
        findings: list[Finding] = []
        phase_set = set(phases)

        if "schema" in phase_set:
            findings.extend(self.validate_schema(document))
        has_schema_errors = any(finding.severity in {"error", "fatal"} for finding in findings if finding.phase == "schema")

        if isinstance(document, dict) and not has_schema_errors:
            if "semantic" in phase_set:
                findings.extend(self.validate_semantics(document))
            if "execution" in phase_set:
                findings.extend(self.validate_execution(document))

        return ValidationReport(source=source, kind=str(kind) if kind is not None else None, findings=tuple(findings))

    def validate_schema(self, document: Any) -> list[Finding]:
        if not isinstance(document, dict):
            return [
                Finding(
                    severity="error",
                    code="OEBP_SCHEMA_DOCUMENT_TYPE",
                    pointer="/",
                    message="OEBP document must be a JSON object.",
                    phase="schema",
                    remediation="Wrap the document in a protocol envelope object.",
                )
            ]

        kind = document.get("kind")
        if not isinstance(kind, str):
            schema = self.schema_store.load("schemas/v0.1/protocol-envelope.schema.json")
            issues = self.schema_validator.validate(schema, document)
        else:
            entry = self.schema_store.schema_for_kind(kind)
            if entry is None:
                schema = self.schema_store.load("schemas/v0.1/protocol-envelope.schema.json")
                issues = self.schema_validator.validate(schema, document)
            else:
                _, schema = entry
                issues = self.schema_validator.validate(schema, document)

        return [self._finding_from_schema_issue(kind if isinstance(kind, str) else None, issue) for issue in issues]

    def validate_semantics(self, document: dict[str, Any]) -> list[Finding]:
        kind = str(document.get("kind", ""))
        if kind == "BehaviorSpec":
            return self._validate_behavior_semantics(document)
        if kind == "CapabilityProfile":
            return self._validate_capability_profile_semantics(document)
        if kind == "ContextSnapshot":
            return self._validate_context_semantics(document)
        if kind == "ProvenanceRecord":
            return self._validate_provenance_semantics(document)
        if kind == "TraceSpan":
            return self._validate_trace_semantics(document)
        return []

    def validate_capability_match(self, behavior: dict[str, Any], capability_profile: dict[str, Any]) -> list[Finding]:
        findings: list[Finding] = []
        required = behavior.get("spec", {}).get("requirements", {}).get("capabilities", [])
        supported = {
            item.get("id")
            for item in capability_profile.get("spec", {}).get("capabilities", [])
            if isinstance(item, dict)
        }
        for index, requirement in enumerate(required):
            capability_id = requirement.get("id") if isinstance(requirement, dict) else None
            if capability_id and capability_id not in supported:
                findings.append(
                    Finding(
                        severity="error",
                        code="OEBP_CAPABILITY_MISSING",
                        pointer=f"/spec/requirements/capabilities/{index}/id",
                        message=f"Capability profile does not support required capability {capability_id}.",
                        phase="capability",
                        context={"capability": capability_id},
                        remediation="Select a capability profile with this capability or change the behavior requirements.",
                    )
                )

        bound_skills = {
            binding.get("skill")
            for binding in capability_profile.get("spec", {}).get("adapter_bindings", [])
            if isinstance(binding, dict)
        }
        for pointer, skill in self._iter_invoke_skills(behavior.get("spec", {}).get("root", {}), "/spec/root"):
            if skill not in bound_skills:
                findings.append(
                    Finding(
                        severity="warning",
                        code="OEBP_CAPABILITY_ADAPTER_BINDING_MISSING",
                        pointer=pointer,
                        message=f"No adapter binding is declared for invoked skill {skill}.",
                        phase="capability",
                        context={"skill": skill},
                        remediation="Add an adapter binding before compilation or execution.",
                    )
                )
        return findings

    def validate_execution(self, document: dict[str, Any]) -> list[Finding]:
        if document.get("kind") != "InvocationRequest":
            return []
        policy = document.get("spec", {}).get("execution_policy", {})
        gates = policy.get("required_validation_gates", [])
        findings: list[Finding] = []
        if isinstance(gates, list) and "schema" not in gates:
            findings.append(
                Finding(
                    severity="error",
                    code="OEBP_EXECUTION_SCHEMA_GATE_REQUIRED",
                    pointer="/spec/execution_policy/required_validation_gates",
                    message="InvocationRequest must require the schema gate before execution.",
                    phase="execution",
                    context={"required_validation_gates": gates},
                    remediation="Add schema to required_validation_gates.",
                )
            )
        if policy.get("dry_run") is False and "provenance_ref" not in document.get("spec", {}):
            findings.append(
                Finding(
                    severity="warning",
                    code="OEBP_EXECUTION_PROVENANCE_RECOMMENDED",
                    pointer="/spec/provenance_ref",
                    message="Non-dry-run invocation should reference provenance.",
                    phase="execution",
                    remediation="Attach a ProvenanceRecord reference.",
                )
            )
        return findings

    def _validate_behavior_semantics(self, document: dict[str, Any]) -> list[Finding]:
        findings: list[Finding] = []
        spec = document.get("spec", {})
        capabilities = spec.get("requirements", {}).get("capabilities", [])
        if isinstance(capabilities, list) and not capabilities:
            findings.append(
                Finding(
                    severity="warning",
                    code="OEBP_SEMANTIC_NO_REQUIRED_CAPABILITIES",
                    pointer="/spec/requirements/capabilities",
                    message="BehaviorSpec declares no required capabilities.",
                    phase="semantic",
                    remediation="Declare required capabilities before claiming cross-embodiment portability.",
                )
            )

        seen: dict[str, str] = {}
        for pointer, node_id in self._iter_node_ids(spec.get("root", {}), "/spec/root"):
            if node_id in seen:
                findings.append(
                    Finding(
                        severity="error",
                        code="OEBP_SEMANTIC_DUPLICATE_NODE_ID",
                        pointer=pointer,
                        message=f"Duplicate behavior graph node_id {node_id}.",
                        phase="semantic",
                        context={"first_pointer": seen[node_id], "node_id": node_id},
                        remediation="Use stable node_id values that are unique within the behavior document.",
                    )
                )
            else:
                seen[node_id] = pointer
        return findings

    def _validate_capability_profile_semantics(self, document: dict[str, Any]) -> list[Finding]:
        findings: list[Finding] = []
        for collection_name in ("effectors", "sensors", "frames", "capabilities"):
            seen: dict[str, int] = {}
            for index, item in enumerate(document.get("spec", {}).get(collection_name, [])):
                if not isinstance(item, dict) or "id" not in item:
                    continue
                item_id = str(item["id"])
                if item_id in seen:
                    findings.append(
                        Finding(
                            severity="error",
                            code="OEBP_SEMANTIC_DUPLICATE_ID",
                            pointer=f"/spec/{collection_name}/{index}/id",
                            message=f"Duplicate {collection_name} id {item_id}.",
                            phase="semantic",
                            context={"first_index": seen[item_id], "id": item_id},
                            remediation="Use unique ids within each capability profile collection.",
                        )
                    )
                else:
                    seen[item_id] = index
        return findings

    def _validate_context_semantics(self, document: dict[str, Any]) -> list[Finding]:
        findings: list[Finding] = []
        entities = document.get("spec", {}).get("entities", [])
        entity_ids: set[str] = set()
        for index, entity in enumerate(entities):
            if not isinstance(entity, dict):
                continue
            entity_id = str(entity.get("id", ""))
            if entity_id in entity_ids:
                findings.append(
                    Finding(
                        severity="error",
                        code="OEBP_SEMANTIC_DUPLICATE_ENTITY_ID",
                        pointer=f"/spec/entities/{index}/id",
                        message=f"Duplicate context entity id {entity_id}.",
                        phase="semantic",
                        context={"entity_id": entity_id},
                        remediation="Use stable entity ids that are unique inside the context snapshot.",
                    )
                )
            entity_ids.add(entity_id)
        for index, relation in enumerate(document.get("spec", {}).get("relations", [])):
            if not isinstance(relation, dict):
                continue
            for field in ("subject", "object"):
                value = relation.get(field)
                if isinstance(value, str) and value and value not in entity_ids:
                    findings.append(
                        Finding(
                            severity="error",
                            code="OEBP_SEMANTIC_UNRESOLVED_ENTITY_REF",
                            pointer=f"/spec/relations/{index}/{field}",
                            message=f"Relation {field} does not resolve to a context entity.",
                            phase="semantic",
                            context={"entity_ref": value},
                            remediation="Add the referenced entity or correct the relation.",
                        )
                    )
        return findings

    def _validate_provenance_semantics(self, document: dict[str, Any]) -> list[Finding]:
        spec = document.get("spec", {})
        if spec.get("trust_level") == "production_approved" and spec.get("human_review") not in {
            "approved",
            "approved_with_notes",
        }:
            return [
                Finding(
                    severity="error",
                    code="OEBP_SEMANTIC_PRODUCTION_APPROVAL_REQUIRES_REVIEW",
                    pointer="/spec/human_review",
                    message="production_approved provenance requires approved human review.",
                    phase="semantic",
                    remediation="Set human_review to approved or lower the trust_level.",
                )
            ]
        return []

    def _validate_trace_semantics(self, document: dict[str, Any]) -> list[Finding]:
        spec = document.get("spec", {})
        if spec.get("ended_at") and "duration_ms" not in spec:
            return [
                Finding(
                    severity="warning",
                    code="OEBP_SEMANTIC_TRACE_DURATION_RECOMMENDED",
                    pointer="/spec/duration_ms",
                    message="TraceSpan with ended_at should include duration_ms.",
                    phase="semantic",
                    remediation="Record a deterministic span duration.",
                )
            ]
        return []

    def _finding_from_schema_issue(self, kind: str | None, issue: SchemaIssue) -> Finding:
        return Finding(
            severity="error",
            code=self._schema_code(kind, issue),
            pointer=issue.pointer,
            message=issue.message,
            phase="schema",
            context={"keyword": issue.keyword, **issue.context},
            remediation=self._schema_remediation(issue),
        )

    def _schema_code(self, kind: str | None, issue: SchemaIssue) -> str:
        pointer = issue.pointer
        message = issue.message
        if pointer == "/protocol" and issue.keyword == "const":
            return "OEBP_SCHEMA_PROTOCOL_CONST"
        if pointer == "/kind" and issue.keyword in {"const", "enum"}:
            return "OEBP_SCHEMA_KIND_CONST" if kind in CORE_SCHEMA_BY_KIND else "OEBP_SCHEMA_KIND_ENUM"
        if pointer == "/version" and issue.keyword == "pattern":
            return "OEBP_SCHEMA_VERSION_PATTERN"
        if "missing required property" in message:
            required = str(issue.context.get("property", "FIELD")).upper()
            return f"OEBP_SCHEMA_{required}_REQUIRED"
        if issue.keyword == "enum":
            leaf = pointer.rsplit("/", 1)[-1].upper()
            return f"OEBP_SCHEMA_{leaf}_ENUM"
        if issue.keyword == "minItems":
            leaf = pointer.rsplit("/", 1)[-1].upper()
            return f"OEBP_SCHEMA_{leaf}_MIN_ITEMS"
        if issue.keyword == "maxItems":
            leaf = pointer.rsplit("/", 1)[-1].upper()
            return f"OEBP_SCHEMA_{leaf}_MAX_ITEMS"
        if issue.keyword == "minimum":
            leaf = pointer.rsplit("/", 1)[-1].upper()
            return f"OEBP_SCHEMA_{leaf}_MINIMUM"
        if issue.keyword == "maximum":
            leaf = pointer.rsplit("/", 1)[-1].upper()
            return f"OEBP_SCHEMA_{leaf}_MAXIMUM"
        if issue.keyword == "pattern":
            leaf = pointer.rsplit("/", 1)[-1].upper()
            return f"OEBP_SCHEMA_{leaf}_PATTERN"
        if issue.keyword == "type":
            leaf = pointer.rsplit("/", 1)[-1].upper() or "DOCUMENT"
            return f"OEBP_SCHEMA_{leaf}_TYPE"
        if issue.keyword == "uniqueItems":
            leaf = pointer.rsplit("/", 1)[-1].upper()
            return f"OEBP_SCHEMA_{leaf}_UNIQUE_ITEMS"
        if issue.keyword == "oneOf":
            return "OEBP_SCHEMA_ONEOF"
        return "OEBP_SCHEMA_VALIDATION_FAILED"

    def _schema_remediation(self, issue: SchemaIssue) -> str:
        if issue.keyword == "required":
            return f"Add the required property {issue.context.get('property')}."
        if issue.keyword == "enum":
            return "Use one of the enumerated values from the schema."
        if issue.keyword == "const":
            return "Use the constant value required by the schema."
        if issue.keyword == "type":
            return "Change the value to the type required by the schema."
        return "Update the document so it satisfies the target JSON Schema."

    def _iter_node_ids(self, node: Any, pointer: str) -> Iterable[tuple[str, str]]:
        if not isinstance(node, dict):
            return
        node_id = node.get("node_id")
        if isinstance(node_id, str):
            yield f"{pointer}/node_id", node_id
        if "child" in node:
            yield from self._iter_node_ids(node["child"], f"{pointer}/child")
        for index, child in enumerate(node.get("children", []) if isinstance(node.get("children"), list) else []):
            yield from self._iter_node_ids(child, f"{pointer}/children/{index}")

    def _iter_invoke_skills(self, node: Any, pointer: str) -> Iterable[tuple[str, str]]:
        if not isinstance(node, dict):
            return
        if node.get("type") == "invoke" and isinstance(node.get("skill"), str):
            yield f"{pointer}/skill", str(node["skill"])
        if "child" in node:
            yield from self._iter_invoke_skills(node["child"], f"{pointer}/child")
        for index, child in enumerate(node.get("children", []) if isinstance(node.get("children"), list) else []):
            yield from self._iter_invoke_skills(child, f"{pointer}/children/{index}")
