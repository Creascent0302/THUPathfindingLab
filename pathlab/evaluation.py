"""Private, ordered-path scoring. It never supplies data to an algorithm."""

from __future__ import annotations

import math

import numpy as np

from .config import Scene
from .simulation import VehicleState, wrap_angle

EVALUATOR_VERSION = "1.0"
THRESHOLDS = {
    "acquire_distance_m": 0.20,
    "acquire_heading_rad": 0.45,
    "entry_arc_m": 0.5,
    "track_distance_m": 0.24,
    "track_heading_rad": 0.65,
    "offtrack_timeout_s": 2.0,
    "switch_distance_m": 0.14,
    "switch_margin_m": 0.035,
    "switch_duration_s": 0.5,
    "finish_remaining_m": 0.18,
}


class OrderedPath:
    def __init__(self, points):
        self.points = np.asarray(points, dtype=float)
        self.vectors = np.diff(self.points, axis=0)
        self.lengths = np.linalg.norm(self.vectors, axis=1)
        self.arc = np.r_[0, np.cumsum(self.lengths)]
        self.total = float(self.arc[-1])

    def project(
        self, point, low: float = 0, high: float | None = None
    ) -> tuple[float, float, float]:
        high = self.total if high is None else min(self.total, high)
        low = max(0, min(low, high))
        indices = np.flatnonzero((self.arc[:-1] <= high) & (self.arc[1:] >= low))
        vectors, lengths = self.vectors[indices], self.lengths[indices]
        t = np.sum(
            (np.asarray(point) - self.points[indices]) * vectors, axis=1
        ) / np.maximum(lengths**2, 1e-12)
        t = np.clip(
            t,
            np.clip((low - self.arc[indices]) / lengths, 0, 1),
            np.clip((high - self.arc[indices]) / lengths, 0, 1),
        )
        projections = self.points[indices] + vectors * t[:, None]
        distances = np.linalg.norm(projections - point, axis=1)
        local = int(np.argmin(distances))
        index = indices[local]
        arc = self.arc[index] + t[local] * self.lengths[index]
        heading = math.atan2(self.vectors[index, 1], self.vectors[index, 0])
        return float(arc), float(distances[local]), heading


class Evaluator:
    def __init__(self, scene: Scene):
        self.scene = scene
        self.path = OrderedPath(scene.target_path)
        self.distractors = [OrderedPath(line) for line in scene.distractors]
        self.previous = np.array([scene.initial_pose.x_m, scene.initial_pose.y_m])
        self.progress = 0.0
        self.acquired_at = None
        self.offtrack_s = 0.0
        self.switch_s = 0.0
        self.switched = False
        self.switches = []
        self.done_reason = None

    def update(self, state: VehicleState, timestamp: float) -> dict:
        p = np.array([state.x_m, state.y_m])
        travel = float(np.linalg.norm(p - self.previous))
        self.previous = p
        dt, t = self.scene.dt_s, THRESHOLDS
        if travel > self.scene.vehicle.max_speed_mps * dt * 1.05 + 0.001:
            self.done_reason = "invalid_motion"
        upper = (
            t["entry_arc_m"]
            if self.acquired_at is None
            else self.progress + travel * 1.5 + 0.025
        )
        arc, error, tangent = self.path.project(p, max(0, self.progress - 0.35), upper)
        heading_error = abs(wrap_angle(state.yaw_rad - tangent))
        if (
            self.acquired_at is None
            and error <= t["acquire_distance_m"]
            and heading_error <= t["acquire_heading_rad"]
            and self.done_reason is None
        ):
            self.acquired_at = timestamp
            self.progress = arc
        ontrack = (
            error <= t["track_distance_m"] and heading_error <= t["track_heading_rad"]
        )
        if self.acquired_at is not None:
            if ontrack and self.done_reason is None:
                self.progress = max(self.progress, arc)
                self.offtrack_s = 0
            else:
                self.offtrack_s += dt
            global_target_error = self.path.project(p)[1]
            other_error = min(
                (line.project(p)[1] for line in self.distractors), default=math.inf
            )
            wrong_line = (
                other_error < t["switch_distance_m"]
                and other_error + t["switch_margin_m"] < global_target_error
            )
            self.switch_s = self.switch_s + dt if wrong_line else 0
            if self.switch_s >= t["switch_duration_s"] and not self.switched:
                self.switches.append(
                    {
                        "timestamp_s": timestamp,
                        "x_m": state.x_m,
                        "y_m": state.y_m,
                        "progress_m": self.progress,
                    }
                )
                self.switched = True
                self.done_reason = "illegal_switch"
            if self.offtrack_s >= t["offtrack_timeout_s"] and self.done_reason is None:
                self.done_reason = "deviation"
            if (
                ontrack
                and self.progress >= self.path.total - t["finish_remaining_m"]
                and self.done_reason is None
            ):
                self.done_reason = "success"
        return {
            "phase": "tracking" if self.acquired_at is not None else "acquisition",
            "lateral_error_m": error,
            "heading_error_rad": heading_error,
            "progress_m": self.progress,
            "completion": min(1.0, self.progress / self.path.total),
            "switch_count": len(self.switches),
            "reason": self.done_reason,
        }


def distribution(values: list[float]) -> dict:
    if not values:
        return {"mean": None, "p95": None, "max": None}
    return {
        "mean": float(np.mean(values)),
        "p95": float(np.percentile(values, 95)),
        "max": float(np.max(values)),
    }


def summarize(
    records: list[dict],
    evaluator: Evaluator | None,
    reason: str | None,
    failures: list[dict],
) -> dict:
    scored = [r for r in records if r.get("evaluation") is not None]
    track = [r for r in scored if r["evaluation"]["phase"] == "tracking"]
    acquire = [r for r in scored if r["evaluation"]["phase"] == "acquisition"]
    elapsed = records[-1]["timestamp_s"] if records else 0
    lost_count, recovered, lost_seconds, in_loss = 0, 0, 0.0, False
    for row in records:
        status = (row.get("output") or {}).get("status")
        if status == "LOST":
            if not in_loss:
                lost_count += 1
            in_loss = True
            lost_seconds += row["dt_s"]
        elif status == "TRACK" and in_loss:
            recovered += 1
            in_loss = False
    actual = [r["applied"]["actual"] for r in records if r.get("applied")]
    compute = [r["inference_ms"] for r in records if r.get("inference_ms") is not None]
    timeout_count = sum(f["kind"] == "timeout" for f in failures)
    interventions = [r.get("interventions", []) for r in records]
    return {
        "evaluator_version": EVALUATOR_VERSION,
        "reason": reason,
        "frames": len(records),
        "success": reason == "success" if evaluator else None,
        "acquisition_success": evaluator.acquired_at is not None if evaluator else None,
        "acquisition_time_s": evaluator.acquired_at if evaluator else None,
        "completion": evaluator.progress / evaluator.path.total if evaluator else None,
        "tracking_lateral_error_m": distribution(
            [r["evaluation"]["lateral_error_m"] for r in track]
        ),
        "acquisition_lateral_error_m": distribution(
            [r["evaluation"]["lateral_error_m"] for r in acquire]
        ),
        "heading_error_rad": distribution(
            [r["evaluation"]["heading_error_rad"] for r in track]
        ),
        "illegal_switches": evaluator.switches if evaluator else None,
        "lost_count": lost_count,
        "lost_duration_s": lost_seconds,
        "recovery_rate": recovered / lost_count if lost_count else None,
        "inference_ms": distribution(compute),
        "timeout_count": timeout_count,
        "timeout_rate": timeout_count / max(len(compute) + timeout_count, 1),
        "speed_mps": distribution([a["speed_mps"] for a in actual]),
        "simulation_time_s": elapsed if evaluator else None,
        "completion_time_s": elapsed if evaluator and reason == "success" else None,
        "action_saturation_frames": sum(
            any(e in {"steering_saturated", "speed_saturated"} for e in row)
            for row in interventions
        ),
        "steering_total_variation_rad": float(
            np.abs(np.diff([a["steering_angle_rad"] for a in actual])).sum()
        )
        if actual
        else None,
        "safety_intervention_frames": sum(
            any(
                e.startswith("status_stop")
                or e in {"action_expired", "algorithm_failure", "manual_deadman"}
                for e in row
            )
            for row in interventions
        ),
        "failure_counts": {
            kind: sum(f["kind"] == kind for f in failures)
            for kind in ["timeout", "crash", "protocol", "invalid_output", "exception"]
        },
        "truth_metrics_available": evaluator is not None,
    }
