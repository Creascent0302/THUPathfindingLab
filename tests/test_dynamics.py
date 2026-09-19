"""Physical invariants, public prediction parity, and environment migration."""

import math

import numpy as np
import pytest

from pathlab.config import Pose, Scene, VehicleConfig
from pathlab.dynamics import VX, VY, YAW, integrate_motion
from pathlab.scenarios import generate, validate_scene
from pathlab.sdk import Action
from pathlab.simulation import Vehicle


def drive(vehicle, steer, speed, steps):
    states = []
    for _ in range(steps):
        vehicle.advance(Action(steering_angle_rad=steer, speed_mps=speed), 0.05)
        states.append(vehicle.state.model_copy())
    return states


def test_inertia_brakes_over_distance_and_cannot_reverse():
    vehicle = Vehicle(VehicleConfig(), Pose())
    cruise = drive(vehicle, 0, 1, 100)[-1]
    braking = drive(vehicle, 0, 0, 80)
    assert 0 < braking[0].speed_mps < cruise.speed_mps
    assert braking[0].x_m > cruise.x_m
    assert braking[-1].x_m - cruise.x_m > 0.2
    assert braking[-1].speed_mps == 0
    assert all(s.speed_mps >= 0 for s in braking)
    assert braking[-1].x_m == braking[-2].x_m


def test_acceleration_and_jerk_are_bounded_before_rest_contact():
    c = VehicleConfig()
    states = drive(Vehicle(c, Pose()), 0.2, 1.2, 120)
    accelerations = np.array([s.acceleration_mps2 for s in states])
    assert accelerations.min() >= -c.braking_mps2
    assert accelerations.max() <= c.acceleration_mps2
    assert (
        np.max(abs(np.diff(np.r_[0, accelerations]))) <= c.jerk_limit_mps3 * 0.05 + 1e-9
    )


def test_turning_preserves_velocity_direction_and_bounds_lateral_acceleration():
    c = VehicleConfig(max_lateral_acceleration_mps2=0.5)
    vehicle = Vehicle(c, Pose())
    drive(vehicle, 0, 1, 100)
    states = drive(vehicle, 0.5, 1, 80)
    courses = np.unwrap(
        [math.atan2(s.velocity_y_mps, s.velocity_x_mps) for s in states]
    )
    assert states[10].yaw_rad > courses[10] > 0
    speeds = np.array([s.speed_mps for s in states])
    assert (
        np.max(abs(np.diff(courses)) * (speeds[1:] + speeds[:-1]) / 2 / 0.05)
        <= 0.5 + 1e-9
    )
    assert all(
        s.speed_mps == pytest.approx(math.hypot(s.velocity_x_mps, s.velocity_y_mps))
        for s in states
    )
    previous_rate = states[-1].yaw_rate_rad_s
    released = drive(vehicle, 0, 1, 1)[0]
    assert 0 < released.yaw_rate_rad_s < previous_rate + 0.02


@pytest.mark.parametrize("model", ["kinematic_v1", "inertial_v2"])
def test_batched_public_predictions_match_scalar_and_vehicle(model):
    c = VehicleConfig(motion_model=model)
    vehicle = Vehicle(c, Pose())
    batch = np.zeros((3, 8))
    for _ in range(60):
        batch = integrate_motion(
            batch, [-0.3, 0.3, 0], [0.7, 0.7, 0], c.model_dump(), 0.05
        )
        vehicle.advance(Action(steering_angle_rad=0.3, speed_mps=0.7), 0.05)
    np.testing.assert_allclose(
        batch[1, :3],
        [vehicle.state.x_m, vehicle.state.y_m, vehicle.state.yaw_rad],
        atol=1e-10,
    )
    np.testing.assert_allclose(batch[0, [0, VX]], batch[1, [0, VX]], atol=1e-10)
    np.testing.assert_allclose(
        batch[0, [1, YAW, VY]], -batch[1, [1, YAW, VY]], atol=1e-10
    )
    assert np.linalg.norm(batch[2]) == 0


def test_response_parameters_change_stopping_distance():
    distances = []
    for braking, jerk in [(0.8, 1), (2.5, 12)]:
        vehicle = Vehicle(
            VehicleConfig(braking_mps2=braking, jerk_limit_mps3=jerk), Pose()
        )
        start = drive(vehicle, 0, 1, 150)[-1].x_m
        distances.append(drive(vehicle, 0, 0, 150)[-1].x_m - start)
    assert distances[0] > distances[1] * 1.5


def test_negligible_brake_force_cannot_create_unbounded_stopping():
    with pytest.raises(ValueError):
        VehicleConfig(braking_mps2=1e-20)
    raw = generate("straight").model_dump()
    raw["render_version"] = "2"
    raw["vehicle"].pop("motion_model")
    raw["vehicle"]["braking_mps2"] = 0.01
    legacy = Scene.model_validate(raw)
    assert legacy.vehicle.braking_mps2 == 0.01
    assert any("制动" in error for error in validate_scene(legacy))


def test_old_scenes_keep_their_motion_model():
    raw = generate("straight").model_dump()
    assert raw["render_version"] == "3"
    assert raw["vehicle"]["motion_model"] == "inertial_v2"
    raw["render_version"] = "2"
    del raw["vehicle"]["motion_model"]
    assert Scene.model_validate(raw).vehicle.motion_model == "kinematic_v1"
    raw["vehicle"]["motion_model"] = "inertial_v2"
    assert Scene.model_validate(raw).vehicle.motion_model == "inertial_v2"
