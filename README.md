# Open Embodied Behavior Protocol (OEBP)

OEBP is a proposed open standard for representing, validating, composing,
executing, and recording embodied behaviors across robots and embodied agents.

The goal is to make high-level robot behavior portable across embodiments while
keeping every behavior explainable, machine-validatable, and traceable back to
capabilities, observations, safety gates, execution feedback, and dataset
records.

```text
Context + Goal + Capability Profile
            |
            v
Explainable Behavior Contract / Behavior Graph
            |
            v
Embodiment Adapter
            |
            v
Native skill, policy, planner, action codec, or controller
            |
            v
Feedback + Result + Trace + Training Record
```

## Status

OEBP is currently a v0.1 design proposal, not a finalized industry standard.
The repository is organized so researchers, robot vendors, middleware teams,
dataset maintainers, and safety reviewers can turn the proposal into a tested,
multi-implementation standard through public RFCs and conformance work.

## Why This Exists

Robot learning and robot application stacks are fragmented across embodiment
shape, control interfaces, action spaces, sensors, simulators, datasets, and
task vocabularies. OEBP separates stable semantic intent from
embodiment-specific execution so the same behavior can be checked, compiled,
adapted, executed, and recorded across different robots.

OEBP aims to be:

- Open: public specifications, schemas, registries, RFCs, and conformance tests.
- Explainable: typed behavior contracts instead of opaque labels or free-form code.
- Composable: deterministic behavior graphs with bounded loops and recovery.
- Cross-embodiment: capability profiles and adapters bridge semantic intent to hardware.
- Data-centric: execution traces and episode annotations connect runtime to learning data.
- Safety-aware: model-generated proposals are untrusted until deterministic validation passes.

## Contents

- `spec/v0.1/core.md` - normative v0.1 core with RFC-style requirements.
- `spec/v0.1/SPEC.md` - complete v0.1 protocol architecture and design proposal.
- `schemas/v0.1/` - core JSON Schemas for OEBP documents.
- `src/oebp/` - Python SDK models, validator, compiler, mock runtime, reference adapters, generation gates, and episode helpers.
- `examples/` - minimal behavior and capability examples.
- `conformance/fixtures/` - valid and invalid schema fixtures with expected error codes.
- `datasets/synthetic/v0.1/` - small trace-linked synthetic dataset fixture using external data references.
- `registry/core-skills/v0.1/` - starting point for the core skill registry.
- `docs/` - research basis, glossary, binding notes, training-data guidance, and supporting explanations.
- `governance/` - project charter and RFC process.
- `rfcs/` - proposed normative changes.
- `adrs/` - architecture decision records.
- `scripts/validate_oebp.py` - local OEBP document validator using the SDK.
- `scripts/run_conformance.py` - deterministic conformance suite for SDK and protocol fixtures.
- `scripts/create_training_data.py` - creates JSONL training views from OEBP episode annotations.

## Start Here

1. Read the [v0.1 specification](spec/v0.1/SPEC.md).
2. Run through the examples in [examples/](examples/).
3. Validate an example with `python3 scripts/validate_oebp.py examples/pick-and-place.behavior.json`.
4. Try the reference CLI with `PYTHONPATH=src python3 -m oebp.cli conformance run`.
5. Create training-data views with `python3 scripts/create_training_data.py --output-dir /tmp/oebp-training`.
6. Review the [roadmap](ROADMAP.md).
7. Open an issue for ambiguity, interoperability gaps, safety concerns, or implementation proposals.
8. Use the [RFC process](governance/RFC_PROCESS.md) for changes that affect protocol semantics.

## Reference CLI

The SDK exposes a console entry point named `oebp` when the package is
installed. From a source checkout, use `PYTHONPATH=src python3 -m oebp.cli`.

```bash
PYTHONPATH=src python3 -m oebp.cli validate examples/pick-and-place.behavior.json
PYTHONPATH=src python3 -m oebp.cli validate-capability examples/generic-mobile-manipulator.capability.json
PYTHONPATH=src python3 -m oebp.cli compile examples/pick-and-place.behavior.json --capability examples/generic-mobile-manipulator.capability.json
PYTHONPATH=src python3 -m oebp.cli run examples/pick-and-place.behavior.json --adapter mock
PYTHONPATH=src python3 -m oebp.cli conformance run
```

## Training Data

OEBP creates training data from semantic episode annotations rather than from
raw media embedded in protocol files. The reference method keeps observation
and action streams in external storage, then emits JSONL views for planner,
next-skill, contract, recovery, and success-estimation training.

```bash
python3 scripts/create_training_data.py --output-dir /tmp/oebp-training
```

See [docs/training-data.md](docs/training-data.md) for the full method and
trust boundary.

## Protocol Logic

OEBP separates stable semantic intent from embodiment-specific execution.

1. A behavior document states the contract, graph, required capabilities,
   lifecycle expectations, recovery policy, and trace obligations.
2. A capability profile states what an embodiment can do and how semantic skills
   bind to native actions, planners, policies, middleware, or SDK calls.
3. Validation rejects malformed documents, ambiguous semantics, unsupported
   capabilities, unbounded loops, unsafe risk classes, missing adapters, and
   resource conflicts before execution.
4. Compilation chooses adapter bindings deterministically and produces an
   inspectable plan.
5. Runtime execution emits feedback, terminal results, findings, and trace spans
   aligned to semantic behavior nodes.
6. Episode annotations reference external observations and actions, preserving
   training-data lineage without duplicating raw media or low-level signals.

## How To Contribute

Good first contributions include:

- clarifying ambiguous normative language;
- adding valid and invalid fixtures for existing schemas;
- proposing canonical skill contracts;
- mapping OEBP concepts to ROS 2, BehaviorTree.CPP, LeRobot-like datasets, or robot vendor SDKs;
- writing adapters for mock, simulation, or real robot embodiments;
- adding dataset converters or training views that preserve OEBP provenance;
- contributing conformance tests that expose portability or safety gaps.

See [CONTRIBUTING.md](CONTRIBUTING.md) for the workflow and review expectations.

## Standards Principles

- The written specification defines semantics; reference code demonstrates them.
- Conformance tests are part of the standard, not optional examples.
- Vendor and lab extensions must use owned namespaces.
- Experimental features must be clearly labeled and cannot silently redefine core behavior.
- A core feature should graduate only after multi-implementation evidence.

## License

OEBP uses a dual-license intent:

- Specification, registry text, diagrams, and documentation: CC BY 4.0.
- Schemas, examples, validators, SDKs, adapters, and tools: Apache-2.0.

See [LICENSE.md](LICENSE.md). Contributions should follow the same split unless a
file states otherwise.
