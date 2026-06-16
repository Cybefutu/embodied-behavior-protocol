# ADR 0003: Capability Profiles And Adapter Binding

- Status: Accepted
- Date: 2026-06-16
- Deciders: OEBP maintainers
- Related RFCs: None

## Context

OEBP's portability claim depends on separating semantic behavior contracts from
embodiment-specific execution. A behavior must not execute just because it is
well formed; it must match a robot capability profile, bind to an adapter, and
pass preflight checks. Capability profiles also need to describe enough frames,
effectors, sensors, limits, and adapter bindings to make deterministic
compilation possible.

Without a precise capability and adapter boundary, vendors could claim support
for semantic skills while mapping parameters, frames, units, resources, or
result states incompatibly.

## Decision

OEBP v0.1 will require an explicit capability profile for compilation. A
capability profile describes the embodiment and declares supported semantic
capabilities, effectors, sensors, frames, safety envelopes, and adapter
bindings.

The compiler must fail closed when a required capability, resource, frame,
unit, risk policy, or adapter binding cannot be resolved. Capability matching
must produce machine-readable reports with stable rejection codes.

Adapters are implementation-specific, but their bindings to OEBP skills must be
declared in data. An adapter binding must identify:

- semantic skill identifier;
- implementation type;
- parameter map;
- result map;
- adapter or implementation version when available.

For v0.1, conformance requires two materially different mock adapters that
compile the same semantic pick-and-place behavior and report at least one
intentional unsupported variation with a precise capability error.

## Consequences

This decision makes cross-embodiment claims testable. It prevents a runtime from
executing a behavior without explicit evidence that a compatible adapter exists.

The cost is that capability profiles must be more precise than vendor marketing
descriptions. They become part of the safety and conformance surface.

## Alternatives Considered

### Runtime Discovery Only

Rejected. Runtime discovery may be useful, but v0.1 needs deterministic
fixtures and repeatable conformance tests.

### Natural-Language Capability Descriptions

Rejected. Natural language may help documentation, but it cannot drive safe
compilation.

### Adapter Code As The Source Of Truth

Rejected. Adapter code is implementation-specific and cannot replace
machine-readable capability and binding declarations.
