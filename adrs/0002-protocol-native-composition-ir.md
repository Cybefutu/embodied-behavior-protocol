# ADR 0002: Protocol-Native Composition IR

- Status: Accepted
- Date: 2026-06-16
- Deciders: OEBP maintainers
- Related RFCs: None

## Context

OEBP needs composable behavior semantics that can be validated, compiled,
executed, traced, and mapped to different robot embodiments. The proposal
references behavior-tree ecosystems, but direct adoption of a specific engine
would import blackboard, ticking, decorator, plugin, and runtime assumptions
that are not required for protocol interoperability.

The architecture review recommends defining a small protocol-native behavior
graph IR first, then treating behavior-tree mappings as non-normative bindings.

## Decision

OEBP v0.1 will define protocol-native composition semantics for a bounded
behavior graph IR. The initial normative subset will include:

- `invoke`;
- `sequence`;
- `fallback`;
- `retry`;
- `timeout`;
- `guard`.

`parallel` and `monitor` may be documented, but they remain experimental until
resource conflict, cancellation, failure propagation, and trace semantics are
covered by conformance tests.

Every behavior node must have a stable `node_id`, deterministic terminal
states, bounded execution semantics, and trace obligations. Loops, retries,
timeouts, and recovery activations must be bounded before execution.

Behavior-tree runtimes may be adapter or binding targets only after compilation
proves semantic equivalence for the supported subset.

## Consequences

This decision keeps OEBP independent from any one behavior-tree implementation
while preserving a path to behavior-tree execution. It also gives validators and
conformance tests a small, explicit semantic surface.

The cost is that OEBP must define its own execution-state semantics rather than
delegating them to existing behavior-tree documentation.

## Alternatives Considered

### Directly Adopt BehaviorTree.CPP Semantics

Rejected for the normative core. BehaviorTree.CPP is a useful target, but its
engine-specific concepts should not determine the standard.

### Free-Form Workflow Graphs

Rejected. Free-form graph semantics would make bounded validation, resource
checking, cancellation, and trace conformance too ambiguous.

### Only Atomic Skill Invocations

Rejected. OEBP needs composition to prove meaningful behavior portability, but
the subset must stay small enough to validate.
