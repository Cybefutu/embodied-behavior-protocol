# Core Skill Registry v0.1

This directory is the starting point for canonical `oebp.skill.*` contracts.
Registry entries should be stable, versioned, and backed by examples,
validation rules, and at least one adapter path before they are treated as core.

## Initial Families

- `oebp.skill.perception.*`
- `oebp.skill.navigation.*`
- `oebp.skill.manipulation.*`
- `oebp.skill.interaction.*`
- `oebp.skill.meta.*`
- `oebp.skill.safety.*`

## Registry Entry Requirements

Each skill entry should define:

- canonical identifier and major version;
- summary;
- input and output ports;
- preconditions;
- invariants;
- success conditions;
- failure conditions and stable error codes;
- cancellation behavior;
- resource requirements;
- risk class;
- trace fields;
- at least one valid behavior example.

Experimental skills should stay in an owned namespace such as
`org.example.skill.*` until they meet core graduation criteria.

