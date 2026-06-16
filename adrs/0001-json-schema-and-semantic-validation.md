# ADR 0001: JSON Schema Plus Deterministic Semantic Validation

- Status: Accepted
- Date: 2026-06-16
- Deciders: OEBP maintainers
- Related RFCs: None

## Context

OEBP needs human-readable protocol documents, stable fixtures, and deterministic
validation before any behavior can compile or execute. JSON Schema can validate
document shape, required fields, primitive types, bounded arrays, enum values,
and reusable definitions. It cannot fully validate registry references, graph
cycles, resource conflicts, stale evidence, capability matching, frame
compatibility, safety policy, adapter availability, or trace continuity.

The repository already contains Draft 2020-12 schemas and JSON examples. The
architecture review recommends a narrow v0.1 proof that starts with JSON and
keeps transport-specific encodings experimental.

## Decision

OEBP v0.1 will use JSON as the canonical exchange format and JSON Schema Draft
2020-12 for schema validation. JSON Schema validation is the first validation
gate, but it is not sufficient for conformance.

OEBP will implement a deterministic semantic validator as a separate gate. The
semantic validator will report findings with:

- severity;
- stable error code;
- JSON Pointer;
- human-readable message;
- machine-readable context;
- suggested remediation when deterministic.

The validator must not silently repair invalid behavior documents. Any future
binary or transport encoding must prove semantic equivalence with the canonical
JSON representation.

## Consequences

This decision makes fixtures easy to inspect, review, and use in conformance.
It keeps early implementation work practical and avoids binding the protocol to
a transport stack before semantics are stable.

The cost is that validators must implement checks beyond JSON Schema. Release
readiness cannot be claimed from schema validity alone.

## Alternatives Considered

### Protobuf First

Rejected for v0.1. Protobuf is useful for transport and strongly typed APIs, but
it would force binary compatibility and code-generation decisions before the
semantic model is stable.

### Pydantic As The Normative Model

Rejected as a normative source of truth. Pydantic may be useful in the Python
SDK, but the protocol must remain language-neutral.

### JSON Schema Only

Rejected. JSON Schema cannot express the semantic validation required for safe
cross-embodiment behavior compilation and execution.
