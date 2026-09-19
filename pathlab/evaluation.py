"""Private, ordered-path scoring. It never supplies data to an algorithm."""

from __future__ import annotations

import math
import hashlib
import json

import numpy as np

from .config import Scene
from .simulation import VehicleState, wrap_angle

EVALUATOR_VERSION = "2.0"
SCORE_VERSION = "2.0"
SCORE_WEIGHTS = {
    "tracking": 35,
    "efficiency": 20,
    "smoothness": 15,
    "safety": 20,
    "realtime": 10,
}
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
        self.success_at_s: float | None = None
        self.collisions: list[dict] = []
        self.collision_duration_s = 0.0
        self.contacts: set[int] = set()
        self.last_evaluation: dict | None = None
        self.coasting = False
        self.previous_collision_pose = scene.initial_pose
        self.object_geometry = []
        if scene.render_version == "3":
            from .scene_objects import object_footprint

            self.object_geometry = [
                (
                    index,
                    polygon,
                    polygon.min(axis=0),
                    polygon.max(axis=0),
                    min(obj.length_m, obj.width_m),
                )
                for index, obj in enumerate(scene.objects)
                if obj.enabled and obj.collidable
                for polygon in [object_footprint(obj)]
            ]

    def begin_coasting(self):
        """Freeze task progress on every termination, including external timeouts."""
        self.coasting = True

    def update(self, state: VehicleState, timestamp: float) -> dict:
        p = np.array([state.x_m, state.y_m])
        travel = float(np.linalg.norm(p - self.previous))
        self.previous = p
        dt, t = self.scene.dt_s, THRESHOLDS
        collision_ids = self._collision_ids(state)
        for index in set(collision_ids) - self.contacts:
            self.collisions.append({"object_index": index, "timestamp_s": timestamp})
        self.contacts = set(collision_ids)
        if collision_ids:
            self.collision_duration_s += dt
            if self.done_reason in {None, "success"}:
                self.done_reason = "collision"
        if self.coasting or (
            self.last_evaluation is not None
            and self.last_evaluation["reason"] is not None
        ):
            # Terminal coasting still checks collision, but never advances route identity.
            if self.last_evaluation is None:
                _, error, tangent = self.path.project(p, 0, t["entry_arc_m"])
                self.last_evaluation = {
                    "phase": "acquisition",
                    "lateral_error_m": error,
                    "heading_error_rad": abs(wrap_angle(state.yaw_rad - tangent)),
                    "progress_m": 0.0,
                    "completion": 0.0,
                    "switch_count": 0,
                }
            self.last_evaluation = {
                **self.last_evaluation,
                "reason": self.done_reason,
                "collision_ids": collision_ids,
            }
            return self.last_evaluation.copy()
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
            if (
                self.switch_s >= t["switch_duration_s"]
                and not self.switched
                and self.done_reason is None
            ):
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
                self.success_at_s = timestamp
        self.last_evaluation = {
            "phase": "tracking" if self.acquired_at is not None else "acquisition",
            "lateral_error_m": error,
            "heading_error_rad": heading_error,
            "progress_m": self.progress,
            "completion": min(1.0, self.progress / self.path.total),
            "switch_count": len(self.switches),
            "reason": self.done_reason,
            "collision_ids": collision_ids,
        }
        return self.last_evaluation.copy()

    def _collision_ids(self, state: VehicleState) -> list[int]:
        before = self.previous_collision_pose
        self.previous_collision_pose = state.model_copy()
        if not self.object_geometry:
            return []
        vehicle = self.scene.vehicle
        half_length, half_width = vehicle.length_m / 2, vehicle.width_m / 2
        local = np.array(
            [
                [-half_length, -half_width],
                [half_length, -half_width],
                [half_length, half_width],
                [-half_length, half_width],
            ]
        )
        local[:, 0] += vehicle.wheelbase_m / 2
        start, end = (
            np.array([before.x_m, before.y_m]),
            np.array([state.x_m, state.y_m]),
        )
        radius = float(np.linalg.norm(local, axis=1).max())
        low, high = np.minimum(start, end) - radius, np.maximum(start, end) + radius
        candidates = [
            entry
            for entry in self.object_geometry
            if np.all(entry[3] >= low) and np.all(entry[2] <= high)
        ]
        if not candidates:
            return []
        yaw_delta = wrap_angle(state.yaw_rad - before.yaw_rad)
        # Bounded physical dimensions guarantee centimetre-scale sweep samples.
        spacing = min(
            0.04, vehicle.width_m / 2, *(entry[4] / 2 for entry in candidates)
        )
        steps = max(
            1,
            math.ceil(
                (np.linalg.norm(end - start) + abs(yaw_delta) * radius) / spacing
            ),
        )
        contacts = set()
        for fraction in np.linspace(0, 1, steps + 1):
            yaw = before.yaw_rad + fraction * yaw_delta
            c, s = math.cos(yaw), math.sin(yaw)
            footprint = (
                local @ np.array([[c, s], [-s, c]]) + start + fraction * (end - start)
            )
            body_low, body_high = footprint.min(axis=0), footprint.max(axis=0)
            for index, polygon, object_low, object_high, _ in candidates:
                if (
                    index not in contacts
                    and np.all(object_high >= body_low)
                    and np.all(object_low <= body_high)
                    and polygons_overlap(footprint, polygon)
                ):
                    contacts.add(index)
        return sorted(contacts)


def polygons_overlap(a: np.ndarray, b: np.ndarray) -> bool:
    """Separating-axis test for convex physical footprints, including edge contact."""
    for polygon in (a, b):
        edges = np.roll(polygon, -1, axis=0) - polygon
        for edge in edges:
            axis = np.array([-edge[1], edge[0]])
            if np.linalg.norm(axis) < 1e-10:
                continue
            pa, pb = a @ axis, b @ axis
            if pa.max() < pb.min() or pb.max() < pa.min():
                return False
    return True


def comparison_key(
    config: dict, scene: dict | None, physics_version: str
) -> str | None:
    if scene is None:
        return None
    settings = {
        k: config.get(k)
        for k in ("execution", "max_steps", "timeout_s", "stress", "task_hint")
    }
    payload = {
        "scene": scene,
        "settings": settings,
        "physics_version": physics_version,
        "evaluator_version": EVALUATOR_VERSION,
        "score_version": SCORE_VERSION,
    }
    return hashlib.sha256(
        json.dumps(
            payload, sort_keys=True, separators=(",", ":"), allow_nan=False
        ).encode()
    ).hexdigest()


def score_metrics(metrics: dict, scene: Scene | None) -> dict | None:
    """Versioned teaching rubric, separate from the unchanged success criterion."""
    if scene is None or not metrics["truth_metrics_available"]:
        return None
    completion = float(np.clip(metrics.get("completion") or 0, 0, 1))
    error = metrics["tracking_lateral_error_m"]["p95"]
    tracking = (
        max(0.0, 1 - error / THRESHOLDS["track_distance_m"])
        if error is not None
        else 0.0
    )
    elapsed = metrics.get("simulation_time_s") or 0
    progress = completion * OrderedPath(scene.target_path).total
    efficiency = (
        min(1.0, progress / (scene.vehicle.max_speed_mps * elapsed))
        if elapsed > 0
        else 0.0
    )
    rate = metrics.get("steering_rate_rad_s", {}).get("p95")
    smoothness = (
        max(0.0, 1 - rate / scene.vehicle.steering_rate_rad_s)
        if rate is not None
        else 0.0
    )
    frames = max(1, metrics.get("task_frames", metrics["frames"]))
    safety = max(0.0, 1 - metrics["safety_intervention_frames"] / frames)
    if metrics.get("collision_count") or metrics.get("illegal_switches"):
        safety = 0.0
    inference = metrics["inference_ms"]["p95"]
    realtime = (
        min(1.0, scene.dt_s * 1000 / max(inference, 1e-6))
        if inference is not None
        else None
    )
    components = {
        "tracking": tracking,
        "efficiency": efficiency,
        "smoothness": smoothness,
        "safety": safety,
        "realtime": realtime,
    }
    denominator = sum(
        SCORE_WEIGHTS[k] for k, value in components.items() if value is not None
    )
    quality = (
        sum(
            SCORE_WEIGHTS[k] * value
            for k, value in components.items()
            if value is not None
        )
        / denominator
    )
    total = (
        60 + 40 * quality
        if metrics["success"]
        else 49 * completion * (0.5 + 0.5 * quality)
    )
    return {
        "version": SCORE_VERSION,
        "total": round(total, 2),
        "quality": round(quality * 100, 2),
        "components": {
            k: {
                "value": round(value * 100, 2) if value is not None else None,
                "weight": SCORE_WEIGHTS[k],
            }
            for k, value in components.items()
        },
        "rule": "成功：60 + 40 × 质量；失败：49 × 完成度 × (0.5 + 0.5 × 质量)",
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
    task_records = [
        r for r in records if "safety_braking" not in r.get("interventions", [])
    ]
    scored = [r for r in task_records if r.get("evaluation") is not None]
    track = [r for r in scored if r["evaluation"]["phase"] == "tracking"]
    acquire = [r for r in scored if r["evaluation"]["phase"] == "acquisition"]
    elapsed = task_records[-1]["timestamp_s"] if task_records else 0
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
    speeds = [a["speed_mps"] for a in actual]
    steering = [a["steering_angle_rad"] for a in actual]
    dt = evaluator.scene.dt_s if evaluator else (records[0]["dt_s"] if records else 1)
    vector_acceleration = []
    for before, after in zip(records, records[1:]):
        poses = [before.get("pose") or {}, after.get("pose") or {}]
        if all(
            pose.get("velocity_x_mps") is not None
            and pose.get("velocity_y_mps") is not None
            for pose in poses
        ):
            velocities = np.array(
                [[pose["velocity_x_mps"], pose["velocity_y_mps"]] for pose in poses]
            )
            vector_acceleration.append(
                float(np.linalg.norm(velocities[1] - velocities[0]) / after["dt_s"])
            )
    metrics = {
        "evaluator_version": EVALUATOR_VERSION,
        "reason": reason,
        "frames": len(records),
        "task_frames": len(task_records),
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
        "completion_time_s": (evaluator.success_at_s or elapsed)
        if evaluator and reason == "success"
        else None,
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
        "collision_count": len(evaluator.collisions) if evaluator else None,
        "collisions": evaluator.collisions if evaluator else None,
        "collision_duration_s": evaluator.collision_duration_s if evaluator else None,
        "acceleration_mps2": distribution(list(np.abs(np.diff(speeds)) / dt)),
        "vector_acceleration_mps2": distribution(vector_acceleration),
        "jerk_mps3": distribution(list(np.abs(np.diff(speeds, n=2)) / dt**2)),
        "steering_rate_rad_s": distribution(list(np.abs(np.diff(steering)) / dt)),
        "realtime_miss_rate": sum(value > dt * 1000 for value in compute) / len(compute)
        if compute
        else None,
    }
    metrics["score"] = score_metrics(metrics, evaluator.scene if evaluator else None)
    return metrics
