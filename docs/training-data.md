# Training Data Creation

OEBP training data is created from validated behavior, capability, runtime,
trace, episode, and provenance documents. Raw observations, videos, and
low-level action streams stay in their original storage system. OEBP records
refer to them through stable `observation_ref` and `action_ref` values.

This keeps semantic training labels portable while avoiding duplicated media,
hidden licensing changes, or accidental mixing of trusted and untrusted data.

## Data Creation Flow

1. Create or collect an embodied episode in a simulator, mock runtime, or robot
   dataset.
2. Validate the behavior document, capability profile, invocation result, trace
   spans, and provenance record.
3. Build an `EpisodeAnnotation` that links:
   - behavior ID;
   - capability profile ID;
   - source dataset ID;
   - trace reference;
   - observation reference;
   - action reference;
   - action codec;
   - outcome;
   - quality labels;
   - provenance.
4. Run `scripts/create_training_data.py` to emit JSONL training views.
5. Review generated records before publishing or using them for model training.

## Reference Command

```bash
python3 scripts/create_training_data.py \
  --manifest datasets/synthetic/v0.1/manifest.json \
  --behavior examples/pick-and-place.behavior.json \
  --capability examples/generic-mobile-manipulator.capability.json \
  --output-dir /tmp/oebp-training
```

The command creates:

- `planner.jsonl`: context and capability input to target behavior graph.
- `next_skill.jsonl`: behavior history to next semantic skill and parameters.
- `contract.jsonl`: contract condition records for preconditions, invariants,
  success conditions, and failure conditions.
- `recovery.jsonl`: error-code and trace context to recovery behavior.
- `success_estimation.jsonl`: observation and contract context to outcome labels.
- `index.json`: counts, source manifest, and generated file list.

## Safety And Trust Rules

- Generated training rows MUST NOT embed raw observations, videos, or action
  streams.
- Model-generated behaviors are untrusted until schema, semantic, capability,
  runtime, and provenance gates pass.
- A successful mock run is evidence for protocol semantics, not physical safety.
- Dataset releases should preserve source dataset IDs, licenses, and provenance.
- Human review is required before generated data is promoted into public
  training datasets.

## Training Views

Planner records teach a model to propose a behavior graph for a context,
capability profile, and goal.

Next-skill records teach a model to choose the next semantic skill and
parameters from behavior history.

Contract records teach a model or evaluator which predicates must hold before,
during, or after behavior execution.

Recovery records teach bounded recovery choices for known failure codes.

Success-estimation records teach outcome prediction from observation references,
behavior contracts, and quality labels.
