# OEBP Schemas v0.1

This directory contains the initial JSON Schema Draft 2020-12 proposal for OEBP
v0.1 machine-readable documents.

## Current Schemas

- `protocol-envelope.schema.json` validates the shared top-level envelope.
- `context-snapshot.schema.json` validates entities, relations, facts, poses,
  evidence, and observation freshness.
- `predicate-expression.schema.json` validates the declarative predicate AST.
- `skill-contract.schema.json` validates preconditions, invariants, success
  conditions, failure conditions, timeout, cancellation, and risk fields.
- `behavior-spec.schema.json` validates composable semantic behavior
  specifications.
- `capability-profile.schema.json` validates robot and embodiment capability
  manifests.
- `invocation-request.schema.json` validates runtime invocation requests.
- `invocation-feedback.schema.json` validates runtime feedback messages.
- `invocation-result.schema.json` validates terminal runtime results.
- `trace-span.schema.json` validates lifecycle and semantic trace spans.
- `episode-annotation.schema.json` validates semantic annotations for
  robot-learning episodes.
- `provenance-record.schema.json` validates source lineage, validation gates,
  generator identity, and trust level.

These schemas are intentionally self-contained in v0.1 so the bootstrap gates
can run without a cross-file `$ref` resolver. Shared definitions may be factored
out after the SDK and conformance runner provide deterministic resolver support.

## Conformance Direction

JSON Schema validation is only the first gate. OEBP also needs deterministic
semantic validation for identifiers, registry references, graph bounds, resource
conflicts, capability matching, unit and frame compatibility, risk policy,
adapter availability, trace continuity, and provenance completeness.

Future schema changes that affect compatibility should use the RFC process.
