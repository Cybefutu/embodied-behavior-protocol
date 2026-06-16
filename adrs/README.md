# Architecture Decision Records

ADRs capture material OEBP protocol and implementation decisions.

## Lifecycle

- Proposed: under review and not yet authoritative.
- Accepted: project direction unless superseded by a later ADR.
- Superseded: replaced by a newer decision.
- Withdrawn: abandoned before acceptance.

## Required For

- serialization format decisions;
- behavior composition semantics;
- capability matching and adapter binding;
- lifecycle, cancellation, timeout, and recovery semantics;
- schema compatibility and migration rules;
- evaluator or conformance policy changes;
- security and safety trust-boundary changes.

## Accepted Records

- [ADR 0001: JSON Schema Plus Deterministic Semantic Validation](0001-json-schema-and-semantic-validation.md)
- [ADR 0002: Protocol-Native Composition IR](0002-protocol-native-composition-ir.md)
- [ADR 0003: Capability Profiles And Adapter Binding](0003-capability-profile-and-adapter-binding.md)

Use [0000-template.md](0000-template.md) for new records.
