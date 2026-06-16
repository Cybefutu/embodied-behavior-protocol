# Open Embodied Behavior Protocol (OEBP) v0.1

Status: Design proposal. The initial normative core is maintained in
`spec/v0.1/core.md`.

## 0. Document purpose

OEBP is a proposed open protocol for representing, composing, executing, validating, recording, and learning embodied behaviors across different robot embodiments.

Its central abstraction is:

```text
Context + Goal + Capability Profile
            v
Explainable Behavior Contract / Behavior Graph
            v
Embodiment Adapter
            v
Native skill, policy, motion planner, action codec, or controller
            v
Feedback + Result + Trace + Training Record
```

The protocol is designed to support two complementary uses:

1. Runtime interoperability: a planner or model can request a semantic behavior without knowing each robot's joints or proprietary control interface.
2. Dataset interoperability: demonstrations, synthetic episodes, failures, recoveries, and action chunks can share a common semantic annotation layer.

OEBP does not attempt to replace robot middleware, physics simulators, low-level control, or learned policies. It defines the contract between semantic intent, execution, embodiment-specific realization, and data traces.

---

# 1. Problem statement

Robot learning data is fragmented along several axes:

- Different robots expose different joint spaces, end-effectors, sensors, control frequencies, and coordinate frames.
- Similar physical behaviors are described with inconsistent task names and language.
- Datasets usually contain observations and actions but insufficient semantic information about preconditions, effects, success, failure, and recovery.
- High-level planners often emit free-form language or executable code that is difficult to validate safely.
- Low-level action tokenizers can compress trajectories but their tokens are generally not human-interpretable.
- Synthetic data generation can scale task diversity, but generated examples may be physically impossible, semantically inconsistent, unsafe, duplicated, or poorly grounded.

OEBP addresses these issues by separating stable semantic meaning from embodiment-specific execution.

---

# 2. Goals and non-goals

## 2.1 Goals

OEBP must be:

1. Open: implementation-neutral, license-friendly, and governed through public schemas, registries, conformance tests, and RFCs.
2. Explainable: each behavior has a stable identifier, typed parameters, preconditions, invariants, success conditions, failure conditions, evidence, and result.
3. Composable: atomic skills can be combined using deterministic control-flow operators.
4. Cross-embodiment: behavior requirements are matched against a robot capability profile and compiled through an adapter.
5. Model-friendly: records can be serialized into compact tokens or structured sequences for model training and inference.
6. Safety-aware: generated plans are untrusted until validated; runtime safety supervision remains external and non-bypassable.
7. Data-centric: every execution can produce a trace suitable for behavior cloning, planning, recovery learning, reward modeling, or evaluation.
8. Extensible: vendors and research groups can add namespaced skills and fields without breaking the core protocol.

## 2.2 Non-goals

OEBP v0.1 will not:

- Define a universal joint-level action space.
- Guarantee that a semantic skill is physically executable on every robot.
- Replace ROS 2, DDS, gRPC, OPC UA, simulators, motion planners, or behavior-tree engines.
- Permit arbitrary executable code inside behavior messages.
- Treat natural-language explanations as proof of correctness.
- Standardize every possible household, industrial, medical, or autonomous-driving behavior in the first release.
- Allow a large model to bypass capability, safety, or physics validation.

---

# 3. Design principles

## 3.1 Semantic core, optional learned lower layer

The core protocol uses explicit skills such as `navigate_to`, `reach`, `grasp`, `place`, and `verify`. An embodiment adapter may realize a skill through:

- deterministic code;
- a ROS 2 action server;
- a motion planner;
- a behavior tree;
- a reinforcement-learning policy;
- a VLA model;
- continuous action chunks;
- a learned action tokenizer such as FAST-like tokens;
- a proprietary robot SDK.

The lower-level representation is an implementation detail referenced by the trace, not the semantic definition itself.

## 3.2 Contracts instead of labels

A skill is not merely a class name. It is a typed contract:

```text
Skill = Identifier
      + Inputs and outputs
      + Preconditions
      + Invariants
      + Intended effects
      + Success conditions
      + Failure conditions
      + Cancellation semantics
      + Resource requirements
      + Risk metadata
```

## 3.3 Factorized context instead of enumerated scenes

OEBP represents entities, properties, spatial relationships, affordances, robot state, events, uncertainty, and history independently. It does not create a unique class for every combination of room, object, pose, robot, and task.

## 3.4 Validation before execution

Every behavior passes through:

1. schema validation;
2. ontology and type validation;
3. capability matching;
4. contract validation;
5. safety-policy validation;
6. optional simulation or reachability validation;
7. adapter compilation.

## 3.5 Closed-loop execution

A behavior invocation must provide feedback, support cancellation or preemption, and return a structured result. Long open-loop action lists are discouraged.

## 3.6 Evidence, not hidden reasoning

For explainability, OEBP records:

- predicates observed;
- sensor or model evidence references;
- selected behavior node;
- rejected alternatives and machine-readable reason codes when available;
- confidence and freshness;
- result and recovery path.

It does not require private model chain-of-thought.

---

# 4. Protocol architecture

OEBP consists of six layers.

## 4.1 Layer A - Semantic Context Model

Represents the world and the agent in a factorized, timestamped form.

Core objects:

- `ContextSnapshot`
- `Entity`
- `Pose`
- `Relation`
- `Affordance`
- `RobotState`
- `Event`
- `EvidenceRef`

## 4.2 Layer B - Behavior Ontology and Contracts

Defines canonical skill identifiers and their typed contracts.

Examples:

- `oebp.skill.perception.locate@1`
- `oebp.skill.navigation.navigate_to@1`
- `oebp.skill.manipulation.reach@1`
- `oebp.skill.manipulation.grasp@1`
- `oebp.skill.manipulation.place@1`
- `oebp.skill.interaction.handover@1`
- `oebp.skill.meta.verify@1`
- `oebp.skill.safety.stop@1`

## 4.3 Layer C - Behavior Composition Intermediate Representation

Defines deterministic composition operators for atomic or composite behavior nodes.

## 4.4 Layer D - Capability and Embodiment Binding

Describes robot capabilities and maps semantic skills to native implementations.

## 4.5 Layer E - Execution Lifecycle and Transport Binding

Defines goal, acceptance, progress, feedback, cancellation, preemption, result, and error semantics. Bindings may be provided for ROS 2 Actions, gRPC, HTTP, local Python/C++, or other middleware.

## 4.6 Layer F - Trace and Dataset Annotation

Records behavior execution alongside observations and low-level actions. It supports conversion to or extension of existing robot-learning dataset formats.

---

# 5. Canonical data model

## 5.1 Protocol envelope

Every top-level document uses a common envelope:

```json
{
  "protocol": "oebp",
  "version": "0.1.0",
  "kind": "BehaviorSpec",
  "metadata": {
    "id": "org.example.behavior.pick-and-place",
    "revision": "1.0.0",
    "created_at": "2026-06-16T09:00:00Z",
    "license": "CC-BY-4.0",
    "tags": ["manipulation", "mvp"]
  },
  "spec": {}
}
```

Required envelope fields:

- `protocol`
- `version`
- `kind`
- `metadata.id`
- `metadata.revision`
- `spec`

## 5.2 Identifiers and namespaces

Identifiers use reverse-domain namespaces:

```text
oebp.skill.manipulation.grasp@1
oebp.error.manipulation.object_slipped@1
org.vendor.robot.skill.vacuum_grasp@2
org.lab.dataset.kitchen-v3
```

Rules:

- Core identifiers start with `oebp.`.
- Extensions must use an owned namespace.
- The suffix `@N` is the contract major version.
- A breaking semantic change requires a new major version.
- Display names and natural-language aliases never replace canonical IDs.

## 5.3 Typed values and units

All physical quantities use SI units in the canonical representation.

```json
{
  "value": 0.12,
  "unit": "m"
}
```

Common canonical units:

- distance: `m`
- angle: `rad`
- time: `s` or integer `ms` in lifecycle fields
- mass: `kg`
- force: `N`
- torque: `N_m`
- velocity: `m_s`
- angular velocity: `rad_s`

Adapters may convert to native units.

## 5.4 Time and freshness

Every observed fact should include:

- monotonic or episode-relative timestamp;
- optional wall-clock timestamp;
- source;
- confidence;
- optional time-to-live.

Stale facts must not satisfy preconditions unless explicitly permitted.

## 5.5 Coordinate frames

All poses reference a named frame:

```json
{
  "frame": "robot/base_link",
  "position_m": [0.52, -0.12, 0.81],
  "orientation_xyzw": [0.0, 0.0, 0.0, 1.0],
  "covariance": [0.0, 0.0, 0.0]
}
```

Frame requirements:

- right-handed coordinates in canonical exchange;
- explicit transform chain or adapter-provided transformation;
- no implicit camera or world frame;
- pose confidence or covariance where available.

## 5.6 Entities

An entity represents an object, person, robot part, region, tool, surface, container, waypoint, or abstract resource.

```json
{
  "id": "scene/cup_01",
  "type": "oebp.entity.container.cup",
  "pose": {},
  "properties": {
    "material": "glass",
    "fragile": true,
    "estimated_mass_kg": 0.24
  },
  "affordances": [
    {
      "id": "oebp.affordance.graspable",
      "confidence": 0.94,
      "evidence": ["evidence/vision_302"]
    }
  ]
}
```

## 5.7 Relations

Relations are typed edges:

```json
{
  "predicate": "oebp.relation.on",
  "subject": "scene/cup_01",
  "object": "scene/table_01",
  "confidence": 0.96,
  "timestamp_ms": 4120
}
```

Core relation families:

- topological: `on`, `inside`, `contains`, `attached_to`
- metric: `near`, `far`, `within_distance`
- directional: `left_of`, `right_of`, `above`, `below`, `in_front_of`
- visibility: `visible_to`, `occluded_from`
- possession/contact: `held_by`, `touching`, `supported_by`
- operational: `reachable_by`, `reserved_by`, `blocked_by`

Derived relations such as `reachable_by` must record the computation source and freshness.

---

# 6. Predicate expression language

OEBP uses a small declarative expression AST. Arbitrary scripts are forbidden in core documents.

Supported expression types:

- `all`
- `any`
- `not`
- `predicate`
- `compare`
- `exists`
- `capability`
- `event`
- `fresh`

Example:

```json
{
  "op": "all",
  "args": [
    {
      "op": "predicate",
      "name": "oebp.relation.visible_to",
      "subject": "$object",
      "object": "$robot"
    },
    {
      "op": "predicate",
      "name": "oebp.relation.reachable_by",
      "subject": "$object",
      "object": "$effector"
    },
    {
      "op": "compare",
      "left": {"path": "$object.properties.estimated_mass_kg"},
      "operator": "lte",
      "right": {"path": "$capability.max_payload_kg"}
    }
  ]
}
```

The MVP validator should implement deterministic evaluation and return:

```json
{
  "value": false,
  "failed_nodes": ["predicate-2"],
  "reason_codes": ["oebp.reason.object_not_reachable"],
  "evidence": ["planner/reachability_check_44"]
}
```

---

# 7. Behavior contract

Every registered skill must define the following.

## 7.1 Contract fields

```text
id
summary
input ports
output ports
required capabilities
resource locks
preconditions
invariants
intended effects
success conditions
failure conditions
cancellation semantics
risk class
default timeout
standard error codes
recommended recovery mappings
```

## 7.2 Example: grasp contract

```yaml
id: oebp.skill.manipulation.grasp@1
inputs:
  object: EntityRef
  effector: EffectorRef
  grasp_hint: optional GraspHint
outputs:
  grasp_id: string
requires:
  - oebp.capability.manipulation.grasp
resources:
  - $effector
preconditions:
  - object exists and is fresh
  - object is visible or localized
  - object is reachable by effector
  - estimated object mass is within payload limit
invariants:
  - force and speed stay inside safety envelope
  - forbidden contact regions are not entered
success:
  - stable contact detected
  - object is held by effector for minimum dwell time
failure:
  - no contact
  - object slipped
  - force limit reached
  - object moved out of workspace
  - timeout
cancel:
  - stop closing actuator
  - retract if safe
```

## 7.3 Risk classes

The protocol proposes five generic classes. Deployment policy determines concrete approval rules.

- `R0`: observation or reasoning only; no physical actuation.
- `R1`: low-energy motion in a controlled area.
- `R2`: contact manipulation or motion near property.
- `R3`: operation near people, fragile/high-value assets, heat, sharp objects, or elevated force.
- `R4`: deployment-prohibited by default unless an external certified policy explicitly authorizes it.

Risk classification is metadata, not a substitute for a real safety case.

---

# 8. Core behavior ontology for v0.1

The first release should remain small. Each skill must be useful across multiple robots.

## 8.1 Perception and state

1. `observe`
2. `locate`
3. `track`
4. `inspect`
5. `estimate_pose`
6. `verify`

## 8.2 Navigation and body motion

7. `navigate_to`
8. `approach`
9. `align_base`
10. `follow`
11. `dock`
12. `retreat`

## 8.3 Manipulation

13. `reach`
14. `align_effector`
15. `grasp`
16. `release`
17. `lift`
18. `lower`
19. `place`
20. `push`
21. `pull`
22. `rotate`
23. `insert`
24. `extract`
25. `press`
26. `pour`
27. `handover`
28. `stabilize`

## 8.4 Interaction and meta behaviors

29. `signal`
30. `ask_for_help`
31. `wait`
32. `stop`

A domain extension may add `wipe`, `screw`, `weld`, `scan_barcode`, `open_door`, or other skills, but extension skills must preserve contract structure.

---

# 9. Composition model

OEBP uses a behavior-graph intermediate representation inspired by behavior-tree and workflow semantics, while remaining serialization-neutral.

## 9.1 Node types

- `invoke`: call a registered skill.
- `sequence`: execute children in order until one fails.
- `fallback`: execute children in order until one succeeds.
- `parallel`: execute children under an explicit success/failure policy.
- `retry`: retry a child with bounded attempts and optional backoff.
- `timeout`: cancel a child after a deadline.
- `guard`: execute a child only if a predicate is satisfied.
- `loop`: repeat with a mandatory finite bound or termination condition.
- `monitor`: run a condition concurrently and interrupt on violation.
- `select`: choose among branches using explicit predicates or a planner decision record.
- `emit`: emit an event without physical action.

## 9.2 Prohibited constructs

- Unbounded loops.
- Hidden side effects.
- Dynamic execution of arbitrary model-generated source code.
- Implicit global variables.
- Silent failure swallowing.
- Parallel nodes without resource-lock declarations.

## 9.3 Runtime node states

Canonical states:

```text
IDLE
VALIDATING
ACCEPTED
RUNNING
PAUSED
SUCCEEDED
FAILED
CANCELING
CANCELED
PREEMPTED
BLOCKED
UNSAFE
```

## 9.4 Control semantics

### Sequence

- Starts child 1.
- Advances only after `SUCCEEDED`.
- Returns the first non-success terminal result.

### Fallback

- Starts child 1.
- Advances after recoverable failure.
- Stops on success or non-recoverable failure.

### Retry

- Requires `max_attempts`.
- Must record every attempt as a separate trace span.
- May mutate parameters only through an explicit recovery policy.

### Parallel

- Requires declared resource locks and a success policy such as `all`, `any`, or `threshold`.
- Conflicting locks fail validation before execution.

### Monitor

- Evaluates an invariant while a child runs.
- On violation, requests cancellation and invokes the configured safe response.

---

# 10. Capability profile and cross-embodiment compilation

## 10.1 Capability profile

Each robot publishes a `CapabilityProfile` describing what it can do rather than only listing its model name.

```json
{
  "embodiment_id": "org.example.robot.mobile-manipulator-01",
  "embodiment_class": "mobile_manipulator",
  "effectors": [],
  "sensors": [],
  "frames": [],
  "capabilities": [],
  "safety_envelopes": [],
  "adapter_bindings": []
}
```

Capabilities should include quantitative constraints where relevant:

- workspace;
- payload;
- grasp aperture;
- force/torque sensing;
- mobility type;
- maximum speed;
- control modes;
- localization quality;
- camera coverage;
- supported object or surface classes;
- expected success and latency ranges;
- certification or deployment restrictions.

## 10.2 Capability requirements

A behavior declares requirements such as:

```json
{
  "capability": "oebp.capability.manipulation.grasp",
  "constraints": {
    "min_payload_kg": 0.5,
    "min_aperture_m": 0.08,
    "requires_force_feedback": true
  }
}
```

## 10.3 Adapter binding

A binding maps a semantic skill to a native implementation:

```json
{
  "skill": "oebp.skill.manipulation.grasp@1",
  "implementation": {
    "type": "ros2_action",
    "endpoint": "/right_arm/grasp",
    "message_type": "example_robot_msgs/action/Grasp"
  },
  "parameter_map": {
    "object.pose": "goal.target_pose",
    "grasp_hint.force_n": "goal.max_force"
  },
  "result_map": {
    "native.SUCCESS": "SUCCEEDED",
    "native.SLIP": "oebp.error.manipulation.object_slipped@1"
  }
}
```

Other implementation types:

- `local_function`
- `grpc_action`
- `behavior_tree`
- `motion_planner`
- `policy_model`
- `continuous_action_chunk`
- `action_token_codec`
- `vendor_sdk`

## 10.4 Compilation pipeline

```text
Behavior graph
  -> resolve parameters and entity references
  -> evaluate static predicates
  -> match capability constraints
  -> allocate resources and locks
  -> select adapter binding
  -> translate frames and units
  -> generate executable plan
  -> run preflight checks
```

Compilation must return a machine-readable report, including unsupported nodes and fallback options.

---

# 11. Execution lifecycle

The lifecycle intentionally mirrors long-running action patterns.

## 11.1 Goal request

```json
{
  "invocation_id": "inv-3492",
  "behavior_ref": "org.example.behavior.pick-and-place@1.0.0",
  "bindings": {
    "object": "scene/cup_01",
    "target": "scene/tray_01",
    "effector": "robot/right_gripper"
  },
  "deadline_ms": 30000,
  "priority": 50,
  "idempotency_key": "task-883-attempt-1"
}
```

## 11.2 Acceptance response

The executor returns:

- accepted or rejected;
- validation report;
- estimated support level;
- selected adapter;
- required approval state;
- resource reservations.

## 11.3 Feedback

Feedback is structured and periodic or event-driven:

```json
{
  "invocation_id": "inv-3492",
  "node_id": "grasp-object",
  "state": "RUNNING",
  "progress": 0.62,
  "observed_predicates": ["object_within_reach"],
  "metrics": {"contact_force_n": 3.1},
  "warnings": [],
  "timestamp_ms": 7420
}
```

## 11.4 Cancellation and preemption

Every actuation skill must define cancellation behavior. Cancellation is a request, not an assumption that motion stops instantaneously.

Preemption rules must consider:

- current risk;
- whether the robot is supporting an object;
- safe intermediate states;
- resource handoff;
- priority;
- timeout.

## 11.5 Result

```json
{
  "invocation_id": "inv-3492",
  "state": "FAILED",
  "error": {
    "code": "oebp.error.manipulation.object_slipped@1",
    "recoverable": true,
    "details": {"slip_distance_m": 0.018}
  },
  "effects": [
    {
      "predicate": "oebp.relation.on",
      "subject": "scene/cup_01",
      "object": "scene/table_01"
    }
  ],
  "trace_ref": "trace/episode-551/span-19"
}
```

---

# 12. Error taxonomy and recovery

## 12.1 Error families

### Perception

- `object_not_found`
- `object_ambiguous`
- `pose_uncertain`
- `target_lost`
- `observation_stale`

### Planning

- `no_path`
- `unreachable`
- `collision_predicted`
- `constraint_unsatisfied`

### Manipulation

- `no_contact`
- `object_slipped`
- `unstable_grasp`
- `force_limit_reached`
- `insertion_jammed`
- `target_moved`

### Embodiment

- `capability_missing`
- `joint_limit`
- `payload_exceeded`
- `sensor_unavailable`
- `adapter_not_found`

### Environment and interaction

- `human_intrusion`
- `workspace_blocked`
- `unexpected_contact`
- `recipient_not_ready`

### Safety and system

- `policy_denied`
- `safety_envelope_violation`
- `emergency_stop`
- `timeout`
- `communication_fault`
- `adapter_fault`

## 12.2 Recovery policy

A recovery policy maps an error pattern to a bounded response:

```json
{
  "on": ["oebp.error.manipulation.object_slipped@1"],
  "max_activations": 2,
  "behavior": {
    "type": "sequence",
    "children": [
      {"type": "invoke", "skill": "oebp.skill.manipulation.release@1"},
      {"type": "invoke", "skill": "oebp.skill.manipulation.retreat@1"},
      {"type": "invoke", "skill": "oebp.skill.perception.estimate_pose@1"},
      {"type": "invoke", "skill": "oebp.skill.manipulation.grasp@1"}
    ]
  }
}
```

Recovery is always bounded. After limits are exhausted, the system must fail safely or request human assistance.

---

# 13. Explainability and observability

Every execution should produce a trace with spans analogous to distributed tracing.

## 13.1 Trace span

```json
{
  "trace_id": "episode-551",
  "span_id": "span-19",
  "parent_span_id": "span-12",
  "node_id": "grasp-object",
  "skill": "oebp.skill.manipulation.grasp@1",
  "start_ms": 6150,
  "end_ms": 8010,
  "input_bindings": {},
  "precondition_report": {},
  "adapter": "org.example.adapter.right-arm-grasp@2",
  "evidence_refs": [],
  "feedback_refs": [],
  "result": {},
  "low_level_action_ref": "data/actions.parquet#6150:8010"
}
```

## 13.2 Decision record

When a planner or model selects among options, store:

- candidate behavior IDs;
- chosen candidate;
- contract satisfaction scores;
- capability compatibility;
- safety-policy result;
- evidence references;
- concise reason codes.

Do not require unrestricted natural-language reasoning.

## 13.3 Metrics

Recommended metrics:

- success rate by skill and embodiment;
- recovery success rate;
- precondition false-positive rate;
- cancellation latency;
- safety interruptions;
- adapter compilation failures;
- execution latency;
- action smoothness;
- cross-embodiment transfer gap;
- confidence calibration.

---

# 14. Runtime transport bindings

## 14.1 Canonical exchange format

- JSON with JSON Schema Draft 2020-12 for interoperability, fixtures, model output, debugging, and dataset metadata.
- Canonical field ordering is not semantically significant.
- Deterministic canonicalization should be specified for hashing and signatures.

## 14.2 ROS 2 binding

Recommended mapping:

```text
OEBP Goal       -> ROS 2 Action Goal
OEBP Feedback   -> ROS 2 Action Feedback
OEBP Result     -> ROS 2 Action Result
OEBP cancel     -> ROS 2 Action cancellation
Context stream  -> ROS 2 topics or local world model
```

An OEBP executor may expose a generic action or generated action types for registered skills.

## 14.3 gRPC / Protobuf binding

Use Protobuf for efficient runtime transport while preserving semantic equivalence with the JSON representation. Generated bindings must pass round-trip conformance tests.

## 14.4 Behavior-tree binding

Composition nodes map naturally to behavior-tree control nodes. Typed input/output ports should map to OEBP ports, while the blackboard stores resolved bindings and observed effects.

---

# 15. Training-data representation

OEBP adds a semantic annotation plane to time-series robot data.

## 15.1 Episode package

```text
episode/
|-- episode_manifest.json
|-- behavior_graph.json
|-- capability_profile.json
|-- provenance.json
|-- trace.jsonl
|-- observations.parquet
|-- actions.parquet
|-- videos/
`-- optional_action_tokens.parquet
```

## 15.2 Per-frame or per-window fields

Recommended fields:

```text
timestamp
observation.*
action.*
oebp.invocation_id
oebp.node_id
oebp.skill_id
oebp.behavior_phase
oebp.status
oebp.active_predicates
oebp.success_probability
oebp.error_code
oebp.recovery_id
oebp.evidence_refs
oebp.action_codec
oebp.action_token_ids
```

## 15.3 Compatibility strategy

For formats such as LeRobot-style datasets:

- retain existing video, observation, action, timestamp, and task fields;
- add OEBP fields as tabular features;
- store behavior graphs, capability profiles, schemas, and provenance under metadata;
- do not duplicate large videos or raw signals;
- preserve the original dataset license and source identifiers.

## 15.4 Training views

The same episode can produce several supervised datasets.

### Planner dataset

```text
Context + Goal + Capability Profile -> Behavior Graph
```

### Next-skill dataset

```text
Context + Goal + History -> Next Skill + Parameters
```

### Contract dataset

```text
Context + Candidate Skill -> Preconditions satisfied? + Evidence
```

### Recovery dataset

```text
Failure Context + Error Code + History -> Recovery Behavior
```

### Success-estimation dataset

```text
Observation Window + Behavior Contract -> Success Probability / Result
```

### Low-level policy dataset

```text
Observation + Skill Token + Parameters -> Continuous Action Chunk / Action Tokens
```

### Preference or ranking dataset

```text
Same Context + Multiple Traces -> Ranked quality and safety labels
```

---

# 16. Large-model-assisted data generation

The large model is a proposal generator and semantic annotator, not the final authority on physical correctness.

## 16.1 Generation architecture

```text
Ontology + Seed Tasks + Asset Catalog + Capability Profiles
                         v
               Coverage-aware Task Generator
                         v
                ScenarioSpec + GoalSpec
                         v
              Behavior Graph Generator
                         v
       Schema / Type / Contract / Safety Validators
                         v
              Embodiment Compiler
                         v
     Simulator + Planner + Demonstration Generator
                         v
       Multi-seed execution and domain randomization
                         v
          Trace annotator and failure generator
                         v
          Quality critics and deduplication
                         v
             Human review sampling
                         v
             Versioned dataset release
```

## 16.2 What the model may generate

- scenario descriptions;
- object and relation graphs using known asset IDs;
- goals;
- behavior graphs from registered skills;
- parameter ranges within declared capability limits;
- language paraphrases;
- candidate failure perturbations;
- recovery candidates;
- test cases and invalid counterexamples;
- simulator task code in a sandboxed generation workflow.

## 16.3 What the model must not assert without verification

- that a trajectory is collision-free;
- that an object can be grasped;
- that a robot has sufficient reach or payload;
- that a force profile is safe;
- that the behavior succeeded;
- that synthetic data transfers to reality;
- that an unregistered skill has valid semantics.

These facts require deterministic checking, simulation, execution, measurement, or human review.

## 16.4 Coverage model

Maintain a multidimensional coverage matrix:

```text
skill
x object affordance
x environment type
x embodiment class
x initial-state difficulty
x failure type
x recovery type
x language variation
x visual variation
x risk class
```

The generator should preferentially sample underrepresented cells instead of only generating plausible common tasks.

## 16.5 ScenarioSpec

The LLM first emits a constrained scenario document:

```json
{
  "scenario_id": "synthetic/kitchen/pick-cup-000341",
  "environment": "kitchen_counter",
  "assets": [
    {"asset_id": "asset/cup/glass_04", "role": "target"},
    {"asset_id": "asset/tray/plastic_02", "role": "destination"}
  ],
  "initial_relations": [
    {"predicate": "oebp.relation.on", "subject": "target", "object": "counter"}
  ],
  "goal_predicates": [
    {"predicate": "oebp.relation.on", "subject": "target", "object": "destination"}
  ],
  "difficulty": {
    "clutter": 0.3,
    "occlusion": 0.1,
    "precision": 0.6
  },
  "allowed_skills": [
    "oebp.skill.manipulation.grasp@1",
    "oebp.skill.manipulation.place@1"
  ]
}
```

Only catalog assets and registered predicates are permitted in accepted data.

## 16.6 Behavior generation prompt contract

The model receives:

- exact schema;
- registered skill cards;
- capability profile;
- scenario graph;
- safety policy;
- examples of valid and invalid plans;
- maximum graph depth and retries.

It must return JSON only. Any natural-language commentary is discarded or treated as a validation failure.

## 16.7 Static validation gates

Hard gates:

1. JSON Schema valid.
2. All identifiers registered or namespaced.
3. All ports type-compatible.
4. All entity references resolvable.
5. No unbounded loops.
6. Resource locks non-conflicting.
7. Capability constraints satisfiable.
8. Required preconditions are achievable in principle.
9. Safety policy permits the proposed behavior.
10. No arbitrary code in protocol fields.

## 16.8 Simulation and execution gates

For each accepted symbolic plan:

1. Compile to at least one embodiment.
2. Run deterministic preflight checks.
3. Execute multiple random seeds.
4. Record success, failure, and interruption traces.
5. Perturb object pose, lighting, clutter, friction, latency, and sensor noise within declared ranges.
6. Reject or flag plans whose success depends on narrow accidental conditions.
7. Verify final goal predicates from simulator state rather than model narration.

## 16.9 Demonstration generation methods

The pipeline may use:

- motion planning;
- trajectory optimization;
- scripted experts;
- reinforcement learning;
- teleoperation seeds;
- demonstration transformation;
- learned policies;
- hybrid planners.

The data record must identify the method and software version.

## 16.10 Failure and recovery data

At least one controlled failure family should be generated for each applicable skill:

- target moved;
- perception dropout;
- object slip;
- blocked path;
- grasp miss;
- insertion jam;
- timeout;
- human enters safety zone;
- actuator or sensor unavailable;
- capability mismatch.

Each failure episode should contain:

- injected perturbation;
- first observable evidence;
- detection latency;
- error code;
- recovery decision;
- recovery outcome;
- safe terminal state.

## 16.11 Multi-model critics

Use independent critics with different roles:

- schema critic;
- semantic critic;
- safety critic;
- diversity critic;
- visual-grounding critic;
- trace-consistency critic;
- language-quality critic.

A model critic can flag issues, but hard acceptance should depend on deterministic validators and simulator or real measurements whenever possible.

## 16.12 Quality score

Use hard gates plus a soft score.

```text
ACCEPT = schema_valid
      AND contract_valid
      AND capability_valid
      AND safety_valid
      AND execution_evidence_present
```

Suggested soft score:

```text
Q = 0.15 semantic_consistency
  + 0.20 execution_success_and_stability
  + 0.15 perturbation_robustness
  + 0.10 diversity_and_novelty
  + 0.15 annotation_confidence
  + 0.15 safety_margin
  + 0.10 cross_embodiment_transferability
```

Store component scores; never retain only the aggregate.

## 16.13 Provenance

Every generated episode must record:

- generator model and version;
- prompts or prompt template hashes;
- seed;
- source ontology version;
- asset IDs and licenses;
- simulator and physics-engine versions;
- embodiment adapter version;
- expert policy or planner version;
- validators and outcomes;
- human-review status;
- transformations from source demonstrations;
- dataset lineage.

---

# 17. LLM prompt templates

## 17.1 Scenario generator

```text
SYSTEM
You generate candidate embodied-learning scenarios using only the provided
ontology, asset catalog, capability profile, and JSON Schema. Output JSON only.
Do not claim physical feasibility or success. Do not create unregistered IDs.
Prefer underrepresented coverage cells supplied in COVERAGE_GAPS.

INPUT
- Scenario schema
- Asset catalog
- Skill registry
- Capability profile
- Safety policy
- Coverage gaps
- Valid examples
- Invalid examples

OUTPUT
One ScenarioSpec with explicit initial predicates, goal predicates, parameter
ranges, difficulty dimensions, and intended failure perturbations.
```

## 17.2 Behavior planner

```text
SYSTEM
Compile the given GoalSpec into an OEBP BehaviorSpec. Use only registered skills.
Every physical invocation must be guarded by relevant preconditions and must
have bounded timeout, error handling, and recovery. Output JSON only.
The output is a proposal and will be rejected if it violates the schema,
capability profile, contracts, safety policy, or resource constraints.
```

## 17.3 Failure generator

```text
SYSTEM
Generate one controlled failure perturbation for the selected skill. The
perturbation must be observable, bounded, reproducible, and safe in simulation.
Specify the expected OEBP error code, evidence channel, detection window, and
acceptable recovery outcomes. Output JSON only.
```

## 17.4 Semantic reviewer

```text
SYSTEM
Review the candidate strictly against the supplied contracts and context.
Return machine-readable findings only. Do not repair the document. Classify
each finding by severity, JSON Pointer, violated rule, and suggested correction.
```

---

# 18. Data curation and human review

## 18.1 Sampling policy

Human review should focus on:

- new skill contracts;
- high-risk behavior classes;
- low-confidence annotations;
- low simulator success but high semantic score;
- novel asset categories;
- cross-embodiment disagreements;
- safety critic disagreements;
- random audit samples.

## 18.2 Review labels

- `approved`
- `approved_with_notes`
- `rejected_semantic`
- `rejected_physics`
- `rejected_safety`
- `rejected_duplicate`
- `needs_real_world_validation`

## 18.3 Dataset splits

Avoid leakage by splitting on combinations such as:

- object instance;
- scene layout;
- embodiment;
- task composition;
- language family;
- failure type.

A random episode split alone is insufficient for measuring compositional or cross-embodiment generalization.

---

# 19. Conformance and benchmarks

## 19.1 Schema conformance

- valid fixtures accepted;
- invalid fixtures rejected with stable error paths;
- deterministic canonical serialization;
- JSON/Protobuf round-trip equivalence.

## 19.2 Contract conformance

- preconditions evaluated consistently;
- stated effects checked against final context;
- cancellation reaches a declared safe state;
- retries remain bounded;
- parallel resource conflicts rejected.

## 19.3 Cross-embodiment benchmark

The same semantic behavior should compile to at least two embodiments with different control interfaces.

Measure:

- compilation rate;
- success rate;
- semantic result equivalence;
- parameter adaptation;
- unsupported-capability detection;
- amount of embodiment-specific data required.

## 19.4 Compositional generalization

Hold out combinations of known skills and evaluate behavior graphs that use familiar atomic skills in unseen sequences or branches.

## 19.5 Recovery benchmark

Evaluate controlled failures with metrics for:

- detection accuracy;
- detection latency;
- correct error classification;
- recovery selection;
- recovery success;
- safe-failure rate.

## 19.6 Safety benchmark

- unsafe plans rejected before execution;
- invariant violation interrupts execution;
- cancellation latency within deployment policy;
- risk-class approval enforced;
- model-generated fields cannot override supervisor policy.

## 19.7 Data-generation benchmark

Measure:

- schema-valid generation rate;
- compile-valid rate;
- simulator-executable rate;
- multi-seed success distribution;
- novelty after deduplication;
- coverage gain;
- human approval rate;
- real-data benefit when synthetic data is added;
- transfer gap across embodiments.

---

# 20. Security and safety model

## 20.1 Trust boundaries

Untrusted:

- LLM outputs;
- third-party behavior documents;
- external context sources;
- dataset annotations without provenance;
- vendor adapters not certified for the deployment.

Trusted only by explicit configuration:

- schema registry;
- skill registry;
- capability profile issuer;
- safety supervisor;
- adapter packages;
- signing keys;
- simulator or execution evidence.

## 20.2 Security controls

- signed registries and adapter manifests;
- content hashes for behavior specs;
- allowlists for skills and namespaces;
- no dynamic source-code execution in the core runtime;
- sandboxed simulator-code generation;
- parameter bounds;
- rate limits and invocation quotas;
- replay protection and idempotency keys;
- audit logs;
- least-privilege access to actuators and sensors.

## 20.3 Safety supervisor

The safety supervisor is outside the learned planner and outside the OEBP behavior graph. It may:

- deny a goal;
- clamp parameters;
- interrupt execution;
- trigger emergency stop;
- require human approval;
- enforce workspace, speed, force, proximity, and payload rules.

The protocol records these interventions but cannot override them.

---

# 21. Versioning and governance

## 21.1 Version dimensions

- Protocol version: envelope and lifecycle semantics.
- Schema version: serialization structure.
- Skill contract major version: semantic compatibility.
- Ontology release: registry content.
- Adapter version: embodiment implementation.
- Dataset annotation version: training label layout.

## 21.2 Compatibility rules

- Unknown optional fields must be preserved where possible.
- Unknown required core fields cause rejection.
- Minor versions may add optional fields or non-breaking enum values.
- Breaking contract changes require a new skill major ID.
- Deprecated skills retain machine-readable replacements and migration notes.

## 21.3 Open governance proposal

- Public RFC repository.
- Technical steering committee with research, hardware, middleware, safety, and dataset representation.
- Reference implementation cannot define semantics that are absent from the written spec.
- Conformance tests are normative.
- Vendor extensions may graduate into core only after multi-implementation evidence.

---

# 22. Reference implementation architecture

## 22.1 Components

```text
oebp-registry
  Skill, predicate, error, capability, and adapter metadata

oebp-schema
  JSON Schemas and generated types

oebp-validator
  Schema, type, contract, graph, resource, and safety checks

oebp-compiler
  Capability matching and adapter selection

oebp-runtime
  Lifecycle, feedback, cancellation, preemption, tracing

oebp-sdk-python
  Python models and APIs

oebp-sdk-cpp
  C++ models and runtime interfaces

oebp-ros2
  ROS 2 action and topic bindings

oebp-sim
  Simulator adapters and evidence collection

oebp-data
  Episode annotation and dataset conversion

oebp-gen
  LLM-assisted candidate generation and quality pipeline

oebp-conformance
  Fixtures and test harness
```

## 22.2 Suggested repository

```text
oebp/
|-- README.md
|-- LICENSES/
|-- GOVERNANCE.md
|-- CONTRIBUTING.md
|-- rfcs/
|-- spec/
|   |-- core.md
|   |-- context.md
|   |-- behavior-contract.md
|   |-- composition.md
|   |-- capability.md
|   |-- lifecycle.md
|   |-- trace-and-data.md
|   `-- safety.md
|-- registry/
|   |-- skills/
|   |-- predicates/
|   |-- errors/
|   `-- capabilities/
|-- schemas/
|-- protobuf/
|-- sdk/python/
|-- sdk/cpp/
|-- bindings/ros2/
|-- adapters/
|   |-- mock/
|   |-- simulation/
|   `-- examples/
|-- generator/
|   |-- prompts/
|   |-- validators/
|   |-- critics/
|   `-- pipelines/
|-- datasets/
|   |-- converters/
|   `-- fixtures/
|-- conformance/
|-- benchmarks/
|-- examples/
`-- docs/
```

## 22.3 CLI proposal

```bash
oebp validate behavior.json
oebp validate-capability robot.json
oebp compile behavior.json --capability robot.json
oebp run behavior.json --adapter mock
oebp trace inspect trace.jsonl
oebp dataset annotate ./episode
oebp dataset validate ./dataset
oebp generate scenario --coverage coverage.json
oebp generate behavior --scenario scenario.json --robot robot.json
oebp conformance run --implementation http://localhost:8080
```

---

# 23. MVP implementation plan

## Phase 0 - Formalization

Deliverables:

- envelope schema;
- predicate AST;
- behavior-graph schema;
- capability schema;
- lifecycle model;
- error taxonomy;
- 10 core skill contracts;
- valid and invalid fixtures.

## Phase 1 - Local reference runtime

- Python SDK using typed models;
- deterministic validator;
- mock executor;
- trace writer;
- CLI;
- unit and property-based tests.

## Phase 2 - Two embodiments

Support at least:

1. a fixed manipulator;
2. a mobile manipulator or second arm with a materially different interface.

Demonstrate the same pick-and-place behavior compiling and running on both.

## Phase 3 - Dataset annotation

- import one existing demonstration dataset;
- annotate behavior phases and errors;
- export an OEBP episode package;
- train or evaluate a next-skill baseline.

## Phase 4 - LLM-assisted generation

- constrained scenario generation;
- behavior-graph generation;
- validation and repair loop;
- simulation execution;
- multi-seed data collection;
- provenance and quality scoring.

## Phase 5 - Open RFC release

- publish specification;
- publish reference implementation;
- publish conformance suite;
- invite independent adapter implementations;
- freeze v0.1 after interoperability evidence.

---

# 24. Initial acceptance criteria

The v0.1 reference implementation is acceptable when:

1. All published examples validate against the schemas.
2. At least 30 invalid fixtures fail for the expected reason.
3. No behavior graph can contain an unbounded loop.
4. Parallel resource conflicts are detected statically.
5. The same semantic pick-and-place behavior compiles to two distinct capability profiles.
6. Unsupported behavior returns `capability_missing`, not a generic runtime error.
7. Feedback, cancellation, timeout, and recovery are demonstrated end to end.
8. Every execution produces a trace with behavior-to-low-level-action alignment.
9. Generated scenarios record complete provenance.
10. LLM-generated behavior cannot execute before deterministic validation.
11. Synthetic success is determined from simulator state and goal predicates.
12. Dataset exports can preserve observations, actions, video references, semantic labels, and source lineage.

---

# 25. Open design questions for contributors

Contributors should explicitly critique and optimize the following decisions rather than accepting them blindly.

1. Is the predicate AST expressive enough without becoming an unsafe programming language?
2. Should composition semantics exactly adopt an existing behavior-tree standard or remain protocol-native?
3. Which skill boundaries are stable across manipulators, mobile robots, quadrupeds, humanoids, and drones?
4. How should capability quality, uncertainty, and probabilistic success be represented?
5. Should `reach`, `align_effector`, and `grasp` be separate core skills or profiles of a broader manipulation contract?
6. How should bimanual resource locking and synchronization work?
7. How should learned latent action tokens be associated with semantic skills without falsely assigning meaning to individual tokens?
8. Which fields belong in runtime messages versus dataset-only annotations?
9. What is the minimum safe expression for recovery and compensation?
10. How should registry trust, signing, and extension governance work?
11. How should real-world evidence update capability claims and success priors?
12. How can OEBP interoperate with ROS 2, BehaviorTree.CPP, LeRobot-like datasets, Open X-Embodiment conversions, and vendor SDKs with minimal duplication?

---

# 26. Recommended initial thesis

OEBP should position itself as:

> A semantic behavior contract and trace protocol connecting embodied planners, robot capabilities, execution systems, and training datasets.

It should not initially claim to be:

- a universal robot foundation model;
- a universal low-level action tokenizer;
- a replacement for robot middleware;
- a guarantee of physical or safety correctness.

Its strongest differentiated contribution is the combination of:

```text
Explainable semantic skills
+ deterministic composition
+ capability contracts
+ lifecycle and recovery
+ cross-embodiment adapter bindings
+ aligned dataset traces
+ validation-first generative data pipeline
```
