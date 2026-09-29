"""Replaceable execution adapter: no map or simulator imports."""

from __future__ import annotations

import math

import numpy as np

from .sdk import Action, AlgorithmOutput


class PurePursuit:
    """Follow the first forward part of an ordered polyline, without route truth.

    The lookahead intersects line segments, so inserting collinear samples does
    not change the command. A returning branch behind the car ends the local
    prefix: it must never become a new target merely because it re-enters view.
    """

    def __init__(
        self,
        wheelbase_m: float,
        max_speed_mps: float,
        lookahead_m: float = 0.57,
        *,
        max_steering_rad: float = 0.52,
    ):
        self.wheelbase = wheelbase_m
        self.max_speed = max_speed_mps
        self.lookahead = lookahead_m
        self.max_steering = max_steering_rad

    def target(self, path: np.ndarray) -> np.ndarray | None:
        forward = np.flatnonzero(path[:, 0] > 0.05)
        if not len(forward):
            return None
        start = int(forward[0])
        tail = path[start:]
        behind = np.flatnonzero(tail[:, 0] <= 0.05)
        if len(behind):
            tail = tail[: behind[0]]
        # Retain a segment crossing from behind to ahead of the rear axle.
        if start and path[start - 1, 0] <= 0.05:
            tail = np.vstack((path[start - 1], tail))
        radius2 = self.lookahead**2
        if tail[0, 0] > 0.05 and tail[0] @ tail[0] >= radius2:
            return tail[0]
        for first, second in zip(tail[:-1], tail[1:]):
            delta = second - first
            a = float(delta @ delta)
            if a < 1e-12:
                continue
            b = 2 * float(first @ delta)
            c = float(first @ first) - radius2
            discriminant = b * b - 4 * a * c
            if discriminant < 0:
                continue
            # Exit from the lookahead circle, not its entry behind the axle.
            t = (-b + math.sqrt(discriminant)) / (2 * a)
            if 0 <= t <= 1:
                point = first + t * delta
                if point[0] > 0.05:
                    return point
        return tail[-1]

    def action(self, output: AlgorithmOutput) -> Action:
        if output.local_path_m is None:
            raise ValueError("path 模式缺少 local_path_m")
        path = np.asarray(output.local_path_m, dtype=float)
        if np.any(np.linalg.norm(path, axis=1) > 30):
            raise ValueError("局部路径超出 30 m 范围")
        point = self.target(path)
        if point is None:
            return Action(steering_angle_rad=0, speed_mps=0)
        curvature = 2 * point[1] / max(float(point @ point), 0.01)
        confidence = output.confidence if output.confidence is not None else 0.35
        # Curves slow down before the inertial model reaches the steering bound.
        speed = min(self.max_speed, 0.8) * confidence / max(1, 1.5 * abs(curvature))
        return Action(
            steering_angle_rad=float(
                np.clip(
                    math.atan(self.wheelbase * curvature),
                    -self.max_steering,
                    self.max_steering,
                )
            ),
            speed_mps=speed,
        )


def execution_action(
    output: AlgorithmOutput, mode: str, adapter: PurePursuit
) -> tuple[Action, list[str]]:
    if output.status in {"UNINITIALIZED", "LOST", "AMBIGUOUS", "FINISHED", "ERROR"}:
        return Action(steering_angle_rad=0, speed_mps=0), [
            f"status_stop:{output.status}"
        ]
    if mode == "perception":
        return Action(steering_angle_rad=0, speed_mps=0), ["perception_only"]
    if mode == "path":
        return adapter.action(output), []
    if output.action is None:
        raise ValueError("action 模式缺少 action；缺失值不会转换为零")
    return output.action, []
