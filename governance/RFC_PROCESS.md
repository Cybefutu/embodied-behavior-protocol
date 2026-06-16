# RFC Process

RFCs are used for protocol-level changes that affect OEBP semantics,
compatibility, conformance, or governance.

## Lifecycle

1. Draft: a contributor opens an RFC pull request using `rfcs/0000-template.md`.
2. Discussion: reviewers identify ambiguity, compatibility risk, and missing tests.
3. Trial implementation: when possible, the RFC is exercised in schemas, fixtures,
   validators, adapters, or examples.
4. Accepted: maintainers agree the change is ready to become normative or
   scheduled for a release.
5. Superseded or withdrawn: the RFC is replaced, abandoned, or deferred.

## RFCs Are Required For

- new core skill families;
- behavior composition semantics;
- lifecycle state changes;
- capability matching semantics;
- registry graduation into `oebp.*`;
- breaking schema changes;
- conformance requirements;
- security or safety trust-boundary changes.

## Acceptance Criteria

An RFC should include:

- motivation and problem statement;
- exact normative change;
- examples;
- compatibility impact;
- safety and security impact;
- validation and conformance plan;
- alternatives considered.

Accepted RFCs should be linked from the affected specification sections and any
related ADRs.

