"""Public-limit motion prediction and two replaceable local-path controllers."""

import math
import numpy as np

from pathlab.sdk import Action


class MotionEstimate:
    """Command-based short-term prediction, never simulator telemetry."""

    def __init__(self, limits):
        self.limits = limits
        self.speed = self.steering = 0.0

    def advance(self, action, duration, dt):
        c, x, y, yaw = self.limits, 0.0, 0.0, 0.0
        for _ in range(min(100, max(1, round(duration / dt)))):
            ds = float(
                np.clip(
                    action.steering_angle_rad - self.steering,
                    -c["steering_rate_rad_s"] * dt,
                    c["steering_rate_rad_s"] * dt,
                )
            )
            target = np.clip(action.speed_mps, 0, c["max_speed_mps"])
            limit = c["acceleration_mps2"] if target > self.speed else c["braking_mps2"]
            dv = float(np.clip(target - self.speed, -limit * dt, limit * dt))
            speed, steer = self.speed + dv / 2, self.steering + ds / 2
            angle = speed * math.tan(steer) / c["wheelbase_m"] * dt
            distance = speed * dt * np.sinc(angle / (2 * math.pi))
            x += distance * math.cos(yaw + angle / 2)
            y += distance * math.sin(yaw + angle / 2)
            yaw += angle
            self.speed += dv
            self.steering += ds
        return np.array([x, y]), yaw


class Pursuit:
    def __init__(self, limits, speed=0.85):
        self.limits, self.cruise = limits, speed

    def command(self, path, confidence, motion):
        distance = np.linalg.norm(path, axis=1)
        near = int(np.argmin(distance))
        path, distance = path[near:], distance[near:]
        lookahead = 0.57 + 0.12 * motion.speed
        indices = np.flatnonzero((distance >= lookahead) & (path[:, 0] > 0.05))
        target = path[indices[0] if len(indices) else -1]
        curvature = 2 * target[1] / max(float(target @ target), 0.04)
        steering = math.atan(self.limits["wheelbase_m"] * curvature)
        speed = min(
            self.cruise, self.limits["max_speed_mps"], 0.8 / max(1, abs(curvature))
        )
        speed *= float(np.clip(confidence / 0.85, 0.3, 1))
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
    """Deterministic sampled MPC with rate-limited steering and ordered references."""

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
        x, y, yaw = np.zeros((3, len(choices)))
        steer = np.full(len(choices), motion.steering)
        velocity = motion.speed
        cost = np.zeros(len(choices))
        for step in range(horizon):
            target = choices if step < 4 else later
            steer += np.clip(
                target - steer,
                -self.limits["steering_rate_rad_s"] * dt,
                self.limits["steering_rate_rad_s"] * dt,
            )
            velocity += np.clip(
                speed - velocity,
                -self.limits["braking_mps2"] * dt,
                self.limits["acceleration_mps2"] * dt,
            )
            yaw += velocity * np.tan(steer) / self.limits["wheelbase_m"] * dt
            x += velocity * np.cos(yaw) * dt
            y += velocity * np.sin(yaw) * dt
            cost += (x - references[step, 0]) ** 2 + 5 * (y - references[step, 1]) ** 2
        cost += 0.18 * (choices - motion.steering) ** 2 + 0.2 * (later - choices) ** 2
        return Action(
            steering_angle_rad=float(choices[np.argmin(cost)]), speed_mps=speed
        )
