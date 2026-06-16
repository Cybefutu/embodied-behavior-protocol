# OEBP Architecture Review

Status: Design rationale for the v0.1 baseline
Scope: `spec/v0.1/SPEC.md`, `schemas/v0.1/`, examples, SDK, conformance, and governance files
Purpose: document the smallest rigorous v0.1 boundary for community review

## Executive Summary

OEBP has a strong central thesis: semantic behavior contracts should sit between
high-level goals and embodiment-specific execution, and every behavior should be
validated before it can run. The proposal is promising, but v0.1 currently
mixes normative protocol semantics, implementation architecture, transport
bindings, dataset tooling, LLM-assisted generation, benchmark design, and
future SDK plans in one large document.

The highest-risk issue is scope coupling. If v0.1 tries to standardize semantic
contracts, behavior composition, capability matching, runtime lifecycle,
traces, dataset annotation, LLM data generation, ROS 2 bindings, Protobuf
equivalence, SDKs, and conformance all at once, the result will be broad but
under-tested. The first release should instead prove one narrow portability
claim: the same validated semantic behavior can compile to two materially
different mock robot embodiments, execute through a deterministic lifecycle, and
emit comparable traces.

## Ten Material Ambiguities And Risks

1. Normative scope is not separated from reference implementation scope.
   The specification describes registries, SDKs, compilers, runtimes, ROS 2,
   datasets, generators, and benchmarks without consistently marking what an
   implementation MUST support for v0.1 conformance.

2. Behavior composition semantics are underspecified.
   Sequence, fallback, retry, parallel, monitor, timeout, and guard semantics
   need precise state transitions, terminal states, cancellation propagation,
   resource lock behavior, and trace obligations. Parallel behavior is
   especially risky without deterministic conflict and failure rules.

3. Skill contracts do not yet define a complete type system.
   Inputs, outputs, entity references, typed values, units, frames, uncertainty,
   and optional fields need a minimal formal model before schemas can prevent
   adapter-specific interpretation drift.

4. Capability matching is too informal.
   The proposal states that behavior requirements are matched against robot
   profiles, but it does not yet define required matching operators, partial
   support semantics, quality thresholds, frame requirements, unit conversion
   obligations, or deterministic rejection codes.

5. Predicate evaluation mixes observed facts, derived facts, and policy gates.
   Predicates such as `reachable_by` and `safety_envelope_ok` may come from
   sensors, planners, simulations, adapters, or safety supervisors. v0.1 needs
   evidence provenance and freshness rules for each source class.

6. Safety responsibility could be misread.
   OEBP validation is necessary but not sufficient for physical execution. The
   spec must repeatedly state that independent safety supervisors, emergency
   stops, hardware limits, operator approval, and site policies remain outside
   the protocol runtime and cannot be bypassed.

7. Dataset annotation scope could outrun runtime proof.
   Training-data views, provenance, low-level action tokens, preference data,
   and LLM-generated traces are useful, but they should not become normative
   before the runtime trace model is proven.

8. LLM-assisted generation is underspecified as an untrusted pipeline.
   The proposal correctly says generated behavior must be validated, but it
   still needs hard separation between proposal generation, schema validation,
   semantic validation, capability compilation, mock or simulation execution,
   human review, and release into fixture datasets.

9. Registry governance is not executable yet.
   Core identifiers such as skills, predicates, errors, and capabilities need
   versioning rules, ownership rules, deprecation rules, collision handling, and
   graduation criteria from extension namespaces into `oebp.*`.

10. Conformance evidence is currently aspirational.
    The acceptance criteria are strong, but v0.1 needs a minimal executable
    conformance suite with valid fixtures, invalid fixtures, lifecycle
    scenarios, capability mismatch cases, and trace checks before any standard
    claims are credible.

## Delete, Simplify, Or Defer

Delete from normative v0.1:

- any implication that natural-language explanations prove correctness;
- any pathway that allows arbitrary source code inside core behavior documents;
- any claim that OEBP guarantees physical executability across all robots;
- any conformance claim that is not backed by deterministic tests.

Simplify for v0.1:

- support one canonical exchange format: JSON documents validated by JSON Schema
  plus semantic validation;
- support a small expression AST: `all`, `any`, `not`, `exists`, `predicate`,
  `compare`, `capability`, and `fresh`;
- support a minimal behavior graph: `invoke`, `sequence`, `fallback`, `retry`,
  `timeout`, and `guard`;
- make `parallel` experimental until resource conflict and cancellation rules
  are tested;
- make transport binding documents non-normative design notes;
- make dataset conversion non-normative until trace semantics are stable.

Defer from core v0.1:

- full ROS 2 message/action definitions;
- Protobuf schema parity;
- C++ SDK;
- production robot adapters;
- real simulator task generation;
- learned action token codec standardization;
- benchmark leaderboard design;
- automatic registry publication;
- stable public release declaration.

## Protocol-Native Composition Versus Behavior Trees

OEBP should not directly adopt BehaviorTree.CPP semantics as the normative core
for v0.1. Behavior trees are a mature execution pattern, but OEBP's main
standardization target is the contract between semantic intent, validation,
capability matching, execution lifecycle, and traces. A direct behavior-tree
adoption would import implementation-specific blackboard, ticking, decorator,
and plugin assumptions that are not necessary for protocol interoperability.

Recommended approach:

- Define protocol-native behavior graph semantics in a small deterministic IR.
- Provide a behavior-tree binding as a non-normative adapter target.
- Require each OEBP node to have stable node IDs, bounded execution semantics,
  terminal states, resource declarations, and trace spans.
- Permit behavior-tree runtimes to execute OEBP graphs only after compilation
  proves semantic equivalence for the supported node subset.

Decision:

- v0.1 SHOULD define protocol-native composition.
- v0.1 MAY provide a BehaviorTree.CPP mapping document.
- v0.1 MUST NOT require a behavior-tree engine for conformance.

## Threat Model

### Assets

- robot safety and operator trust;
- semantic behavior documents;
- capability profiles;
- registry identifiers;
- adapter bindings;
- execution traces;
- dataset annotations;
- conformance fixtures;
- provenance records.

### Trust Boundaries

- LLM or planner output enters as untrusted behavior proposals.
- Capability profiles may be inaccurate, stale, or vendor-biased.
- Context facts may be stale, spoofed, or derived from uncertain perception.
- Registries may contain malicious, conflicting, or ambiguous identifiers.
- Adapters may mis-map parameters, frames, units, resources, or results.
- Dataset traces may be tampered with or detached from raw evidence.

### Required Controls

- Every external behavior document MUST pass schema validation before semantic
  validation.
- Every semantic behavior MUST pass registry, type, capability, resource,
  timeout, recovery, and risk validation before compilation.
- Every compiled plan MUST bind to an explicit adapter and record the adapter
  version.
- Every runtime invocation MUST have a bounded lifecycle and terminal result.
- Every recovery path MUST have bounded activation counts.
- Every generated-data record MUST include provenance and validator versions.
- OEBP MUST NOT execute source code embedded in behavior documents.
- OEBP MUST NOT claim physical safety without an external safety supervisor.

## What OEBP Standardizes

OEBP v0.1 should standardize:

- protocol envelope and versioning;
- canonical identifier and namespace rules;
- typed values, SI units, frames, time, and uncertainty representation;
- context entities, relations, evidence references, and freshness;
- predicate expression AST and deterministic evaluation result shape;
- behavior contract fields and risk metadata;
- behavior graph node types and terminal states;
- capability profile structure;
- capability matching result shape and stable rejection codes;
- invocation request, acceptance, feedback, cancellation, timeout, recovery, and
  result semantics;
- trace span shape and semantic node correlation;
- extension namespace rules;
- conformance fixture categories and minimum gates.

## What Remains Implementation-Specific

OEBP v0.1 should leave implementation-specific:

- robot middleware and transport details;
- native skill implementation;
- motion planning algorithms;
- perception models and world-model construction;
- low-level policies and action tokenizers;
- simulator internals;
- hardware safety certification;
- operator approval workflows;
- scheduling and distributed execution;
- registry hosting;
- SDK language ergonomics beyond the reference implementation.

## Recommended v0.1 Scope

The v0.1 proof should be intentionally narrow.

Required:

- normative core specification using MUST, MUST NOT, SHOULD, SHOULD NOT, and MAY;
- JSON Schemas for the core document types defined by the v0.1 protocol scope;
- Python reference SDK using standard library or a documented minimal dependency;
- deterministic validator with stable findings;
- compiler with capability matching and adapter selection;
- deterministic mock runtime with lifecycle, feedback, cancellation, timeout,
  and bounded recovery;
- two materially different mock adapters;
- one shared pick-and-place behavior that compiles to both adapters;
- one unsupported variation that produces a precise capability error;
- valid and invalid fixtures;
- conformance command;
- documentation separating implemented standard features from experimental or
  deferred features.

Experimental in v0.1:

- ROS 2 binding design;
- Protobuf equivalence;
- dataset conversion tools;
- LLM-assisted scenario and behavior proposal pipeline;
- generated failure and recovery data;
- benchmark scoring beyond local conformance.

Out of scope for v0.1:

- physical robot execution;
- production safety certification;
- public standard stabilization;
- registry governance beyond local files;
- real model API dependence;
- real simulator code generation.

## Decision Matrix

| Decision Area | Recommendation | Rationale | v0.1 Status |
|---|---|---|---|
| JSON Schema | Use Draft 2020-12 for document shape validation | Human-readable, tooling-friendly, and compatible with fixtures | Normative |
| Semantic validation | Implement deterministic Python validator | JSON Schema cannot check references, capability matching, graph bounds, or safety policy | Normative |
| Protobuf | Defer to equivalence design | Useful for transport, but premature before JSON semantics stabilize | Experimental |
| ROS 2 | Provide mapping design, not required runtime | Important ecosystem target, but should not define core semantics | Experimental |
| Python SDK | Implement first | Fastest path to validators, compiler, runtime, fixtures, and conformance | Normative reference |
| C++ SDK | Defer | Valuable for robotics deployment, but too costly before semantics stabilize | Deferred |
| Behavior tree binding | Provide mapping after IR is stable | Helps adoption without inheriting engine-specific semantics | Experimental |
| LLM generation | Treat as untrusted proposal pipeline | Useful for data scale, but cannot replace deterministic gates | Experimental |
| Dataset annotation | Define minimal trace-linked package | Needed for learning use cases, but should follow runtime trace proof | Experimental |
| Conformance | Build early and keep deterministic | Only executable tests make cross-embodiment claims credible | Normative |

## First Implementation Boundary

The next implementation work should not start by building adapters or runtime
features in isolation. It should proceed in this order:

1. Split the normative core from exploratory sections.
2. Add complete core schemas and fixtures.
3. Implement semantic validator findings.
4. Implement capability matching and compiler reports.
5. Implement mock runtime lifecycle.
6. Add two adapters and cross-embodiment tests.
7. Add LLM proposal pipeline gates after validation and runtime gates exist.
8. Publish a concise status section that separates implemented, experimental,
   and deferred features.

This order keeps the standard honest: every implemented behavior must be
traceable back to a normative requirement and a deterministic conformance gate.
