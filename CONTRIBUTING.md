# Contributing to OEBP

OEBP is trying to become an open, explainable, composable, cross-embodiment
behavior protocol. Contributions are welcome from robotics researchers,
robot vendors, middleware maintainers, dataset builders, safety reviewers, and
application developers.

## Contribution Types

- Specification clarifications and normative wording.
- JSON Schemas, fixtures, semantic validators, and conformance tests.
- Core skill, predicate, error, capability, and trace registry entries.
- Mock, simulation, ROS 2, gRPC, SDK, and robot-specific adapters.
- Dataset annotation and conversion utilities.
- Security, safety, threat-model, and governance improvements.
- Documentation, tutorials, diagrams, examples, and translations.

## Working Rules

- Prefer small, reviewable pull requests.
- Explain the interoperability problem before proposing a new abstraction.
- Use RFC-style terms consistently: MUST, MUST NOT, SHOULD, SHOULD NOT, MAY.
- Keep protocol semantics separate from implementation-specific behavior.
- Do not embed arbitrary executable code in core protocol documents.
- Treat model-generated behavior proposals as untrusted data.
- Add conformance fixtures for semantic changes whenever possible.
- Keep extension points namespaced under an owned namespace.

## When To Use an RFC

Open an RFC for changes that affect:

- protocol semantics;
- canonical identifiers;
- behavior graph execution rules;
- safety or trust boundaries;
- schema compatibility;
- conformance requirements;
- registry graduation from extension to core.

Small editorial fixes, examples, tests, and non-normative documentation can be
submitted directly as pull requests.

## Pull Request Checklist

- The problem statement is clear.
- The change is scoped to one topic.
- Normative text and schemas agree.
- Valid and invalid examples are updated when behavior changes.
- Security and safety implications are described.
- Compatibility impact is stated.
- Related RFCs or ADRs are linked.

## Review Culture

OEBP favors precise disagreement over vague approval. Reviewers should identify
ambiguity, cross-embodiment failure modes, hidden implementation assumptions,
and missing tests. Authors should expect iteration on terminology and scope.

