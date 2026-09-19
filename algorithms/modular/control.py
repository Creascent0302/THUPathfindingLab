"""Public-limit motion prediction and two replaceable local-path controllers."""

import math
import numpy as np

from pathlab.sdk import Action
from pathlab.dynamics import integrate_motion


class MotionEstimate:
    """Command-based short-term prediction, never simulator telemetry."""

    def __init__(self, limits):
        self.limits = limits
        self.state = np.zeros(8, dtype=float)

    @property
    def speed(self):
        return float(np.linalg.norm(self.state[3:5]))

    @property
    def steering(self):
        return float(self.state[5])

    def advance(self, action, duration, dt):
        # Integrate the commands we actually issued. No simulator pose, velocity,
        # or route information is available to this estimate.
        remaining = max(0.0, float(duration))
        while remaining > 1e-9:
            step = min(float(dt), remaining, 0.1)
            self.state = integrate_motion(
                self.state,
                action.steering_angle_rad,
                action.speed_mps,
                self.limits,
                step,
            )
            remaining -= step
        translation, yaw = self.state[:2].copy(), float(self.state[2])
        cosine, sine = math.cos(yaw), math.sin(yaw)
        vx, vy = self.state[3:5]
        # The next observation uses the new vehicle frame. Preserve lateral
        # momentum when changing frame; resetting vy would erase tire dynamics.
        self.state[3:5] = cosine * vx + sine * vy, -sine * vx + cosine * vy
        self.state[:3] = 0
        return translation, yaw


class Pursuit:
    def __init__(self, limits, speed=0.85):
        self.limits, self.cruise = limits, speed

    def command(self, path, confidence, motion):
        distance = np.linalg.norm(path, axis=1)
        near = int(np.argmin(distance))
        path, distance = path[near:], distance[near:]
        response = (
            self.limits.get("yaw_response_s", 0.12)
            + self.limits.get("lateral_response_s", 0.10)
            if self.limits.get("motion_model") == "inertial_v2"
            else 0
        )
        lookahead = 0.57 + (0.12 + response) * motion.speed
        indices = np.flatnonzero((distance >= lookahead) & (path[:, 0] > 0.05))
        target = path[indices[0] if len(indices) else -1]
        curvature = 2 * target[1] / max(float(target @ target), 0.04)
        steering = math.atan(self.limits["wheelbase_m"] * curvature)
        speed = min(
            self.cruise, self.limits["max_speed_mps"], 0.8 / max(1, abs(curvature))
        )
        if response:
            speed = min(
                speed,
                math.sqrt(
                    0.75
                    * self.limits.get("max_lateral_acceleration_mps2", 3.0)
                    / max(abs(curvature), 0.05)
                ),
            )
        speed *= float(np.clip(confidence / 0.85, 0.3, 1))
        # Account for braking latency before entering a tighter visible bend.
        future = path[(distance > lookahead) & (distance < lookahead + 0.7)]
        if response and len(future) > 2:
            future_curvature = np.abs(
                2 * future[:, 1] / np.maximum(np.sum(future * future, axis=1), 0.04)
            )
            bend_speed = 0.8 / max(1, float(np.max(future_curvature)))
            braking_distance = max(0.05, lookahead - motion.speed * response)
            speed = min(
                speed,
                math.sqrt(
                    bend_speed**2 + 2 * self.limits["braking_mps2"] * braking_distance
                ),
            )
        if target[0] < 0.08:
            speed = min(speed, 0.2)
        return Action(
            steering_angle_rad=float(
                np.clip(
                    steering,
                    -self.limits["max_steering_rad"],
                    self.limits["max_steering_rad"],
                )
            ),
            speed_mps=speed,
        )


class Predictive(Pursuit):
    """Sampled MPC with vector inertia, actuator limits and ordered references."""

    def command(self, path, confidence, motion):
        initial = super().command(path, confidence, motion)
        horizon, dt = 12, 0.10
        speed = initial.speed_mps
        closest = int(np.argmin(np.linalg.norm(path, axis=1)))
        target_path = path[closest:]
        if len(target_path) < 3:
            return initial
        arc = np.r_[0, np.cumsum(np.linalg.norm(np.diff(target_path, axis=0), axis=1))]
        distances = np.maximum(
            0,
            np.arange(1, horizon + 1) * max(speed, 0.25) * dt
            - np.linalg.norm(target_path[0]),
        )
        references = np.column_stack(
            [np.interp(distances, arc, target_path[:, axis]) for axis in range(2)]
        )
        first, second = np.meshgrid(
            np.linspace(-0.12, 0.12, 9), np.linspace(-0.10, 0.10, 7)
        )
        choices = np.clip(
            initial.steering_angle_rad + first.ravel(),
            -self.limits["max_steering_rad"],
            self.limits["max_steering_rad"],
        )
        later = np.clip(
            choices + second.ravel(),
            -self.limits["max_steering_rad"],
            self.limits["max_steering_rad"],
        )
        state = np.broadcast_to(motion.state, (len(choices), 8)).copy()
        cost = np.zeros(len(choices))
        for step in range(horizon):
            target = choices if step < 4 else later
            # Match the simulation's 20 Hz integration within each 10 Hz
            # prediction node, including steering rate and acceleration memory.
            for _ in range(2):
                state = integrate_motion(state, target, speed, self.limits, dt / 2)
            cost += (state[:, 0] - references[step, 0]) ** 2 + 5 * (
                state[:, 1] - references[step, 1]
            ) ** 2
        cost += 0.18 * (choices - motion.steering) ** 2 + 0.2 * (later - choices) ** 2
        return Action(
            steering_angle_rad=float(choices[np.argmin(cost)]), speed_mps=speed
        )
