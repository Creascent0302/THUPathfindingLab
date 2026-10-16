"""Geometry and message-adapter checks; fake schemas are not ROS MD5 validation."""

from __future__ import annotations

import math

import numpy as np
import pytest

from ros_line_follower.messages import make_goal, validate_message_types
from ros_line_follower.planning import PlannerConfig, build_reference


class RefPoint:
    __slots__ = (
        "t",
        "x",
        "y",
        "v",
        "heading",
        "cr",
        "left_width",
        "right_width",
        "turning_flag",
    )
    _slot_types = ("float64",) * 8 + ("int16",)
    _type = "vehicle_contract/RefPoint"


class Goal:
    __slots__ = ("timestamp", "Estop", "Go", "Signal", "refPath", "mode", "objects")
    _slot_types = (
        "float64",
        "int16",
        "bool",
        "int16",
        "vehicle_contract/RefPoint[]",
        "int16",
        "vehicle_contract/Object[]",
    )
    _type = "vehicle_contract/Goal"


def straight(length=12):
    return np.column_stack(
        (
            np.linspace(0.0, length, int(length / 0.1) + 1),
            np.zeros(int(length / 0.1) + 1),
        )
    )


def kwargs():
    return dict(
        pose_xy_yaw=(10, 20, math.pi / 2),
        output_frame="world",
        point_time_mode="absolute",
        mode=3,
    )


def test_straight_metric_path_stops_with_finite_time_and_braking():
    config = PlannerConfig()
    reference = build_reference(straight(), config, 1.0)
    assert reference.length_m == pytest.approx(10.0)
    assert reference.points[0] == pytest.approx((0, 0))
    assert reference.points[-1] == pytest.approx((10, 0))
    ds = np.linalg.norm(np.diff(reference.points, axis=0), axis=1)
    assert np.max(ds) <= config.spacing_m + 1e-9
    assert np.ptp(ds) < 1e-8
    assert np.allclose(reference.heading, 0)
    assert np.allclose(reference.curvature, 0)
    assert np.max(reference.speed) <= config.max_speed_mps
    assert reference.speed[-1] == 0
    assert np.all(
        reference.speed[:-1] ** 2
        <= reference.speed[1:] ** 2 + 2 * config.braking_mps2 * ds + 1e-9
    )
    assert np.all(np.isfinite(reference.time))
    assert reference.time[0] == 0
    assert np.all(np.diff(reference.time) > 0)


def test_u_turn_preserves_order_and_curvature_speed_limit():
    radius = 2.5
    angles = np.linspace(0, math.pi, 150)
    points = np.column_stack((radius * np.sin(angles), radius * (1 - np.cos(angles))))
    config = PlannerConfig(
        target_length_m=8, max_speed_mps=2, max_lateral_accel_mps2=0.2
    )
    reference = build_reference(points, config, 1)
    assert np.any(np.diff(reference.points[:, 0]) < 0)
    assert reference.points[-1, 1] > 4.8
    assert np.mean(reference.curvature[8:-8]) == pytest.approx(1 / radius, abs=0.02)
    assert np.all(
        reference.speed**2 * np.abs(reference.curvature)
        <= config.max_lateral_accel_mps2 + 1e-9
    )
    assert np.all(np.diff(np.unwrap(reference.heading)) >= -1e-6)


def test_visible_prefix_is_not_extended_across_a_gap_or_to_target():
    points = np.vstack((straight(7), straight(10) + (20, 0)))
    reference = build_reference(points, PlannerConfig(), 1)
    assert reference.length_m == pytest.approx(6.6)
    assert reference.points[-1, 0] == pytest.approx(6.6)
    with pytest.raises(ValueError, match="short|discontinuity"):
        build_reference(
            np.vstack((straight(2), straight(12) + (20, 0))), PlannerConfig(), 1
        )
    with pytest.raises(ValueError, match="short"):
        build_reference(straight(5.2), PlannerConfig(), 1)


def test_duplicate_points_are_removed_and_noise_is_bounded():
    points = straight()
    points[:, 1] = 0.012 * np.sin(points[:, 0] * 15)
    points = np.repeat(points, 2, axis=0)
    reference = build_reference(points, PlannerConfig(), 1)
    assert np.max(np.abs(reference.points[:, 1])) < 0.012
    assert np.all(np.linalg.norm(np.diff(reference.points, axis=0), axis=1) > 0)


def test_excessive_curvature_and_wrong_heading_are_rejected():
    angles = np.linspace(0, 1.8 * math.pi, 200)
    sharp = np.column_stack((np.sin(angles), 1 - np.cos(angles)))
    with pytest.raises(ValueError, match="curvature"):
        build_reference(sharp, PlannerConfig(), 1)
    sideways = straight()[:, ::-1] + (0.1, 0)
    with pytest.raises(ValueError, match="forward|heading"):
        build_reference(sideways, PlannerConfig(), 1)
    with pytest.raises(ValueError, match="start"):
        build_reference(straight() + (3, 0), PlannerConfig(), 1)


@pytest.mark.parametrize("confidence", [0.1, -1, 1.1, float("nan")])
def test_invalid_confidence_does_not_make_a_driving_path(confidence):
    with pytest.raises(ValueError, match="confidence"):
        build_reference(straight(), PlannerConfig(), confidence)


@pytest.mark.parametrize(
    "points", [[], [[0, 0], [1, 1]], [[0, 0], [1, float("nan")], [2, 0]], [[0, 0]] * 10]
)
def test_invalid_path_rejected(points):
    with pytest.raises(ValueError):
        build_reference(points, PlannerConfig(), 1)


def test_goal_fields_world_transform_and_observation_timestamp():
    config = PlannerConfig()
    reference = build_reference(straight(), config, 1)
    goal = make_goal(Goal, RefPoint, reference, 123.5, config, **kwargs())
    assert goal.timestamp == 123.5
    assert goal.Estop == 0 and goal.Go is True and goal.Signal == 0
    assert goal.mode == 3 and goal.objects == []
    assert len(goal.refPath) == len(reference.points)
    assert (goal.refPath[0].x, goal.refPath[0].y) == pytest.approx((10, 20))
    assert (goal.refPath[-1].x, goal.refPath[-1].y) == pytest.approx((10, 30))
    for index, point in enumerate(goal.refPath):
        assert point.heading == pytest.approx(math.pi / 2)
        assert point.t == pytest.approx(123.5 + reference.time[index])
        assert point.cr == pytest.approx(reference.curvature[index])
        assert point.left_width == config.left_width_m
        assert point.right_width == config.right_width_m
        assert point.turning_flag == 0
        assert all(hasattr(point, field) for field in RefPoint.__slots__)


def test_vehicle_relative_output_and_ros_stamp():
    class Stamp:
        def to_sec(self):
            return 500.0

    config = PlannerConfig()
    reference = build_reference(straight(), config, 1)
    options = kwargs()
    options.update(output_frame="vehicle", point_time_mode="relative", pose_xy_yaw=None)
    goal = make_goal(Goal, RefPoint, reference, Stamp(), config, **options)
    assert goal.timestamp == 500.0
    assert goal.refPath[0].t == 0
    assert goal.refPath[-1].x == pytest.approx(10)
    assert goal.refPath[-1].y == pytest.approx(0)
    assert goal.refPath[-1].t == reference.time[-1]


def test_stop_is_explicit_and_has_no_old_path_or_objects():
    goal = make_goal(
        Goal,
        RefPoint,
        None,
        123.5,
        PlannerConfig(),
        enabled=False,
        estop_level=2,
        **kwargs(),
    )
    assert goal.Go is False and goal.Estop == 2
    assert goal.Signal == 0 and goal.refPath == [] and goal.objects == []
    assert goal.timestamp == 123.5
    assert all(hasattr(goal, field) for field in Goal.__slots__)


def test_absolute_time_must_retain_point_time_precision():
    config = PlannerConfig()
    with pytest.raises(ValueError, match="precision"):
        make_goal(
            Goal,
            RefPoint,
            build_reference(straight(), config, 1),
            1e20,
            config,
            **kwargs(),
        )


def test_schema_validation_uses_exact_fields_and_real_package_references():
    validate_message_types(Goal, RefPoint)

    class WrongPoint(RefPoint):
        __slots__ = RefPoint.__slots__
        _slot_types = ("float32",) + RefPoint._slot_types[1:]

    class WrongCase(Goal):
        __slots__ = ("timestamp", "estop", "Go", "Signal", "refPath", "mode", "objects")

    class WrongPackage(Goal):
        __slots__ = Goal.__slots__
        _slot_types = (
            Goal._slot_types[:4] + ("guessed/RefPoint[]",) + Goal._slot_types[5:]
        )

    class WrongObject(Goal):
        __slots__ = Goal.__slots__
        _slot_types = Goal._slot_types[:-1] + ("vehicle_contract/Obstacle[]",)

    for goal_class, point_class in [
        (Goal, WrongPoint),
        (WrongCase, RefPoint),
        (WrongPackage, RefPoint),
        (WrongObject, RefPoint),
    ]:
        with pytest.raises(ValueError):
            validate_message_types(goal_class, point_class)


@pytest.mark.parametrize(
    "changes",
    [
        {"output_frame": "map"},
        {"point_time_mode": "auto"},
        {"mode": 0},
        {"pose_xy_yaw": (float("nan"), 0, 0)},
        {"estop_level": 0},
    ],
)
def test_unknown_coordinate_or_command_semantics_rejected(changes):
    config = PlannerConfig()
    options = kwargs()
    options.update(changes)
    with pytest.raises(ValueError):
        make_goal(
            Goal,
            RefPoint,
            build_reference(straight(), config, 1),
            123,
            config,
            **options,
        )
