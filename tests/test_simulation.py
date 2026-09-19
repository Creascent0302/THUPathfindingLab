import math

import numpy as np
import pytest

from pathlab.config import CameraConfig, Pose, VehicleConfig
from pathlab.scenarios import FAMILIES, generate, validate_scene
from pathlab.sdk import Action, Observation, TaskHint
from pathlab.simulation import (
    Camera,
    Renderer,
    Vehicle,
    vehicle_to_world,
    world_to_vehicle,
)


@pytest.mark.parametrize("yaw,pitch", [(0, 0.52), (0.3, 0.3), (-0.2, 0.8)])
def test_camera_round_trip(yaw, pitch):
    camera = Camera(CameraConfig(yaw_left_rad=yaw, pitch_down_rad=pitch))
    points = np.array([[0.7, 0], [1.5, -0.2], [3, 0.8], [5, -0.6]])
    pixels, front = camera.project(points)
    recovered, valid = camera.unproject(pixels)
    assert front.all() and valid.all()
    np.testing.assert_allclose(recovered, points, atol=1e-10)
    center, _ = Camera(CameraConfig()).project(np.array([[2, 0], [2, 0.2]]))
    assert center[1, 0] < center[0, 0]  # Vehicle left is image left.


def test_coordinate_transform():
    pose = Pose(x_m=1.2, y_m=-0.4, yaw_rad=0.7)
    points = np.array([[0, 0], [1, 2], [-3, 1]])
    np.testing.assert_allclose(
        world_to_vehicle(vehicle_to_world(points, pose), pose), points, atol=1e-12
    )


def test_stationary_vehicle_cannot_rotate():
    vehicle = Vehicle(VehicleConfig(), Pose(yaw_rad=0.2))
    for _ in range(100):
        vehicle.advance(Action(steering_angle_rad=0.5, speed_mps=0), 0.05)
    assert vehicle.state.yaw_rad == pytest.approx(0.2)
    assert vehicle.state.x_m == vehicle.state.y_m == 0


def test_motion_limits_and_signs():
    c = VehicleConfig()
    vehicle = Vehicle(c, Pose())
    applied = vehicle.advance(Action(steering_angle_rad=10, speed_mps=20), 0.05)
    assert "steering_saturated" in applied.interventions
    assert vehicle.state.speed_mps == pytest.approx(c.acceleration_mps2 * 0.05)
    assert vehicle.state.steering_angle_rad == pytest.approx(
        c.steering_rate_rad_s * 0.05
    )
    assert vehicle.state.yaw_rad > 0
    previous_speed = vehicle.state.speed_mps
    vehicle.advance(Action(steering_angle_rad=0, speed_mps=-3), 0.05)
    assert 0 <= vehicle.state.speed_mps <= previous_speed


def test_constant_curvature_is_bicycle_not_yaw_rate():
    vehicle = Vehicle(VehicleConfig(), Pose())
    vehicle.state.speed_mps = 0.8
    vehicle.state.steering_angle_rad = 0.3
    for _ in range(20):
        vehicle.advance(Action(steering_angle_rad=0.3, speed_mps=0.8), 0.05)
    radius = vehicle.config.wheelbase_m / math.tan(0.3)
    yaw = 0.8 / radius
    assert vehicle.state.yaw_rad == pytest.approx(yaw)
    assert vehicle.state.x_m == pytest.approx(radius * math.sin(yaw))
    assert vehicle.state.y_m == pytest.approx(radius * (1 - math.cos(yaw)))


@pytest.mark.parametrize("family", list(FAMILIES))
def test_scene_families_are_feasible_and_deterministic(family):
    for seed in range(6):
        scene = generate(family, seed)
        assert validate_scene(scene) == []
        assert scene.model_dump() == generate(family, seed).model_dump()


def test_renderer_depends_on_pose_and_seeded_noise():
    scene = generate("parallel", 7)
    renderer = Renderer(scene)
    image = renderer.render(scene.initial_pose, 0)
    assert np.array_equal(image, renderer.render(scene.initial_pose, 0))
    assert not np.array_equal(
        image, renderer.render(scene.initial_pose.model_copy(update={"x_m": -0.8}), 0)
    )
    assert image.shape == (360, 640, 3)
    green = (image[:, :, 1].astype(int) - image[:, :, 0] > 50) & (
        image[:, :, 1].astype(int) - image[:, :, 2] > 30
    )
    assert green.sum() > 100  # Start/direction marker is genuinely visible.


def test_scene_rejects_infeasible_core_and_missing_hint():
    scene = generate("straight")
    scene.target_path = [(0, 0), (0.04, 0), (0.04, 0.04)]
    assert any("曲率" in e for e in validate_scene(scene))
    scene = generate("straight")
    scene.task_hint = TaskHint(kind="none")
    assert any("提示" in e for e in validate_scene(scene))


def test_rgb_roundtrip_and_observation_shape():
    rgb = np.zeros((32, 48, 3), dtype=np.uint8)
    rgb[:, :24] = [255, 3, 17]
    obs = Observation.from_rgb(
        rgb,
        episode_id="test",
        frame_id=0,
        timestamp_s=0,
        dt_s=0.05,
        task_hint=TaskHint(),
    )
    np.testing.assert_array_equal(obs.rgb(), rgb)
    with pytest.raises(ValueError):
        Observation.from_rgb(rgb.astype(float), episode_id="test")
    obs.width = 47
    with pytest.raises(ValueError, match="尺寸"):
        obs.rgb()


def test_protocol_validation():
    from pathlab.sdk import AlgorithmOutput

    for data in [
        {},
        {"status": "TRACK", "confidence": float("nan")},
        {"status": "TRACK", "protocol_version": "0.9"},
        {"status": "TRACK", "action": {"speed_mps": 1}},
        {"status": "TRACK", "local_path_m": [[1, 2, 3], [3, 4, 5]]},
    ]:
        with pytest.raises(ValueError):
            AlgorithmOutput.model_validate(data)


def test_path_adapter_without_truth():
    from pathlab.adapters import PurePursuit, execution_action
    from pathlab.sdk import AlgorithmOutput

    adapter = PurePursuit(0.32, 1.5)
    output = AlgorithmOutput(
        status="TRACK", confidence=0.8, local_path_m=[(0.2, 0.1), (0.7, 0.3), (1, 0.5)]
    )
    action, events = execution_action(output, "path", adapter)
    assert action.steering_angle_rad > 0 and 0 < action.speed_mps < 1
    assert events == []
    with pytest.raises(ValueError, match="缺少"):
        execution_action(AlgorithmOutput(status="TRACK"), "action", adapter)


def test_output_and_parameters_are_bounded():
    from pathlab.config import RunConfig
    from pathlab.sdk import AlgorithmOutput

    with pytest.raises(ValueError, match="64 KiB"):
        AlgorithmOutput(status="TRACK", debug={"large": "x" * 70000})
    with pytest.raises(ValueError, match="16 KiB"):
        RunConfig(parameters={"large": "x" * 18000})
    with pytest.raises(ValueError):
        AlgorithmOutput(status="TRACK", debug={"invalid": float("inf")})


def test_marker_color_mismatch_is_not_hidden():
    scene = generate("straight")
    scene.appearance.marker_rgb = (250, 0, 250)
    assert any("颜色" in message for message in validate_scene(scene))


def test_camera_metadata_must_match_image():
    rgb = np.zeros((32, 48, 3), dtype=np.uint8)
    with pytest.raises(ValueError, match="标定分辨率"):
        Observation.from_rgb(
            rgb,
            episode_id="test",
            frame_id=0,
            timestamp_s=0,
            dt_s=0.05,
            task_hint=TaskHint(),
            calibration=Camera(CameraConfig()).calibration(),
        )
