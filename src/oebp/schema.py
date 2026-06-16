"""Schema loading and dependency-free JSON Schema subset validation."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]

CORE_SCHEMA_BY_KIND = {
    "BehaviorSpec": "schemas/v0.1/behavior-spec.schema.json",
    "CapabilityProfile": "schemas/v0.1/capability-profile.schema.json",
    "ContextSnapshot": "schemas/v0.1/context-snapshot.schema.json",
    "EpisodeAnnotation": "schemas/v0.1/episode-annotation.schema.json",
    "InvocationFeedback": "schemas/v0.1/invocation-feedback.schema.json",
    "InvocationRequest": "schemas/v0.1/invocation-request.schema.json",
    "InvocationResult": "schemas/v0.1/invocation-result.schema.json",
    "PredicateExpression": "schemas/v0.1/predicate-expression.schema.json",
    "ProtocolEnvelope": "schemas/v0.1/protocol-envelope.schema.json",
    "ProvenanceRecord": "schemas/v0.1/provenance-record.schema.json",
    "SkillContract": "schemas/v0.1/skill-contract.schema.json",
    "TraceSpan": "schemas/v0.1/trace-span.schema.json",
}


@dataclass(frozen=True)
class SchemaIssue:
    pointer: str
    message: str
    keyword: str
    context: dict[str, Any]


class SchemaStore:
    def __init__(self, root: Path | None = None) -> None:
        self.root = root or REPO_ROOT
        self._cache: dict[str, dict[str, Any]] = {}

    def load(self, schema_rel: str) -> dict[str, Any]:
        if schema_rel not in self._cache:
            with (self.root / schema_rel).open("r", encoding="utf-8") as handle:
                self._cache[schema_rel] = json.load(handle)
        return self._cache[schema_rel]

    def schema_for_kind(self, kind: str) -> tuple[str, dict[str, Any]] | None:
        rel = CORE_SCHEMA_BY_KIND.get(kind)
        if rel is None:
            return None
        return rel, self.load(rel)


class JsonSchemaSubsetValidator:
    """Validate the JSON Schema subset used by the v0.1 bootstrap schemas."""

    def validate(self, schema: dict[str, Any], instance: Any) -> list[SchemaIssue]:
        return self._validate(schema, instance, schema, "")

    def _validate(
        self,
        schema: dict[str, Any],
        instance: Any,
        root_schema: dict[str, Any],
        pointer: str,
    ) -> list[SchemaIssue]:
        if "$ref" in schema:
            return self._validate(self._resolve_ref(root_schema, str(schema["$ref"])), instance, root_schema, pointer)

        if "oneOf" in schema:
            matches = 0
            for option in schema["oneOf"]:
                if not self._validate(option, instance, root_schema, pointer):
                    matches += 1
            if matches != 1:
                return [self._issue(pointer, "expected exactly one oneOf match, got %d" % matches, "oneOf")]
            return []

        errors: list[SchemaIssue] = []
        expected_type = schema.get("type")
        if expected_type is not None and not self._type_matches(expected_type, instance):
            return [self._issue(pointer, "expected %s" % expected_type, "type", {"expected": expected_type})]

        if "const" in schema and instance != schema["const"]:
            errors.append(self._issue(pointer, "expected const %r" % schema["const"], "const", {"expected": schema["const"]}))
        if "enum" in schema and instance not in schema["enum"]:
            errors.append(self._issue(pointer, "value %r is not in enum" % instance, "enum", {"allowed": schema["enum"]}))
        if isinstance(instance, str):
            if "pattern" in schema and not re.search(str(schema["pattern"]), instance):
                errors.append(self._issue(pointer, "string does not match pattern", "pattern", {"pattern": schema["pattern"]}))
            if "minLength" in schema and len(instance) < int(schema["minLength"]):
                errors.append(self._issue(pointer, "string is shorter than minLength", "minLength"))
            if "maxLength" in schema and len(instance) > int(schema["maxLength"]):
                errors.append(self._issue(pointer, "string is longer than maxLength", "maxLength"))
        if isinstance(instance, (int, float)) and not isinstance(instance, bool):
            if "minimum" in schema and instance < schema["minimum"]:
                errors.append(self._issue(pointer, "number is below minimum", "minimum", {"minimum": schema["minimum"]}))
            if "maximum" in schema and instance > schema["maximum"]:
                errors.append(self._issue(pointer, "number is above maximum", "maximum", {"maximum": schema["maximum"]}))
            if "exclusiveMinimum" in schema and instance <= schema["exclusiveMinimum"]:
                errors.append(self._issue(pointer, "number is not above exclusiveMinimum", "exclusiveMinimum"))
        if isinstance(instance, list):
            errors.extend(self._validate_array(schema, instance, root_schema, pointer))
        if isinstance(instance, dict):
            errors.extend(self._validate_object(schema, instance, root_schema, pointer))
        return errors

    def _validate_array(
        self,
        schema: dict[str, Any],
        instance: list[Any],
        root_schema: dict[str, Any],
        pointer: str,
    ) -> list[SchemaIssue]:
        errors: list[SchemaIssue] = []
        if "minItems" in schema and len(instance) < int(schema["minItems"]):
            errors.append(self._issue(pointer, "array has too few items", "minItems", {"minItems": schema["minItems"]}))
        if "maxItems" in schema and len(instance) > int(schema["maxItems"]):
            errors.append(self._issue(pointer, "array has too many items", "maxItems", {"maxItems": schema["maxItems"]}))
        if schema.get("uniqueItems") and len({json.dumps(item, sort_keys=True) for item in instance}) != len(instance):
            errors.append(self._issue(pointer, "array items are not unique", "uniqueItems"))
        if "items" in schema:
            for index, item in enumerate(instance):
                errors.extend(self._validate(schema["items"], item, root_schema, f"{pointer}/{index}"))
        return errors

    def _validate_object(
        self,
        schema: dict[str, Any],
        instance: dict[str, Any],
        root_schema: dict[str, Any],
        pointer: str,
    ) -> list[SchemaIssue]:
        errors: list[SchemaIssue] = []
        if "maxProperties" in schema and len(instance) > int(schema["maxProperties"]):
            errors.append(self._issue(pointer, "object has too many properties", "maxProperties"))
        for key in schema.get("required", []):
            if key not in instance:
                errors.append(self._issue(pointer, "missing required property %r" % key, "required", {"property": key}))
        properties = schema.get("properties", {})
        for key, value in instance.items():
            child_pointer = f"{pointer}/{self._escape_pointer(key)}"
            if "propertyNames" in schema:
                errors.extend(self._validate(schema["propertyNames"], key, root_schema, child_pointer))
            if key in properties:
                errors.extend(self._validate(properties[key], value, root_schema, child_pointer))
            else:
                additional = schema.get("additionalProperties", True)
                if additional is False:
                    errors.append(self._issue(child_pointer, "additional property is not allowed", "additionalProperties"))
                elif isinstance(additional, dict):
                    errors.extend(self._validate(additional, value, root_schema, child_pointer))
        return errors

    def _type_matches(self, expected_type: Any, instance: Any) -> bool:
        if isinstance(expected_type, list):
            return any(self._type_matches(item, instance) for item in expected_type)
        return {
            "object": isinstance(instance, dict),
            "array": isinstance(instance, list),
            "string": isinstance(instance, str),
            "integer": isinstance(instance, int) and not isinstance(instance, bool),
            "number": isinstance(instance, (int, float)) and not isinstance(instance, bool),
            "boolean": isinstance(instance, bool),
            "null": instance is None,
        }.get(str(expected_type), True)

    def _resolve_ref(self, root_schema: dict[str, Any], ref: str) -> dict[str, Any]:
        if not ref.startswith("#/"):
            raise ValueError(f"external $ref is not supported by the SDK fallback validator: {ref}")
        current: Any = root_schema
        for part in ref[2:].split("/"):
            current = current[part]
        if not isinstance(current, dict):
            raise ValueError(f"$ref does not resolve to a schema object: {ref}")
        return current

    def _issue(
        self,
        pointer: str,
        message: str,
        keyword: str,
        context: dict[str, Any] | None = None,
    ) -> SchemaIssue:
        return SchemaIssue(pointer or "/", message, keyword, context or {})

    def _escape_pointer(self, value: str) -> str:
        return value.replace("~", "~0").replace("/", "~1")
