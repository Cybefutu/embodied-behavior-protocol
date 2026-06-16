# Glossary

## Adapter

An implementation layer that maps OEBP semantic skill invocations to a native
robot, simulator, middleware, policy, planner, SDK, or action codec.

## Behavior Contract

A typed, explainable contract for a skill or composite behavior, including
inputs, outputs, preconditions, invariants, success conditions, failure
conditions, cancellation behavior, resources, and risk metadata.

## Behavior Graph

A deterministic composition of behavior nodes using bounded control-flow
operators such as sequence, fallback, retry, timeout, guard, and parallel.

## Capability Profile

A machine-readable description of an embodiment's effectors, sensors, frames,
skills, limits, adapter bindings, and safety envelopes.

## Conformance

Evidence that an implementation follows the normative specification through
schemas, semantic validation, lifecycle behavior, adapter behavior, traces, and
fixtures.

## Embodiment

The physical or simulated body that executes behavior, including its sensors,
effectors, frames, constraints, and native control interfaces.

## Evidence

A reference to observations, model outputs, planner checks, simulation results,
human review, or runtime feedback used to justify a predicate, decision, result,
or trace event.

## Registry

A versioned catalog of canonical identifiers such as skills, predicates, error
codes, capability names, and trace fields.

## Trace Span

A structured runtime record that connects a semantic node to feedback, result,
evidence, errors, recovery, and low-level action references.

