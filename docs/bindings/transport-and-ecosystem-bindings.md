# Transport And Ecosystem Bindings

Status: non-normative v0.1 binding design note.

This document explains how OEBP can map to common robot middleware and runtime
ecosystems without coupling core semantics to any one stack.

## 1. Binding Boundary

OEBP core semantics are transport-independent. A binding may choose message
formats, service names, action names, topic names, serialization, or execution
mechanisms, but it must preserve the meaning of:

- document kinds and metadata identifiers;
- behavior graph node identifiers and skill identifiers;
- capability identifiers and adapter bindings;
- invocation lifecycle states;
- terminal result states;
- finding severity, code, pointer, message, context, and remediation;
- trace span identifiers, operation names, node links, and finding links;
- provenance generator, validation gate, source reference, and trust fields.

Bindings should be thin. Robot-specific or middleware-specific behavior belongs
in adapter bindings and capability profiles, not in the core protocol.

## 2. JSON Binding

JSON with the published JSON Schemas is the v0.1 canonical exchange format for:

- human review;
- fixtures and conformance tests;
- model-generated candidate data;
- dataset metadata;
- portable behavior and capability documents;
- trace and provenance records.

JSON object field ordering is not semantically significant. Implementations
that need hashing or signatures should use a deterministic canonicalization
profile with UTF-8 encoding, sorted object keys, no insignificant whitespace,
and stable number rendering. The canonicalization profile is not finalized in
v0.1.

JSON bindings must validate documents before execution. A schema-valid document
can still fail semantic, capability, risk, runtime, or provenance gates.

## 3. Protobuf Binding

Protobuf is a candidate runtime transport for lower-latency or strongly typed
systems. It is not the source of truth for v0.1 semantics.

Semantic equivalence requirements:

- A Protobuf representation must round-trip to the canonical JSON document
  without changing semantic fields.
- Missing required JSON fields must not be silently synthesized with Protobuf
  default values during validation.
- Unknown fields may be carried by a transport, but they must not affect core
  semantics unless they are declared extension fields in an owned namespace.
- JSON enum strings and Protobuf enum values must have a documented bijection.
- JSON object maps must preserve keys exactly.
- JSON Pointer references in findings must continue to refer to the JSON
  document shape.
- Repeated fields must preserve order where OEBP semantics are ordered, such as
  behavior graph children, feedback sequences, trace events, and validation
  gates.
- Numeric units must remain explicit where the schema or capability profile
  requires units.

Recommended implementation shape:

- Define Protobuf messages mechanically from the JSON Schema surface where
  possible.
- Keep a lossless JSON import/export function beside every Protobuf binding.
- Run the conformance suite against both JSON input and Protobuf round trips.
- Treat a Protobuf-only behavior as non-conformant until it can be exported to
  schema-valid JSON.

Open issue: a formal `.proto` package and canonical JSON mapping are deferred
until at least one independent implementation validates the design.

## 4. ROS 2 Binding

ROS 2 is a transport and execution ecosystem, not the OEBP semantic core. OEBP
must not require ROS 2 concepts to define behavior meaning.

Recommended lifecycle mapping:

```text
OEBP InvocationRequest  -> ROS 2 Action Goal
OEBP InvocationFeedback -> ROS 2 Action Feedback
OEBP InvocationResult   -> ROS 2 Action Result
OEBP cancellation       -> ROS 2 Action cancel request
OEBP TraceSpan          -> trace topic, bag metadata, or side-channel log
OEBP ContextSnapshot    -> topic stream or local world-model snapshot
```

Recommended node responsibilities:

- An OEBP executor node receives InvocationRequest data.
- The executor validates schema, semantic, capability, risk, and provenance
  gates before dispatch.
- Adapter bindings map semantic skills to ROS 2 actions, services, topics, or
  local planners.
- Feedback from native ROS 2 actions is projected back into
  InvocationFeedback.
- Native action results are projected back into InvocationResult with stable
  OEBP terminal states and findings.
- Cancellation requests are propagated to the active ROS 2 action when the
  execution policy permits cancellation.

ROS 2 names are deployment details. A binding may expose generic OEBP action
types, generated per-skill action types, or adapter-specific native actions, but
the semantic skill id remains the OEBP skill identifier.

ROS 2 binding conformance should demonstrate:

- request, feedback, result, cancellation, timeout, and recovery behavior;
- stable finding codes for validation and adapter failures;
- trace links from ROS 2 action execution back to OEBP node ids;
- no requirement that OEBP core documents import ROS 2 message definitions.

## 5. Behavior-Tree Binding

Behavior-tree binding is experimental in v0.1.

The following mappings are plausible but not yet normative:

- `sequence` to a sequence control node;
- `fallback` to a selector/fallback control node;
- `retry` to a decorator with bounded attempts;
- `timeout` to a decorator with a deadline;
- `guard` to a condition plus child subtree;
- `invoke` to an action leaf that calls an OEBP skill adapter.

Deferred or unsafe areas:

- `parallel` semantics vary across behavior-tree engines and are deferred for
  normative binding until cancellation, resource conflict, and failure
  propagation rules are proven across implementations.
- Behavior-tree blackboards must not become the source of truth for OEBP
  semantic parameters, context, or trace fields.
- Native behavior-tree success and failure states are insufficient to represent
  OEBP terminal states such as canceled, preempted, timeout, unsafe, and
  internal_error.

Any behavior-tree binding must still emit OEBP InvocationFeedback,
InvocationResult, and TraceSpan documents. A behavior tree may be an execution
strategy for an adapter, but it is not a replacement for OEBP behavior graphs or
conformance tests.

## 6. Cross-Binding Conformance

A binding is a candidate for v0.1 conformance only if it can show:

- schema-valid JSON import and export;
- semantic validation parity with the reference validator;
- capability-matching parity for supported and unsupported behaviors;
- lifecycle parity for acceptance, feedback, result, cancellation, preemption,
  timeout, and recovery;
- trace alignment to OEBP behavior node ids;
- provenance preservation for generated and transformed data;
- JSON round-trip equivalence for all core document kinds it supports.

Transport-specific performance, scheduling, and driver behavior can be reported
as implementation evidence, but they do not change OEBP core semantics.
