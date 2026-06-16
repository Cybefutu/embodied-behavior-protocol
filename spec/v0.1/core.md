# OEBP v0.1 Normative Core

Status: Draft normative core

Applies to: OEBP v0.1 conformance work

Companion design proposal: [SPEC.md](SPEC.md)

## 1. Requirement Language

The key words MUST, MUST NOT, REQUIRED, SHALL, SHALL NOT, SHOULD, SHOULD NOT,
RECOMMENDED, NOT RECOMMENDED, MAY, and OPTIONAL in this document are to be
interpreted as described in BCP 14 when, and only when, they appear in all
capitals.

Non-normative notes are explicitly labeled as "Non-normative".

## 2. Conformance Categories

Each normative requirement is tagged with one or more conformance categories.

- `schema`: document shape, required fields, type constraints, and structural
  bounds.
- `semantic`: identifiers, references, predicates, graph structure, resources,
  units, frames, risk, and safety policy.
- `capability`: capability profile matching and adapter-binding selection.
- `runtime`: invocation lifecycle, feedback, cancellation, timeout, result, and
  recovery behavior.
- `trace`: trace span, evidence, provenance, and dataset correlation.
- `security`: trust boundaries, arbitrary-code prevention, and unsafe execution
  prevention.
- `extension`: namespace, versioning, and compatibility behavior.

## 3. Conformance Classes

OEBP v0.1 defines the following conformance classes.

- Document Producer: emits OEBP documents.
- Schema Validator: validates OEBP document shape.
- Semantic Validator: validates OEBP semantics beyond JSON Schema.
- Compiler: matches behavior to capability profiles and adapter bindings.
- Runtime: executes compiled plans through a bounded lifecycle.
- Adapter: maps semantic skills to native robot, simulator, policy, planner, or
  middleware operations.
- Trace Producer: emits trace and provenance records.

An implementation MUST declare which conformance classes it implements.

## 4. Protocol Envelope

REQ-ENV-001 [schema]: Every top-level OEBP document MUST be a JSON object with
`protocol`, `version`, `kind`, `metadata`, and `spec` fields unless a more
specific schema explicitly defines a different top-level shape.

REQ-ENV-002 [schema]: The `protocol` field MUST equal `oebp`.

REQ-ENV-003 [schema]: The `version` field MUST identify the OEBP protocol
version used by the document.

REQ-ENV-004 [schema, extension]: The `kind` field MUST identify the document
kind and MUST be constrained by the corresponding schema.

REQ-ENV-005 [schema]: `metadata.id` and `metadata.revision` MUST be present in
all core top-level documents.

## 5. Identifiers And Namespaces

REQ-ID-001 [semantic, extension]: Core identifiers MUST use the `oebp.`
namespace.

REQ-ID-002 [semantic, extension]: Non-core extensions MUST use an owned
namespace that does not begin with `oebp.`.

REQ-ID-003 [semantic, extension]: A breaking semantic change to a registered
identifier MUST create a new major contract version.

REQ-ID-004 [semantic]: Display names, comments, and natural-language aliases
MUST NOT replace canonical identifiers.

## 6. Values, Units, Frames, And Time

REQ-VALUE-001 [semantic]: Canonical physical quantities MUST use SI units unless
a schema explicitly defines a different unit.

REQ-VALUE-002 [semantic]: A pose MUST identify its coordinate frame.

REQ-VALUE-003 [semantic]: A validator MUST reject implicit frame assumptions
when a behavior requires frame-dependent execution.

REQ-VALUE-004 [semantic, trace]: Observed or derived facts SHOULD include
timestamp, source, confidence, and freshness metadata when available.

REQ-VALUE-005 [semantic]: Stale facts MUST NOT satisfy preconditions unless the
behavior contract or policy explicitly permits stale data.

## 7. Context And Evidence

REQ-CTX-001 [schema, semantic]: Context entities MUST have stable entity IDs
within the document or episode scope.

REQ-CTX-002 [semantic]: Relations MUST identify predicate, subject, and object
where the relation type requires an object.

REQ-CTX-003 [semantic, trace]: Derived predicates SHOULD record evidence and
derivation source.

REQ-CTX-004 [security]: Untrusted context sources MUST NOT be treated as
authoritative without validation or policy approval.

## 8. Predicate Expressions

REQ-PRED-001 [schema, semantic]: Predicate expressions MUST use the declarative
AST forms defined by the active schema.

REQ-PRED-002 [security]: Predicate expressions MUST NOT embed executable source
code.

REQ-PRED-003 [semantic]: Predicate evaluation MUST return a deterministic result
for a fixed context, fixed capability profile, fixed policy, and fixed evidence
set.

REQ-PRED-004 [semantic]: Predicate evaluation failures MUST be reported as
structured findings rather than silently coerced to success.

## 9. Behavior Contracts

REQ-CONTRACT-001 [schema]: A behavior contract MUST define preconditions,
invariants, success conditions, failure conditions, and timeout semantics.

REQ-CONTRACT-002 [schema, semantic]: A behavior contract MUST define at least
one success condition.

REQ-CONTRACT-003 [runtime]: Every physical skill invocation MUST define
cancellation behavior, either directly or through a referenced skill contract.

REQ-CONTRACT-004 [security]: A behavior contract MUST NOT claim physical
feasibility from natural-language text alone.

REQ-CONTRACT-005 [semantic]: Risk metadata MUST be evaluated before compilation
or execution.

## 10. Behavior Graph Composition

REQ-GRAPH-001 [schema, semantic]: Every behavior graph node MUST have a stable
`node_id` within the behavior document.

REQ-GRAPH-002 [semantic]: Graph cycles MUST be rejected unless represented by a
bounded construct explicitly allowed by the schema and semantic validator.

REQ-GRAPH-003 [semantic, runtime]: Retry counts, loop counts, recovery
activation counts, and timeout values MUST be bounded.

REQ-GRAPH-004 [runtime, trace]: Every executed node MUST produce traceable
lifecycle evidence.

REQ-GRAPH-005 [semantic]: Parallel execution MUST be treated as experimental
until resource conflict, cancellation, and failure-propagation semantics are
covered by conformance tests.

## 11. Capability Profiles And Adapter Binding

REQ-CAP-001 [schema]: A capability profile MUST describe embodiment ID,
embodiment class, effectors, sensors, frames, capabilities, and adapter bindings.

REQ-CAP-002 [capability]: A compiler MUST verify that all required behavior
capabilities are supported by the selected capability profile.

REQ-CAP-003 [capability]: A compiler MUST fail closed when a required adapter
binding cannot be selected.

REQ-CAP-004 [capability, semantic]: Unit and frame mappings MUST be explicit
when native adapter representations differ from canonical OEBP values.

REQ-CAP-005 [capability]: Capability mismatch reports MUST be machine-readable
and SHOULD include stable rejection codes.

## 12. Invocation Lifecycle

REQ-LIFE-001 [runtime]: Runtime execution MUST begin with an explicit invocation
request or compiled plan reference.

REQ-LIFE-002 [runtime]: A runtime MUST produce an acceptance or rejection result
before executing physical or simulated actions.

REQ-LIFE-003 [runtime]: A runtime SHOULD emit feedback for long-running
behaviors.

REQ-LIFE-004 [runtime]: A runtime MUST support cancellation for accepted
invocations.

REQ-LIFE-005 [runtime]: A runtime MUST enforce timeouts declared by contracts or
compiled plans.

REQ-LIFE-006 [runtime]: Every invocation MUST terminate in exactly one terminal
result state.

REQ-LIFE-007 [runtime]: Recovery behavior MUST be bounded and MUST NOT repeat
indefinitely.

## 13. Results, Errors, And Findings

REQ-ERR-001 [semantic, runtime]: Validation, compilation, and runtime failures
MUST be reported as structured findings or results.

REQ-ERR-002 [semantic]: Findings MUST include severity, stable code, JSON
Pointer when applicable, message, and machine-readable context.

REQ-ERR-003 [runtime]: Runtime results MUST distinguish success, failure,
cancellation, preemption, timeout, unsafe termination, and internal error where
the implementation supports those states.

REQ-ERR-004 [trace]: Error and recovery traces MUST preserve the link to the
semantic node that produced or handled the error.

## 14. Trace And Provenance

REQ-TRACE-001 [trace]: Trace spans MUST identify the semantic node or lifecycle
operation they describe.

REQ-TRACE-002 [trace]: Trace records SHOULD include evidence references when a
decision depends on perception, planning, policy, simulation, or human review.

REQ-TRACE-003 [trace]: Generated or transformed data MUST include provenance
sufficient to identify generator type, validator versions, and source lineage.

REQ-TRACE-004 [security, trace]: Trace and provenance data MUST NOT be used to
justify bypassing validation gates.

## 15. Security And Safety

REQ-SEC-001 [security]: Model-generated OEBP documents MUST be treated as
untrusted data.

REQ-SEC-002 [security]: OEBP documents MUST NOT embed arbitrary executable code
for the core runtime to execute.

REQ-SEC-003 [security]: A behavior proposal MUST NOT execute before required
schema, semantic, capability, risk, and adapter gates pass for the selected
conformance class.

REQ-SEC-004 [security]: OEBP validation MUST NOT be represented as a complete
physical safety guarantee.

REQ-SEC-005 [security]: Real robot execution MUST remain subject to independent
safety supervisors, hardware limits, emergency stop behavior, and deployment
policy.

REQ-SEC-006 [security]: Implementations SHOULD NOT mark model-generated
documents as trusted solely because they pass JSON Schema validation.

## 16. Extension And Versioning

REQ-EXT-001 [extension]: Extensions MAY add namespaced identifiers and fields
only where the active schema permits extension.

REQ-EXT-002 [extension]: Extensions MUST NOT redefine `oebp.*` core semantics.

REQ-EXT-003 [extension]: Experimental features MUST be labeled as experimental
and MUST NOT be required for core v0.1 conformance.

REQ-EXT-004 [extension]: A future version MUST preserve compatibility or provide
documented migration guidance when schemas or semantics change.

## 17. Experimental And Non-Normative Areas

The following areas are experimental in v0.1 unless later promoted by an
accepted RFC, ADR, and conformance tests:

- ROS 2 bindings;
- Protobuf equivalence;
- behavior-tree runtime bindings;
- dataset converters;
- LLM-assisted data generation;
- learned action token codecs;
- production robot adapters;
- benchmark leaderboards.

Non-normative note: these areas are important for ecosystem adoption, but they
must not define the core protocol before the semantic model, schemas, validator,
compiler, runtime, and two-adapter proof are working.

## 18. Conformance Trace Table

The following table is normative for v0.1 traceability. A conformance claim MUST
cite the requirement IDs it satisfies for each implemented class.

| Category | Primary requirements |
| --- | --- |
| `schema` | REQ-ENV-001 through REQ-ENV-005, REQ-CTX-001, REQ-PRED-001, REQ-CONTRACT-001 through REQ-CONTRACT-002, REQ-GRAPH-001, REQ-CAP-001 |
| `semantic` | REQ-ID-001 through REQ-ID-004, REQ-VALUE-001 through REQ-VALUE-005, REQ-CTX-001 through REQ-CTX-003, REQ-PRED-001 and REQ-PRED-003 through REQ-PRED-004, REQ-CONTRACT-002 and REQ-CONTRACT-005, REQ-GRAPH-001 through REQ-GRAPH-003 and REQ-GRAPH-005, REQ-CAP-004, REQ-ERR-001 through REQ-ERR-002 |
| `capability` | REQ-CAP-002 through REQ-CAP-005 |
| `runtime` | REQ-CONTRACT-003, REQ-GRAPH-003 through REQ-GRAPH-004, REQ-LIFE-001 through REQ-LIFE-007, REQ-ERR-001, REQ-ERR-003 |
| `trace` | REQ-VALUE-004, REQ-CTX-003, REQ-GRAPH-004, REQ-ERR-004, REQ-TRACE-001 through REQ-TRACE-004 |
| `security` | REQ-CTX-004, REQ-PRED-002, REQ-CONTRACT-004, REQ-SEC-001 through REQ-SEC-006, REQ-TRACE-004 |
| `extension` | REQ-ENV-004, REQ-ID-001 through REQ-ID-003, REQ-EXT-001 through REQ-EXT-004 |
