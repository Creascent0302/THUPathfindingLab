"""Replaceable execution adapter: no map or simulator imports."""

from __future__ import annotations

import math

import numpy as np

from .sdk import Action, AlgorithmOutput


class PurePursuit:
    def __init__(
        self, wheelbase_m: float, max_speed_mps: float, lookahead_m: float = 0.65
    ):
        self.wheelbase = wheelbase_m
        self.max_speed = max_speed_mps
        self.lookahead = lookahead_m

    def action(self, output: AlgorithmOutput) -> Action:
        if output.local_path_m is None:
            raise ValueError("path 模式缺少 local_path_m")
        path = np.asarray(output.local_path_m)
        if np.any(np.linalg.norm(path, axis=1) > 30):
            raise ValueError("局部路径超出 30 m 范围")
        # Follow ordering; never search for a distant returning branch.
        distances = np.linalg.norm(path, axis=1)
        candidates = np.flatnonzero((path[:, 0] > 0) & (distances >= self.lookahead))
        forward = np.flatnonzero(path[:, 0] > 0.05)
        if not len(forward):
            return Action(steering_angle_rad=0, speed_mps=0)
        point = path[candidates[0] if len(candidates) else forward[-1]]
        curvature = 2 * point[1] / max(float(point @ point), 0.01)
        confidence = output.confidence if output.confidence is not None else 0.35
        speed = min(self.max_speed, 0.8) * confidence / (1 + abs(curvature))
        return Action(
            steering_angle_rad=math.atan(self.wheelbase * curvature), speed_mps=speed
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
