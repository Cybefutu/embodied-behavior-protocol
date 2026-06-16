# OEBP Project Charter

## Mission

OEBP exists to define an open, explainable, composable, and cross-embodiment
protocol for robot and embodied-agent behavior.

## Scope

OEBP standardizes:

- semantic behavior contracts;
- behavior graph composition semantics;
- capability profiles and matching;
- lifecycle, feedback, cancellation, and result semantics;
- trace and dataset annotation concepts;
- extension, versioning, and conformance rules.

OEBP does not standardize:

- universal joint-level action spaces;
- hardware safety certification;
- proprietary robot SDK internals;
- simulator implementation details;
- model provider APIs;
- free-form executable code generation.

## Decision Principles

- Prefer testable semantics over broad abstractions.
- Prefer cross-embodiment evidence over single-robot convenience.
- Prefer explicit trust boundaries over implicit safety claims.
- Prefer stable identifiers and versioning over display names.
- Prefer conformance fixtures over prose-only agreement.

## Roles

- Contributors propose changes, examples, tests, and implementations.
- Maintainers triage issues, review pull requests, and protect project scope.
- Editors keep normative text, schemas, registry entries, and conformance tests aligned.
- Working groups may form around schemas, ROS 2 bindings, datasets, safety, or adapters.

## Graduation to Core

A proposed core feature should have:

- clear normative semantics;
- schema or validator coverage where applicable;
- at least two implementation or adapter paths when cross-embodiment behavior is claimed;
- conformance fixtures;
- documented safety and compatibility impact.

