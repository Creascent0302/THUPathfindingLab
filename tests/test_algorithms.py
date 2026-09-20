"""Behavioral checks for target identity, temporal safety and deployment boundaries."""

import ast
import importlib.util
import json
from pathlib import Path

import numpy as np
import pytest

from algorithms.modular.algorithm import TemporalMPC, TemporalPursuit
from algorithms.modular.vision import BirdEye, thinning
from algorithms.scanline import ScanlinePID
from pathlab.config import RunConfig
from pathlab.registry import registry
from pathlab.scenarios import generate
from pathlab.sdk import Observation, TaskHint
from pathlab.simulation import Renderer, world_to_vehicle


@pytest.mark.parametrize("model", ["kinematic_v1", "inertial_v2"])
def test_command_motion_estimate_matches_vehicle_with_lateral_momentum(model):
    from algorithms.modular.control import MotionEstimate
    from pathlab.config import Pose, VehicleConfig
    from pathlab.sdk import Action
    from pathlab.simulation import Vehicle

    limits = VehicleConfig(motion_model=model)
    vehicle = Vehicle(limits, Pose(x_m=3, y_m=-2, yaw_rad=0.7))
    estimate = MotionEstimate(limits.model_dump())
    for steering, speed in [(0.45, 1.0)] * 12 + [(-0.35, 0.65)] * 9 + [(0, 0)] * 8:
        action = Action(steering_angle_rad=steering, speed_mps=speed)
        before = vehicle.state.model_copy()
        for _ in range(3):
            vehicle.advance(action, 0.05)
        displacement, yaw = estimate.advance(action, 0.15, 0.05)
        expected = world_to_vehicle(
            np.array([[vehicle.state.x_m, vehicle.state.y_m]]), before
        )[0]
        np.testing.assert_allclose(displacement, expected, atol=1e-11)
        expected_yaw = (vehicle.state.yaw_rad - before.yaw_rad + np.pi) % (
            2 * np.pi
        ) - np.pi
        assert yaw == pytest.approx(expected_yaw, abs=1e-11)
        assert estimate.speed == pytest.approx(vehicle.state.speed_mps, abs=1e-11)
        angle = vehicle.state.yaw_rad
        lateral = (
            -np.sin(angle) * vehicle.state.velocity_x_mps
            + np.cos(angle) * vehicle.state.velocity_y_mps
        )
        assert estimate.state[4] == pytest.approx(lateral, abs=1e-11)
    assert estimate.speed == 0


def test_learning_checkpoint_selection_preserves_explicit_legacy_models():
    from algorithms.learning.algorithm import (
        INERTIAL_CHECKPOINT,
        LEGACY_CHECKPOINT,
        checkpoint_for_limits,
    )

    assert checkpoint_for_limits({}).name == "driver-complex.pt"
    assert (
        checkpoint_for_limits({"motion_model": "kinematic_v1"}).name
        == "driver-complex.pt"
    )
    assert (
        checkpoint_for_limits({"motion_model": "inertial_v2"}).name
        == "driver-complex.pt"
    )
    assert LEGACY_CHECKPOINT.name == "driver.pt" and LEGACY_CHECKPOINT.is_file()
    assert (
        INERTIAL_CHECKPOINT.name == "driver-inertial.pt"
        and INERTIAL_CHECKPOINT.is_file()
    )
    assert checkpoint_for_limits({}, legacy=True) == LEGACY_CHECKPOINT
    assert (
        checkpoint_for_limits({"motion_model": "inertial_v2"}, legacy=True)
        == INERTIAL_CHECKPOINT
    )


def observation(scene, frame=0, *, blank=False):
    renderer = Renderer(scene)
    rgb = renderer.render(scene.initial_pose, frame)
    if blank:
        rgb[:] = 220
    return Observation.from_rgb(
        rgb,
        episode_id="public-only",
        frame_id=frame,
        timestamp_s=frame * scene.dt_s,
        dt_s=scene.dt_s,
        calibration=renderer.camera.calibration(),
        task_hint=scene.task_hint,
    )


def initialized(policy_type=TemporalPursuit, family="parallel", **parameters):
    scene = generate(family, 37)
    obs = observation(scene)
    policy = policy_type()
    policy.initialize(parameters, {"vehicle_limits": scene.vehicle.model_dump()})
    policy.reset(obs, obs.task_hint)
    return policy, scene, obs


def assert_policy_steps_and_continuous_stop(run, count):
    driving = [
        row for row in run.records if "safety_braking" not in row["interventions"]
    ]
    braking = [row for row in run.records if "safety_braking" in row["interventions"]]
    assert len(driving) == count
    assert braking and braking[0]["pose_before"] == driving[-1]["pose"]
    assert braking[-1]["pose"]["speed_mps"] == 0
    assert all(row["applied"]["requested"]["speed_mps"] == 0 for row in braking)


@pytest.mark.parametrize("policy_type", [TemporalPursuit, TemporalMPC, ScanlinePID])
def test_marker_selects_target_instead_of_nearer_distractor(policy_type):
    policy, scene, obs = initialized(policy_type)
    result = policy.step(obs)
    assert result.status == "ACQUIRE"
    local = np.array(result.local_path_m)
    target = world_to_vehicle(np.array(scene.target_path), scene.initial_pose)
    distractor = world_to_vehicle(np.array(scene.distractors[0]), scene.initial_pose)
    target_error = np.linalg.norm(local[:, None] - target[None], axis=2).min(axis=1)
    wrong_error = np.linalg.norm(local[:, None] - distractor[None], axis=2).min(axis=1)
    assert np.median(target_error) < 0.04
    assert np.median(wrong_error) > 0.25
    assert 0 < result.action.speed_mps <= scene.vehicle.max_speed_mps


@pytest.mark.parametrize("policy_type", [TemporalPursuit, ScanlinePID])
def test_ambiguous_initialization_stops(policy_type):
    policy, scene, _ = initialized(policy_type)
    scene.appearance.marker_enabled = False
    scene.task_hint = TaskHint(kind="none")
    obs = observation(scene)
    policy.reset(obs, obs.task_hint)
    result = policy.step(obs)
    assert result.status == "AMBIGUOUS"
    assert result.action.speed_mps == 0
    assert result.local_path_m is None


@pytest.mark.parametrize("policy_type", [TemporalPursuit, ScanlinePID])
def test_occlusion_memory_expires_and_original_target_recovers(policy_type):
    policy, scene, obs = initialized(policy_type, memory_s=0.2)
    policy.step(obs)
    predicted = policy.step(observation(scene, 1, blank=True))
    assert predicted.debug["prediction_only"]
    assert 0 < predicted.action.speed_mps <= 0.35
    for frame in range(2, 9):
        stopped = policy.step(observation(scene, frame, blank=True))
    assert stopped.status == "LOST"
    assert stopped.action.speed_mps == 0
    recovered = policy.step(observation(scene, 9))
    assert recovered.status in {"ACQUIRE", "TRACK"}
    assert not recovered.debug["prediction_only"]


@pytest.mark.parametrize("policy_type", [TemporalPursuit, TemporalMPC, ScanlinePID])
def test_reset_is_reproducible_and_time_reversal_is_rejected(policy_type):
    policy, scene, obs = initialized(policy_type)
    first = policy.step(obs).model_dump()
    policy.step(observation(scene, 1))
    assert policy.step(obs).status == "ERROR"
    policy.reset(obs, obs.task_hint)
    assert policy.step(obs).model_dump() == first


def test_changed_public_calibration_is_used():
    policy, scene, obs = initialized()
    policy.step(obs)
    scene.camera.width, scene.camera.height = 320, 180
    scene.camera.pitch_down_rad = 0.61
    result = policy.step(observation(scene, 1))
    assert result.status in {"ACQUIRE", "TRACK"}
    assert policy.tracker.camera.size == (320, 180)
    assert np.isfinite(result.local_path_m).all()


def test_missing_calibration_has_explicit_error():
    policy, _, obs = initialized()
    obs.calibration = None
    result = policy.step(obs)
    assert result.status == "ERROR"
    assert result.action.speed_mps == 0
    assert "标定" in result.diagnostics[0]


def test_skeleton_preserves_two_disconnected_lines():
    mask = np.zeros((50, 50), np.uint8)
    mask[3:47, 12:17] = 1
    mask[3:47, 21:26] = 1
    skeleton = thinning(mask)
    assert skeleton[:, 17:21].sum() == 0
    assert skeleton[:, :17].sum() > 30
    assert skeleton[:, 21:].sum() > 30


def test_metric_geometry_round_trip():
    _, _, obs = initialized()
    camera = BirdEye(obs.calibration)
    from algorithms.modular.vision import transform_points

    points = np.array([[0.8, 0.2], [2, -0.6], [4, 1]])
    np.testing.assert_allclose(
        transform_points(camera.pixels(points), camera.inv),
        points,
        atol=1e-10,
    )


def test_deployment_modules_do_not_import_private_world_or_training_expert():
    root = Path(__file__).resolve().parents[1]
    sources = [
        root / "algorithms/scanline.py",
        root / "algorithms/avoidance.py",
        *sorted((root / "algorithms/modular").glob("*.py")),
        root / "algorithms/learning/algorithm.py",
        root / "algorithms/learning/model.py",
    ]
    forbidden = {"simulation", "evaluation", "scenarios", "storage", "data", "train"}
    for path in sources:
        tree = ast.parse(path.read_text())
        for node in ast.walk(tree):
            modules = (
                [node.module or ""]
                if isinstance(node, ast.ImportFrom)
                else [n.name for n in node.names]
                if isinstance(node, ast.Import)
                else []
            )
            assert not any(set(module.split(".")) & forbidden for module in modules), (
                path
            )


@pytest.mark.parametrize(
    "name",
    [
        "temporal_pursuit",
        "temporal_mpc",
        "scanline_pid",
        "temporal_pursuit_avoidance",
        "temporal_mpc_avoidance",
    ],
)
def test_reference_algorithms_run_in_real_worker(execute, name):
    run = execute(RunConfig(algorithm=name, max_steps=8, realtime=False))
    assert not run.failures
    assert_policy_steps_and_continuous_stop(run, 8)
    assert run.records[0]["output"]["action"]["speed_mps"] > 0
    assert run.worker.process.poll() is not None


@pytest.mark.skipif(
    importlib.util.find_spec("torch") is None, reason="optional learning dependency"
)
def test_learned_missing_checkpoint_fails_clearly(tmp_path):
    from algorithms.learning.algorithm import RecurrentPolicy

    policy = RecurrentPolicy()
    with pytest.raises(RuntimeError, match="缺少权重"):
        policy.initialize({"checkpoint": str(tmp_path / "missing.pt")}, {})


@pytest.mark.skipif(
    registry()["cnn_gru"].unavailable_reason() is not None,
    reason="trained learning plugin unavailable",
)
def test_learned_checkpoint_reset_and_actual_worker(execute):
    from algorithms.learning.algorithm import RecurrentPolicy

    policy, scene, obs = initialized(RecurrentPolicy)
    first = policy.step(obs)
    assert first.debug["model_id"].startswith("cpu-")
    held = policy.step(observation(scene, 1))
    assert not held.debug["network_updated"]
    with pytest.raises(ValueError, match="时间倒退"):
        policy.step(obs)
    policy.reset(obs, obs.task_hint)
    assert policy.step(obs).model_dump() == first.model_dump()
    run = execute(RunConfig(algorithm="cnn_gru", max_steps=8, realtime=False))
    assert not run.failures
    assert_policy_steps_and_continuous_stop(run, 8)


@pytest.mark.skipif(
    importlib.util.find_spec("torch") is None, reason="optional learning dependency"
)
def test_training_refuses_reserved_test_scenes(tmp_path):
    from algorithms.learning.train import Sequences

    (tmp_path / "manifest.json").write_text(
        json.dumps(
            {
                "episodes": [
                    {
                        "family": "straight",
                        "seed": 1001,
                        "split": "development",
                        "frames": 50,
                        "file": "unused.npz",
                    },
                ]
            }
        )
    )
    with pytest.raises(ValueError, match="测试场景禁止"):
        Sequences([tmp_path], "development")


@pytest.mark.skipif(
    importlib.util.find_spec("torch") is None, reason="optional learning dependency"
)
def test_learning_flip_and_acquisition_weight_are_consistent(tmp_path, monkeypatch):
    from algorithms.learning.train import Sequences

    images = np.zeros((40, 96, 160, 4), np.uint8)
    images[:, :, :80, :3] = 255
    context = np.zeros((40, 5), np.float32)
    context[:, 0] = 0.3
    actions = np.tile(np.array([0.2, 0.6], np.float32), (40, 1))
    np.savez_compressed(
        tmp_path / "episode.npz",
        images=images,
        context=context,
        actions=actions,
        visible=np.ones(40, np.float32),
    )
    (tmp_path / "manifest.json").write_text(
        json.dumps(
            {
                "episodes": [
                    {
                        "family": "straight",
                        "seed": 3,
                        "split": "development",
                        "frames": 40,
                        "file": "episode.npz",
                    },
                ]
            }
        )
    )
    monkeypatch.setattr("algorithms.learning.train.random.random", lambda: 0)
    sequence = Sequences([tmp_path], "development", 4, acquisition_weight=8)
    image, history, action, _, weight = sequence[0]
    assert image[:, :3, :, :80].sum() == 0
    assert image[:, :3, :, 80:].min() == 1
    np.testing.assert_allclose(action[:, 0], -0.2)
    np.testing.assert_allclose(history[:, 0], -0.3)
    np.testing.assert_allclose(action[:, 1], 0.6)
    assert weight.tolist() == [8, 8, 8, 8]


@pytest.mark.skipif(
    registry()["cnn_gru"].unavailable_reason() is not None,
    reason="trained learning plugin unavailable",
)
def test_learning_rejects_untrained_hint_types():
    from algorithms.learning.algorithm import RecurrentPolicy

    policy, _, obs = initialized(RecurrentPolicy)
    with pytest.raises(ValueError, match="默认绿色标记"):
        policy.reset(obs, TaskHint(kind="point", point_px=(200, 150)))
