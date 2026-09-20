"""Route identity is ordered even when rendered lines are almost coincident."""

import math

import numpy as np
import pytest

from pathlab.config import Pose, Scene, VehicleConfig
from pathlab.evaluation import EVALUATOR_VERSION, SCORE_VERSION, Evaluator, comparison_key
from pathlab.sdk import Action
from pathlab.scenarios import PathBuilder
from pathlab.simulation import Vehicle, VehicleState


def scene_with_return(*, gap=0.12, initial=None, distractors=None):
    return Scene(
        name="nearby nonlocal return",
        family="test",
        seed=7,
        target_path=[
            (0, 0), (4, 0), (6, 2), (4, 4), (-2, 4),
            (-2, gap), (0, gap), (4, gap),
        ],
        initial_pose=initial or Pose(),
        distractors=distractors or [],
        vehicle=VehicleConfig(),
    )


def drive(evaluator, vehicle, action, *, steps=200):
    rows = []
    for i in range(steps):
        vehicle.advance(action, evaluator.scene.dt_s)
        rows.append(evaluator.update(vehicle.state, (i + 1) * evaluator.scene.dt_s))
        if evaluator.done_reason:
            break
    return rows


def follow_geometry(evaluator, offset=0.0):
    """Independent geometry oracle; this is not an algorithm rollout."""
    path = evaluator.path
    arc = np.arange(0.0, path.total, 0.03)
    points = np.column_stack([
        np.interp(arc, path.arc, path.points[:, axis]) for axis in range(2)
    ])
    tangent = np.gradient(points, axis=0)
    tangent /= np.linalg.norm(tangent, axis=1)[:, None]
    normal = np.column_stack([-tangent[:, 1], tangent[:, 0]])
    points += normal * (offset * np.minimum(1, arc))[:, None]
    tangent = np.gradient(points, axis=0)
    for index, (point, direction) in enumerate(zip(points, tangent)):
        evaluator.update(
            VehicleState(
                x_m=float(point[0]), y_m=float(point[1]),
                yaw_rad=math.atan2(direction[1], direction[0]),
            ),
            (index + 1) * evaluator.scene.dt_s,
        )
        if evaluator.done_reason:
            break


@pytest.mark.parametrize("motion_model", ["kinematic_v1", "inertial_v2"])
def test_continuous_vehicle_cannot_take_nearby_nonlocal_target_branch(motion_model):
    scene = scene_with_return(initial=Pose(yaw_rad=0.18))
    scene.vehicle.motion_model = motion_model
    evaluator = Evaluator(scene)
    vehicle = Vehicle(scene.vehicle, scene.initial_pose)
    rows = drive(evaluator, vehicle, Action(steering_angle_rad=0, speed_mps=0.45))
    assert evaluator.acquired_at is not None
    assert evaluator.done_reason == "illegal_switch"
    # This wrong road is still inside both old tracking tolerances. It must not
    # supply either a valid reference distance or unearned progress.
    assert rows[-1]["lateral_error_m"] < 0.24
    assert rows[-1]["heading_error_rad"] < 0.65
    assert evaluator.switches[0]["other_route"]["kind"] == "target_nonlocal"
    assert evaluator.switches[0]["other_route"]["arc_m"] > 15
    suspicious = [r for r in rows if r["route_identity"] == "wrong_branch"]
    assert len(suspicious) >= 10
    assert len({r["progress_m"] for r in suspicious}) == 1
    assert evaluator.progress < 1


def test_global_target_return_cannot_hide_an_independent_distractor():
    scene = scene_with_return(
        gap=0.14,
        initial=Pose(yaw_rad=0.18),
        distractors=[[(-1, 0.12), (5, 0.12)]],
    )
    evaluator = Evaluator(scene)
    vehicle = Vehicle(scene.vehicle, scene.initial_pose)
    rows = drive(evaluator, vehicle, Action(steering_angle_rad=0, speed_mps=0.45))
    assert evaluator.done_reason == "illegal_switch"
    alternative = rows[-1]["other_route"]
    assert alternative["kind"] == "distractor"
    assert alternative["index"] == 0
    assert alternative["distance_m"] < 0.04


def test_wrong_road_near_start_does_not_count_as_acquisition():
    scene = scene_with_return(initial=Pose(x_m=-1.5, y_m=0.12))
    evaluator = Evaluator(scene)
    vehicle = Vehicle(scene.vehicle, scene.initial_pose)
    rows = drive(evaluator, vehicle, Action(steering_angle_rad=0, speed_mps=0.45))
    assert evaluator.acquired_at is None
    assert evaluator.done_reason in {"illegal_switch", "acquisition_failed"}
    assert all(row["completion"] == 0 for row in rows)


def test_slow_continuous_approach_can_outlast_initial_grace():
    scene = scene_with_return(initial=Pose(x_m=-1.5))
    evaluator = Evaluator(scene)
    vehicle = Vehicle(scene.vehicle, scene.initial_pose)
    rows = drive(evaluator, vehicle, Action(steering_angle_rad=0, speed_mps=0.10), steps=340)
    assert evaluator.acquired_at > evaluator.acquisition_grace_s * 2
    assert evaluator.done_reason is None
    assert rows[-1]["phase"] == "tracking"
    assert rows[-1]["route_identity"] == "confirmed"


def test_vehicle_can_leave_an_initial_nearby_line_to_reach_the_start():
    initial = Pose(x_m=-1.5, y_m=0.12, yaw_rad=math.atan2(-0.12, 1.5))
    scene = scene_with_return(initial=initial)
    evaluator = Evaluator(scene)
    vehicle = Vehicle(scene.vehicle, initial)
    rows = drive(evaluator, vehicle, Action(steering_angle_rad=0, speed_mps=0.45), steps=90)
    assert evaluator.acquired_at is not None
    assert evaluator.done_reason is None
    assert rows[-1]["route_identity"] == "confirmed"


@pytest.mark.parametrize("initial", [Pose(x_m=0.40), Pose(yaw_rad=math.pi)])
def test_gate_requires_start_and_forward_direction(initial):
    evaluator = Evaluator(scene_with_return(initial=initial))
    state = VehicleState(**initial.model_dump())
    for i in range(160):
        row = evaluator.update(state, (i + 1) * evaluator.scene.dt_s)
    assert evaluator.acquired_at is None
    assert evaluator.progress == 0
    assert row["reason"] == "acquisition_failed"


def test_correct_path_wins_even_with_close_parallel_return_and_crossing():
    scene = scene_with_return(distractors=[[(1, -2), (1, 2)]])
    evaluator = Evaluator(scene)
    vehicle = Vehicle(scene.vehicle, scene.initial_pose)
    rows = drive(evaluator, vehicle, Action(steering_angle_rad=0, speed_mps=0.45), steps=120)
    assert evaluator.done_reason is None
    assert evaluator.progress > 2
    assert not evaluator.switches
    assert all(row["route_identity"] == "confirmed" for row in rows)


def test_nonlocal_return_becomes_legal_after_the_intervening_route_is_driven():
    evaluator = Evaluator(scene_with_return())
    path = evaluator.path
    follow_geometry(evaluator)
    assert evaluator.done_reason == "success"
    assert evaluator.progress > path.total - 0.18
    assert not evaluator.switches


@pytest.mark.parametrize("radius,offset", [(0.57, 0), (0.8, -0.18), (0.8, 0.18)])
def test_feasible_tight_curves_are_not_nonlocal_branch_switches(radius, offset):
    scene = scene_with_return()
    scene.target_path = (
        PathBuilder().segment(2).turn(math.pi, radius).segment(2)
        .turn(-math.pi, radius).segment(2).points
    )
    evaluator = Evaluator(scene)
    follow_geometry(evaluator, offset)
    assert evaluator.done_reason == "success"
    assert not evaluator.switches


def test_stationary_pose_cannot_expand_its_reachable_arc_window():
    evaluator = Evaluator(scene_with_return())
    state = VehicleState()
    first = evaluator.update(state, 0.05)
    for i in range(1, 200):
        row = evaluator.update(state, (i + 1) * 0.05)
    assert evaluator.progress == 0
    assert row["reference_window_m"][1] == 0
    assert first["completion"] == row["completion"]


def test_terminal_braking_preserves_identity_evidence():
    scene = scene_with_return(initial=Pose(yaw_rad=0.18))
    evaluator = Evaluator(scene)
    vehicle = Vehicle(scene.vehicle, scene.initial_pose)
    terminal = drive(evaluator, vehicle, Action(steering_angle_rad=0, speed_mps=0.45))[-1]
    evaluator.begin_coasting()
    for i in range(40):
        vehicle.advance(Action(steering_angle_rad=0, speed_mps=0), scene.dt_s)
        row = evaluator.update(vehicle.state, 10 + i * scene.dt_s)
    assert row == terminal
    assert len(evaluator.switches) == 1
    assert evaluator.done_reason == "illegal_switch"


def test_identity_revision_changes_fair_comparison_version(monkeypatch):
    scene = scene_with_return().model_dump()
    current = comparison_key({}, scene, "inertial_v2")
    assert EVALUATOR_VERSION == SCORE_VERSION == "4.0"
    monkeypatch.setattr("pathlab.evaluation.EVALUATOR_VERSION", "2.0")
    monkeypatch.setattr("pathlab.evaluation.SCORE_VERSION", "2.0")
    assert comparison_key({}, scene, "inertial_v2") != current
