"""Temporal scanlines with a curvature feed-forward and lateral-error PD control.

The shared visual front end supplies calibration and persistent target identity.
This baseline extracts its own path with short, rotating cross-sections and uses
an explicit PD controller; it does not use pursuit or predictive control.
"""

import math

import numpy as np

from pathlab.sdk import Action
from .modular.algorithm import VisualDriver
from .modular.vision import TargetTracker


def ordered_nearest(path):
    """Select the first distance basin, before a returning branch can win."""
    distance = np.linalg.norm(path, axis=1)
    departures = np.flatnonzero(distance > np.minimum.accumulate(distance) + 0.15)
    end = int(departures[0]) + 1 if len(departures) else len(path)
    return int(np.argmin(distance[:end]))


def scan_component(metric, index, direction):
    """Follow ordered normal cross-sections, including bends that turn backward.

    Horizontal image rows merge nearby roads and cannot order a hairpin. Small
    cross-sections in ground coordinates rotate with the last observed tangent.
    Each pass stays local to the identity-selected connected component.
    """

    def walk(heading):
        current = metric[index].copy()
        heading = heading / max(float(np.linalg.norm(heading)), 1e-8)
        path = [current]
        visited = np.linalg.norm(metric - current, axis=1) < 0.03
        for _ in range(160):
            delta = metric - current
            along = delta @ heading
            across = delta @ np.array([-heading[1], heading[0]])
            valid = (
                (~visited) & (along > 0.02) & (along < 0.115) & (np.abs(across) < 0.075)
            )
            if not valid.any():
                break
            cost = (along - 0.065) ** 2 + 1.5 * across**2
            selected = np.argmin(np.where(valid, cost, np.inf))
            section = (
                valid
                & (np.abs(along - along[selected]) < 0.015)
                & (np.abs(across - across[selected]) < 0.025)
            )
            following = metric[section].mean(axis=0)
            step = following - current
            distance = float(np.linalg.norm(step))
            if distance < 0.015:
                break
            heading = 0.35 * heading + 0.65 * step / distance
            heading /= max(float(np.linalg.norm(heading)), 1e-8)
            current = following
            path.append(current)
            visited |= np.linalg.norm(metric - current, axis=1) < 0.03
        return np.asarray(path)

    forward = walk(direction)
    backward = walk(-direction)
    return np.concatenate([backward[:0:-1], forward])


class ScanlineTracker(TargetTracker):
    nearest = staticmethod(ordered_nearest)

    def trace(self, pixels, metric, index, direction):
        return scan_component(metric, index, direction)


class ScanlinePD:
    def __init__(self, limits, speed=0.65):
        self.limits = limits
        self.speed = speed
        self.previous_error = None
        self.derivative = 0.0
        self.kp, self.kd = 0.85, 0.045
        self.lateral_error = 0.0
        self.dt = 0.05

    def command(self, path, confidence, motion):
        nearest = ordered_nearest(path)
        points = path[nearest:]
        arc = np.r_[0.0, np.cumsum(np.linalg.norm(np.diff(points, axis=0), axis=1))]
        response = 0.0
        if self.limits.get("motion_model") == "inertial_v2":
            response = self.limits.get("yaw_response_s", 0.18) + self.limits.get(
                "lateral_response_s", 0.12
            )
        # Measure an observed preview error. Extrapolating a distant polynomial
        # to the rear axle produces a false opposite turn at straight-to-bend
        # transitions, especially when the near road is outside the image.
        distance = np.linalg.norm(points, axis=1)
        preview = 0.65 + (0.12 + response) * motion.speed
        candidates = np.flatnonzero((distance >= preview) & (points[:, 0] > 0.05))
        target = points[candidates[0] if len(candidates) else -1]
        self.lateral_error = float(target[1])
        error = math.atan2(target[1], max(target[0], 0.15))
        derivative = (
            (error - self.previous_error) / max(self.dt, 1e-3)
            if self.previous_error is not None
            else 0.0
        )
        self.derivative = 0.8 * self.derivative + 0.2 * derivative
        self.previous_error = error
        curvature = 0.0
        if arc[-1] >= 0.5:
            sample = np.column_stack(
                [np.interp([0, 0.3, 0.6], arc, points[:, axis]) for axis in range(2)]
            )
            ab, bc, ac = (
                sample[1] - sample[0],
                sample[2] - sample[1],
                sample[2] - sample[0],
            )
            denominator = float(
                np.linalg.norm(ab) * np.linalg.norm(bc) * np.linalg.norm(ac)
            )
            curvature = float(
                np.clip(
                    2 * (ab[0] * bc[1] - ab[1] * bc[0]) / max(denominator, 1e-6), -2, 2
                )
            )
        # The road beyond the marker can lie farther than the requested preview.
        # Keep acquisition feedback active while that near ground is still unseen.
        feedback_scale = 2 * self.limits["wheelbase_m"] / max(preview, 0.35)
        steering = 0.15 * math.atan(
            self.limits["wheelbase_m"] * curvature
        ) + feedback_scale * (
            self.kp * error + (self.kd + 0.25 * response) * self.derivative
        )
        speed = min(
            self.speed, self.limits["max_speed_mps"], 0.68 / max(1.0, abs(curvature))
        )
        speed *= float(np.clip(confidence / 0.85, 0.35, 1.0))
        speed /= 1 + 0.8 * abs(error)
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


class ScanlinePID(VisualDriver):
    tracker_type = ScanlineTracker
    controller_type = ScanlinePD

    def initialize(self, config, public_context):
        super().initialize({"speed_mps": 0.65, **config}, public_context)

    def reset(self, initial_observation, task_hint):
        super().reset(initial_observation, task_hint)
        self.controller.kp = float(self.config.get("kp", 0.85))
        self.controller.kd = float(self.config.get("kd", 0.045))

    def step(self, observation):
        self.controller.dt = max(
            observation.dt_s, observation.timestamp_s - self.last_time
        )
        output = super().step(observation)
        if output.local_path_m is None:
            self.controller.previous_error = None
            self.controller.derivative = 0.0
        output.debug.update(
            extraction="adaptive_normal_scanlines",
            controller="curvature_feedforward_pd",
            lateral_error_m=self.controller.lateral_error,
            preview_error_rad=self.controller.previous_error,
        )
        return output
