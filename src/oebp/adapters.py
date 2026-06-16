"""Reference robot adapters used for cross-embodiment OEBP conformance tests."""

from __future__ import annotations

import copy
from dataclasses import dataclass
from typing import Any

from .compiler import CompilationResult, OEBPCompiler


COMMON_SKILLS = {
    "estimate_pose": "oebp.skill.perception.estimate_pose@1",
    "reach": "oebp.skill.manipulation.reach@1",
    "grasp": "oebp.skill.manipulation.grasp@1",
    "lift": "oebp.skill.manipulation.lift@1",
    "place": "oebp.skill.manipulation.place@1",
    "verify": "oebp.skill.meta.verify@1",
    "release": "oebp.skill.manipulation.release@1",
}


@dataclass(frozen=True)
class RobotAdapter:
    adapter_id: str
    profile: dict[str, Any]

    def capability_profile(self) -> dict[str, Any]:
        return copy.deepcopy(self.profile)

    def compile(self, behavior: dict[str, Any], compiler: OEBPCompiler | None = None) -> CompilationResult:
        active_compiler = compiler or OEBPCompiler()
        return active_compiler.compile(behavior, self.capability_profile())


class FixedArmAdapter(RobotAdapter):
    def __init__(self) -> None:
        super().__init__("fixed_arm", _fixed_arm_profile())


class MobileManipulatorAdapter(RobotAdapter):
    def __init__(self) -> None:
        super().__init__("mobile_manipulator", _mobile_manipulator_profile())


def available_adapters() -> tuple[RobotAdapter, ...]:
    return (FixedArmAdapter(), MobileManipulatorAdapter())


def _binding(
    skill: str,
    implementation: dict[str, Any],
    parameter_map: dict[str, str] | None = None,
    result_map: dict[str, str] | None = None,
) -> dict[str, Any]:
    return {
        "skill": skill,
        "implementation": implementation,
        "parameter_map": dict(parameter_map or {}),
        "result_map": dict(result_map or {"ok": "succeeded"}),
    }


def _fixed_arm_profile() -> dict[str, Any]:
    return {
        "protocol": "oebp",
        "version": "0.1.0",
        "kind": "CapabilityProfile",
        "metadata": {
            "id": "org.oebp.adapters.fixed-arm.reference",
            "revision": "1.0.0",
            "created_at": "2026-06-16T09:00:00Z",
        },
        "spec": {
            "embodiment_id": "org.oebp.robot.reference-fixed-arm",
            "embodiment_class": "fixed_manipulator",
            "effectors": [
                {
                    "id": "arm/gripper",
                    "type": "parallel_gripper",
                    "frame": "arm/tool",
                    "max_payload_kg": 2.0,
                    "max_aperture_m": 0.08,
                    "force_feedback": True,
                }
            ],
            "sensors": [
                {"id": "arm/rgbd", "type": "depth_camera", "frame": "arm/camera", "rate_hz": 30},
                {"id": "arm/wrist_ft", "type": "force_torque", "frame": "arm/tool", "rate_hz": 200},
            ],
            "frames": [
                {"id": "world"},
                {"id": "arm/base", "parent": "world"},
                {"id": "arm/camera", "parent": "arm/base"},
                {"id": "arm/tool", "parent": "arm/base"},
            ],
            "capabilities": [
                {
                    "id": "oebp.capability.perception.object_pose",
                    "support": "native",
                    "parameters": {"frame": "world", "unit": "m", "max_range_m": 1.5},
                    "quality": {"expected_success": 0.95, "p95_latency_ms": 120},
                },
                {
                    "id": "oebp.capability.manipulation.grasp",
                    "support": "planned",
                    "parameters": {"max_payload_kg": 2.0, "max_aperture_m": 0.08, "force_feedback": True},
                    "quality": {"expected_success": 0.9, "p95_latency_ms": 2400},
                },
                {
                    "id": "oebp.capability.manipulation.place",
                    "support": "planned",
                    "parameters": {"frame": "world", "unit": "m", "position_tolerance_m": 0.01},
                    "quality": {"expected_success": 0.92, "p95_latency_ms": 2200},
                },
            ],
            "safety_envelopes": [
                {"id": "bench-cell", "max_contact_force_n": 20, "requires_guarded_workspace": True}
            ],
            "adapter_bindings": [
                _binding(
                    COMMON_SKILLS["estimate_pose"],
                    {"type": "local_function", "name": "fixed_arm_estimate_pose"},
                    {"entity": "entity_id"},
                ),
                _binding(
                    COMMON_SKILLS["reach"],
                    {"type": "motion_planner", "planner": "fixed_arm_rrt_connect", "planning_group": "arm"},
                    {"target": "goal.target_ref", "effector": "goal.tool_ref"},
                ),
                _binding(
                    COMMON_SKILLS["grasp"],
                    {"type": "vendor_sdk", "sdk": "reference_fixed_arm", "method": "close_gripper"},
                    {"object": "goal.object_ref", "effector": "goal.tool_ref"},
                    {"SUCCESS": "succeeded", "SLIP": "oebp.error.manipulation.object_slipped@1"},
                ),
                _binding(
                    COMMON_SKILLS["lift"],
                    {"type": "motion_planner", "planner": "fixed_arm_cartesian_lift", "planning_group": "arm"},
                    {"distance_m": "goal.delta_z_m", "effector": "goal.tool_ref"},
                ),
                _binding(
                    COMMON_SKILLS["place"],
                    {"type": "motion_planner", "planner": "fixed_arm_cartesian_place", "planning_group": "arm"},
                    {"target": "goal.target_ref", "effector": "goal.tool_ref"},
                ),
                _binding(
                    COMMON_SKILLS["verify"],
                    {"type": "local_function", "name": "fixed_arm_verify_predicate"},
                    {"predicate": "predicate_name"},
                ),
                _binding(
                    COMMON_SKILLS["release"],
                    {"type": "vendor_sdk", "sdk": "reference_fixed_arm", "method": "open_gripper"},
                    {"effector": "goal.tool_ref"},
                ),
            ],
        },
    }


def _mobile_manipulator_profile() -> dict[str, Any]:
    return {
        "protocol": "oebp",
        "version": "0.1.0",
        "kind": "CapabilityProfile",
        "metadata": {
            "id": "org.oebp.adapters.mobile-manipulator.reference",
            "revision": "1.0.0",
            "created_at": "2026-06-16T09:00:00Z",
        },
        "spec": {
            "embodiment_id": "org.oebp.robot.reference-mobile-manipulator",
            "embodiment_class": "mobile_manipulator",
            "effectors": [
                {
                    "id": "robot/right_gripper",
                    "type": "parallel_gripper",
                    "frame": "robot/right_gripper_tool",
                    "max_payload_kg": 1.5,
                    "max_aperture_m": 0.09,
                    "force_feedback": True,
                }
            ],
            "sensors": [
                {"id": "robot/head_rgbd", "type": "depth_camera", "frame": "robot/head_camera", "rate_hz": 30},
                {"id": "robot/base_lidar", "type": "lidar", "frame": "robot/base_link", "rate_hz": 10},
                {"id": "robot/wrist_ft", "type": "force_torque", "frame": "robot/right_gripper_tool", "rate_hz": 200},
            ],
            "frames": [
                {"id": "world"},
                {"id": "robot/map", "parent": "world"},
                {"id": "robot/base_link", "parent": "robot/map"},
                {"id": "robot/head_camera", "parent": "robot/base_link"},
                {"id": "robot/right_gripper_tool", "parent": "robot/base_link"},
            ],
            "capabilities": [
                {
                    "id": "oebp.capability.perception.object_pose",
                    "support": "policy",
                    "parameters": {"frame": "world", "unit": "m", "max_range_m": 4.0},
                    "quality": {"expected_success": 0.92, "p95_latency_ms": 180},
                },
                {
                    "id": "oebp.capability.manipulation.grasp",
                    "support": "planned",
                    "parameters": {"max_payload_kg": 1.5, "max_aperture_m": 0.09, "force_feedback": True},
                    "quality": {"expected_success": 0.86, "p95_latency_ms": 3500},
                },
                {
                    "id": "oebp.capability.manipulation.place",
                    "support": "planned",
                    "parameters": {"frame": "world", "unit": "m", "position_tolerance_m": 0.02},
                    "quality": {"expected_success": 0.9, "p95_latency_ms": 3200},
                },
                {
                    "id": "oebp.capability.locomotion.navigate",
                    "support": "native",
                    "parameters": {"max_speed_m_s": 0.5, "localization_frame": "robot/map"},
                    "quality": {"expected_success": 0.88, "p95_latency_ms": 5000},
                },
            ],
            "safety_envelopes": [
                {"id": "shared-space", "max_base_speed_m_s": 0.5, "max_contact_force_n": 25}
            ],
            "adapter_bindings": [
                _binding(
                    COMMON_SKILLS["estimate_pose"],
                    {"type": "policy_model", "model": "mobile_rgbd_pose_policy_v1"},
                    {"entity": "observation.entity_ref"},
                ),
                _binding(
                    COMMON_SKILLS["reach"],
                    {"type": "behavior_tree", "tree": "navigate_and_reach.xml"},
                    {"target": "blackboard.target_ref", "effector": "blackboard.tool_ref"},
                ),
                _binding(
                    COMMON_SKILLS["grasp"],
                    {"type": "ros2_action", "endpoint": "/right_arm/grasp", "message_type": "oebp_msgs/action/Grasp"},
                    {"object": "goal.object_id", "effector": "goal.effector_id"},
                    {"SUCCEEDED": "succeeded", "SLIP": "oebp.error.manipulation.object_slipped@1"},
                ),
                _binding(
                    COMMON_SKILLS["lift"],
                    {"type": "ros2_action", "endpoint": "/right_arm/lift", "message_type": "oebp_msgs/action/Lift"},
                    {"distance_m": "goal.distance_m", "effector": "goal.effector_id"},
                ),
                _binding(
                    COMMON_SKILLS["place"],
                    {"type": "ros2_action", "endpoint": "/right_arm/place", "message_type": "oebp_msgs/action/Place"},
                    {"target": "goal.target_id", "effector": "goal.effector_id"},
                ),
                _binding(
                    COMMON_SKILLS["verify"],
                    {"type": "policy_model", "model": "mobile_relation_verifier_v1"},
                    {"predicate": "query.predicate"},
                ),
                _binding(
                    COMMON_SKILLS["release"],
                    {"type": "ros2_action", "endpoint": "/right_arm/release", "message_type": "oebp_msgs/action/Release"},
                    {"effector": "goal.effector_id"},
                ),
            ],
        },
    }
