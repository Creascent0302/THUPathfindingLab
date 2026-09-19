"""Public, deterministic actuator model for simulation and command-only prediction.

State columns are x, y, yaw, world velocity x/y, steering, yaw rate and
longitudinal acceleration. Inputs may be scalar or broadcast over candidate
trajectories. No scene, pose telemetry or evaluation data is accessed here.
The inertial model is a low-speed approximation, not a full tire-force solver.
"""

from collections.abc import Mapping

import numpy as np

X, Y, YAW, VX, VY, STEER, YAW_RATE, ACCEL = range(8)


def _angle(value):
    return (value + np.pi) % (2 * np.pi) - np.pi


def integrate_motion(state, steering, speed, limits: Mapping, dt: float):
    """Advance an independent copy by dt <= 0.1 s, with no reverse driving.

    Braking requests ramp acceleration under the jerk bound before reducing
    speed. Direction changes rotate the velocity vector under a lateral
    acceleration bound; body yaw follows its own first-order steering response.
    Zero-crossing is clamped at rest, so braking cannot create reverse motion.
    """
    if not 0 < dt <= 0.1:
        raise ValueError("物理步长必须在 (0, 0.1] s")
    old = np.asarray(state, dtype=float)
    if old.shape[-1] != 8:
        raise ValueError("运动状态最后一维必须为 8")
    result = old.copy()
    c = limits
    target_steer = np.clip(steering, -c["max_steering_rad"], c["max_steering_rad"])
    target_speed = np.clip(speed, 0, c["max_speed_mps"])
    v0 = np.hypot(old[..., VX], old[..., VY])
    delta = old[..., STEER] + np.clip(
        target_steer - old[..., STEER],
        -c["steering_rate_rad_s"] * dt,
        c["steering_rate_rad_s"] * dt,
    )
    result[..., STEER] = delta
    if c.get("motion_model", "kinematic_v1") == "kinematic_v1":
        v1 = v0 + np.clip(
            target_speed - v0, -c["braking_mps2"] * dt, c["acceleration_mps2"] * dt
        )
        vm = (v0 + v1) / 2
        dyaw = vm * np.tan((old[..., STEER] + delta) / 2) / c["wheelbase_m"] * dt
        distance = vm * dt * np.sinc(dyaw / (2 * np.pi))
        result[..., X] += distance * np.cos(old[..., YAW] + dyaw / 2)
        result[..., Y] += distance * np.sin(old[..., YAW] + dyaw / 2)
        result[..., YAW] = _angle(old[..., YAW] + dyaw)
        result[..., VX] = v1 * np.cos(result[..., YAW])
        result[..., VY] = v1 * np.sin(result[..., YAW])
        result[..., YAW_RATE] = v1 * np.tan(delta) / c["wheelbase_m"]
        result[..., ACCEL] = (v1 - v0) / dt
        return result

    desired_a = np.clip(
        (target_speed - v0) / c["speed_response_s"],
        -c["braking_mps2"],
        c["acceleration_mps2"],
    )
    # A stop command applies the brakes through to rest, rather than creeping
    # forever under a proportional speed regulator.
    desired_a = np.where(target_speed <= 0, -c["braking_mps2"], desired_a)
    acceleration = old[..., ACCEL] + np.clip(
        desired_a - old[..., ACCEL],
        -c["jerk_limit_mps3"] * dt,
        c["jerk_limit_mps3"] * dt,
    )
    v1 = np.clip(v0 + acceleration * dt, 0, c["max_speed_mps"])
    result[..., ACCEL] = np.where(
        (v1 == 0) | (v1 == c["max_speed_mps"]), 0, acceleration
    )
    vm = (v0 + v1) / 2
    rate_limit = c["max_lateral_acceleration_mps2"] / np.maximum(vm, 0.05)
    desired_rate = np.clip(
        vm * np.tan(delta) / c["wheelbase_m"], -rate_limit, rate_limit
    )
    rate = old[..., YAW_RATE] + (desired_rate - old[..., YAW_RATE]) * (
        -np.expm1(-dt / c["yaw_response_s"])
    )
    rate = np.where(v1 > 0, rate, 0)
    dyaw = (old[..., YAW_RATE] + rate) * dt / 2
    course = np.where(v0 > 1e-10, np.arctan2(old[..., VY], old[..., VX]), old[..., YAW])
    course_error = _angle(old[..., YAW] + dyaw / 2 - course)
    course_delta = course_error * (-np.expm1(-dt / c["lateral_response_s"]))
    course_delta = np.clip(course_delta, -rate_limit * dt, rate_limit * dt)
    result[..., VX] = v1 * np.cos(course + course_delta)
    result[..., VY] = v1 * np.sin(course + course_delta)
    result[..., X] += (old[..., VX] + result[..., VX]) * dt / 2
    result[..., Y] += (old[..., VY] + result[..., VY]) * dt / 2
    result[..., YAW] = _angle(old[..., YAW] + dyaw)
    result[..., YAW_RATE] = rate
    return result
