"""Student path contracts, ordered execution and direct-start classroom maps."""

import math
from pathlib import Path

import numpy as np
import pytest

from pathlab.adapters import PurePursuit, execution_action
from pathlab.config import Pose, RunConfig, Scene
from pathlab.engine import Run
from pathlab.scenarios import FAMILIES, generate, validate_scene
from pathlab.sdk import Action, AlgorithmOutput, TaskHint
from pathlab.simulation import Vehicle


def output(points, **kwargs):
    return AlgorithmOutput(
        status="TRACK", confidence=0.8, local_path_m=points, **kwargs
    )


@pytest.mark.parametrize("side", [-1, 1])
def test_sampling_density_does_not_change_command(side):
    sparse = np.array([[0.2, 0], [0.8, side * 0.4], [1.3, side * 0.8]])
    dense = np.vstack(
        [np.linspace(a, b, 40)[:-1] for a, b in zip(sparse[:-1], sparse[1:])]
        + [sparse[-1:]]
    )
    adapter = PurePursuit(0.32, 1.5)
    a = adapter.action(output(sparse.tolist()))
    b = adapter.action(output(dense.tolist()))
    assert a.steering_angle_rad == pytest.approx(b.steering_angle_rad, abs=1e-12)
    assert a.speed_mps == pytest.approx(b.speed_mps, abs=1e-12)
    assert side * a.steering_angle_rad > 0


def test_short_visible_prefix_does_not_skip_to_returning_branch():
    adapter = PurePursuit(0.32, 1.5)
    prefix = [(0.12, 0), (0.2, 0), (0.1, 0)]
    returning = [(-0.5, -0.2), (-0.5, -1), (0.8, -1), (1.5, -1)]
    assert adapter.action(output(prefix)) == adapter.action(output(prefix + returning))


def test_path_controls_ignore_action_and_pixel_overlay():
    adapter = PurePursuit(0.32, 1.5, max_steering_rad=0.3)
    predicted = output(
        [(0.2, 0.1), (0.6, 0.5)],
        action=Action(steering_angle_rad=-0.5, speed_mps=-1),
        centerline_px=[(0, 0), (10, 10)],
    )
    command, _ = execution_action(predicted, "path", adapter)
    assert 0 < command.steering_angle_rad <= 0.3
    assert command.speed_mps > 0
    assert execution_action(predicted, "perception", adapter)[0].speed_mps == 0
    with pytest.raises(ValueError, match="local_path_m"):
        execution_action(
            AlgorithmOutput(status="TRACK", centerline_px=[(1, 1), (2, 2)]),
            "path",
            adapter,
        )


def test_behind_path_and_lost_status_request_braking_with_inertia():
    adapter = PurePursuit(0.32, 1.5)
    assert adapter.action(output([(-1, 0), (-0.1, 0)])).speed_mps == 0
    scene = generate("straight")
    car = Vehicle(scene.vehicle, scene.initial_pose)
    drive = adapter.action(output([(0.1, 0), (1, 0)]))
    for _ in range(40):
        car.advance(drive, scene.dt_s)
    before = car.state.speed_mps
    stop, events = execution_action(AlgorithmOutput(status="LOST"), "path", adapter)
    car.advance(stop, scene.dt_s)
    assert stop.speed_mps == 0 and events == ["status_stop:LOST"]
    assert 0 < car.state.speed_mps <= before
    for _ in range(100):
        car.advance(stop, scene.dt_s)
    assert car.state.speed_mps == 0


@pytest.mark.parametrize("family", FAMILIES)
def test_classroom_maps_are_legal_obstacle_free_and_start_aligned(family):
    for seed in (7, 1009):
        scene = generate(family, seed)
        assert scene.category == "core" and scene.start_mode == "on_path"
        assert not scene.objects and not scene.appearance.occlusion
        assert validate_scene(scene) == []
        first, second = np.asarray(scene.target_path[:2])
        assert (scene.initial_pose.x_m, scene.initial_pose.y_m) == tuple(first)
        assert scene.initial_pose.yaw_rad == pytest.approx(
            math.atan2(*(second - first)[::-1])
        )
        assert scene.task_hint.kind == "none"
    for path in Path("scenarios/challenges").glob(f"*-{family}.json"):
        assert Scene.model_validate_json(path.read_text()) == generate(family, 7)


def test_legacy_pose_and_hint_are_ignored_without_mutating_saved_scene(tmp_path):
    old = generate("bend")
    old.initial_pose = Pose(x_m=-1.5, y_m=0.3, yaw_rad=0.2)
    old.start_mode = "approach"
    stale_hint = TaskHint(kind="point", point_px=(-30, 999))
    old.task_hint = stale_hint
    original = old.model_dump_json()
    run = Run(RunConfig(scene=old, task_hint=stale_hint), tmp_path, headless=True)
    try:
        assert old.model_dump_json() == original
        assert run.scene.initial_pose == old.at_start().initial_pose
        assert run.hint.kind == "none"
        assert run.config.scene == run.scene
        assert run.evaluator.acquired_at == 0
        assert run.evaluator.progress == 0
    finally:
        run.store.rows.close()


def test_camera_must_see_route_after_start():
    scene = generate("tight_s")
    scene.camera.horizontal_fov_deg = 30
    scene.camera.pitch_down_rad = 0.15
    assert any("相机看不到" in message for message in validate_scene(scene))


def test_imported_core_route_must_obey_same_clearance_as_editor():
    scene = generate("spiral_dense")
    scene.vehicle.width_m = 0.4
    assert any("非相邻路段" in message for message in validate_scene(scene))
