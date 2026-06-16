# Roadmap

This roadmap is intentionally standards-oriented. The first milestone is not a
large SDK; it is a narrow, testable protocol slice that multiple independent
implementations can validate.

## Milestone 0: Repository Foundation

- Contributor guide, governance, RFC process, ADR template, issue templates.
- Versioned locations for spec, schemas, examples, registry entries, and roadmap.
- Clear licensing intent and security/safety reporting.

## Milestone 1: Normative v0.1 Core

- Split the current design proposal into smaller normative documents.
- Define envelope, identifiers, units, frames, time, uncertainty, context,
  predicates, behavior contracts, composition, capability matching, lifecycle,
  traces, extensions, and trust boundaries.
- Use RFC-style terms consistently.

## Milestone 2: Schema and Fixture Conformance

- Expand JSON Schema Draft 2020-12 coverage.
- Add valid and invalid fixtures for each schema.
- Separate schema validity from semantic validity.
- Publish stable error codes.

## Milestone 3: Reference Validator and Compiler

- Implement deterministic validation.
- Implement capability matching and adapter selection.
- Reject cycles, unbounded retries, resource conflicts, unsafe risk classes,
  unresolved entity references, and missing adapters before execution.

## Milestone 4: Two Embodiment Demonstration

- Provide two materially different mock or simulation adapters.
- Compile the same semantic pick-and-place behavior to both.
- Show at least one precise capability mismatch.
- Emit equivalent semantic results and trace spans.

## Milestone 5: Transport and Dataset Bindings

- Design ROS 2 action mappings without coupling the core protocol to ROS 2.
- Define JSON and Protobuf semantic equivalence.
- Add OEBP episode annotations for a LeRobot-like fixture dataset.

## Milestone 6: Public RFC Release

- Publish a v0.1 RFC bundle.
- Run public review across robotics, middleware, safety, and dataset communities.
- Freeze the first conformance targets.
- Start collecting independent implementation reports.

