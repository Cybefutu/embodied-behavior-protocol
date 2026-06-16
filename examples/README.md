# Examples

These examples are intentionally small. They are designed to make the v0.1
proposal concrete before a full reference implementation exists.

## Files

- `pick-and-place.behavior.json` is a semantic behavior graph for moving an
  object from its current support surface to a target surface.
- `generic-mobile-manipulator.capability.json` is a capability profile for a
  mobile manipulator with one parallel gripper and ROS 2-style adapter bindings.

## Expected Use

Use these files as early fixtures for:

- schema validation;
- behavior graph review;
- capability matching;
- adapter binding design;
- trace and dataset annotation experiments.

Examples should stay readable. Add more complex fixtures under a future
`conformance/fixtures/` directory once the validator exists.
