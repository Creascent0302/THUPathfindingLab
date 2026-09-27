"""Bounded reverse recovery using only command odometry and driven breadcrumbs.

There is no rear camera. Reversing is therefore restricted to a recent travelled
corridor, checked against remembered objects; it is not a general reverse planner.
"""

from copy import deepcopy
import math

import numpy as np

from pathlab.dynamics import integrate_motion
from pathlab.sdk import Action
from .obstacles import path_curvature, rotation


class ReverseRecovery:
    def __init__(self, limits):
        self.limits = limits
        self.history = np.array([[0.0, 0.0]])
        self.headings = np.zeros(1)
        self.path = None
        self.stage = "idle"
        self.reason = ""
        self.wait_s = self.age = 0.0
        self.attempts = []
        self.target_distance = 0.0
        self.completed = 0
        self.retry_plan = None
        self.view_recovery = False

    @property
    def active(self):
        return self.stage not in {"idle", "failed"}

    def advance(self, translation, yaw):
        self.history = (self.history - translation) @ rotation(yaw)
        self.headings -= yaw
        if self.retry_plan is not None:
            path, reference, peeking, continuing = self.retry_plan
            self.retry_plan = (
                (path - translation) @ rotation(yaw),
                (reference - translation) @ rotation(yaw),
                peeking,
                continuing,
            )
        for attempt in self.attempts:
            attempt[0] = (attempt[0] - translation) @ rotation(yaw)
        if self.path is not None:
            self.path = (self.path - translation) @ rotation(yaw)
            near = int(np.argmin(np.linalg.norm(self.path, axis=1)))
            self.path = self.path[max(0, near - 1) :]
        if not self.active and np.linalg.norm(self.history[-1]) > 0.025:
            self.history = np.vstack([self.history, [0, 0]])
            self.headings = np.r_[self.headings, 0]
            arc = np.r_[
                0, np.cumsum(np.linalg.norm(np.diff(self.history, axis=0), axis=1))
            ]
            keep = arc > arc[-1] - 4.0
            self.history, self.headings = self.history[keep], self.headings[keep]

    def request(self, tracker, motion, dt):
        self.wait_s += dt
        if (
            not self.limits.get("reverse_allowed")
            or not tracker.initialized
            or self.wait_s < 0.25
            or tracker.planner.blocking is None
        ):
            return
        center = tracker.planner.blocking.center
        if center[0] < -0.3:
            reference = tracker.planner.reference
            if reference is None:
                reference = tracker.planner.last_route
            ahead = (
                tracker.planner.blockers(reference, tracker.obstacles.items)
                if reference is not None and len(reference) >= 4
                else []
            )
            if not ahead:
                return
            tracker.planner.blocking = min(ahead, key=lambda item: item.center[0])
            center = tracker.planner.blocking.center
        match = next(
            (a for a in self.attempts if np.linalg.norm(a[0] - center) < 0.8), None
        )
        if match is not None and match[1] >= 2:
            self.stage, self.reason = (
                "failed",
                "同一占道物件的倒车重试预算已耗尽，制动保留路线身份",
            )
            return
        if self.stage == "failed":
            return
        self.stage, self.age = "brake_before", 0
        self.reason = "前方绕行空间不足，先制动停稳再检查倒车恢复位置"

    def _safe_corridor(self, path, obstacles):
        # Breadcrumbs certify previous traversal, not persistent clearance. Every
        # retry checks newly seen obstacles too. Keep the rear-axle reference used
        # by forward planning, with an extra margin for tracking error.
        clearance = self.limits.get("width_m", 0.28) / 2 + 0.10
        return len(path) >= 3 and all(
            np.linalg.norm(path - item.center, axis=1).min() > item.radius + clearance
            for item in obstacles
        )

    def _choose_retreat(self, tracker):
        planner, obstacles = tracker.planner, tracker.obstacles.items
        history = np.vstack([self.history, [0, 0]])[::-1]
        headings = np.r_[self.headings, 0][::-1]
        arc = np.r_[0, np.cumsum(np.linalg.norm(np.diff(history, axis=0), axis=1))]
        route = planner.reference if planner.reference is not None else tracker.path
        if route is None:
            return None
        self.retry_plan = None
        self.view_recovery = False
        fallback = None
        for distance in (0.45, 0.75, 1.05, 1.35, 1.6):
            if arc[-1] < distance + 0.08:
                continue
            index = int(np.searchsorted(arc, distance))
            corridor = history[: index + 1]
            if not self._safe_corridor(corridor, obstacles):
                continue
            translation, yaw = history[index], headings[index]
            trial, objects = deepcopy((planner, obstacles))
            trial.advance(translation, yaw)
            for item in objects:
                item.center = (item.center - translation) @ rotation(yaw)
            trial.path = None
            trial.peeking = trial.peek_attempted = False
            trial.age = 0
            trial.recovery_pending = True
            predicted_route = (route - translation) @ rotation(yaw)
            components = [
                (pixels, (metric - translation) @ rotation(yaw))
                for pixels, metric in tracker.components
            ]
            candidate, active = trial.command_path(
                predicted_route, components, objects, 0.05
            )
            if active and candidate is not None:
                self.target_distance = float(arc[index])
                self.retry_plan = (
                    candidate @ rotation(yaw).T + translation,
                    trial.reference @ rotation(yaw).T + translation,
                    trial.peeking,
                    trial.continuing,
                )
                return corridor.copy()
            # A front camera cannot reveal newly exposed ground from a virtual
            # pose. If no observed forward plan is available, a bounded retreat
            # may instead restore sight, provided there is sufficient approach
            # room for a two-arc lateral shift at the public turning radius.
            radius = 1 / planner.max_curvature
            offset = min(
                0.8, trial.blocking.radius + self.limits.get("width_m", 0.28) / 2 + 0.12
            )
            approach = math.sqrt(max(0, 4 * radius * offset - offset**2))
            approach += (
                trial.blocking.radius + self.limits.get("length_m", 0.46) / 2 + 0.18
            )
            center = trial.blocking.center
            if (
                fallback is None
                and center[0] >= approach
                and abs(math.atan2(center[1], center[0])) < 0.6
            ):
                fallback = float(arc[index]), corridor.copy()
        if fallback is not None:
            self.target_distance, path = fallback
            self.view_recovery = True
            return path
        return None

    def _resume_plan(self, tracker):
        """Recheck the chosen forward maneuver against observations at rest.

        The final pose is slightly different from a breadcrumb pose because of
        tracking and braking. Reuse geometry only inside a small pose tolerance;
        changed occupancy or neighbor evidence always vetoes it.
        """
        if self.retry_plan is None:
            return False
        path, reference, peeking, continuing = self.retry_plan
        tangent = path[min(3, len(path) - 1)] - path[0]
        if (
            np.linalg.norm(path[0]) > 0.10
            or abs(math.atan2(tangent[1], tangent[0])) > 0.16
        ):
            return False
        planner = tracker.planner
        clearance = self.limits.get("width_m", 0.28) / 2 + 0.12
        if path_curvature(path).max(initial=0) > planner.max_curvature or any(
            np.linalg.norm(path - item.center, axis=1).min() < item.radius + clearance
            for item in tracker.obstacles.items
        ):
            return False
        cloud = planner.other_roads(reference)
        displacement = np.linalg.norm(path[:, None] - reference[None], axis=2).min(
            axis=1
        )
        if not peeking and displacement.max() > planner.corridor_limit(
            reference, planner.blocking
        ):
            return False
        required = (
            np.minimum(0.28, np.linalg.norm(path - path[0], axis=1) * 0.2 + 0.1)
            if peeking
            else np.minimum(0.32, displacement + 0.08)
        )
        if (
            peeking
            and len(cloud)
            and np.any(
                np.linalg.norm(path[:, None] - cloud[None], axis=2).min(axis=1)
                < required
            )
        ):
            return False
        if not peeking and not planner.neighbor_clearance(path, displacement, cloud):
            return False
        planner.path, planner.reference = path.copy(), reference.copy()
        planner.peeking = planner.peek_attempted = peeking
        planner.continuing = continuing
        planner.recovery_pending = False
        planner.rejoin_observed = False
        planner.reason = "倒车停稳后已用当前观测复核绕行路径，继续保持原路线身份"
        return True

    def command(self, tracker, motion, dt):
        self.age += dt
        stop = Action(steering_angle_rad=motion.steering, speed_mps=0)
        if self.age > 18:
            self.stage, self.reason = "failed", "倒车恢复超时，制动保留路线身份"
            return stop
        if self.stage == "brake_before":
            if motion.speed > 1e-6:
                return stop
            self.path = self._choose_retreat(tracker)
            if self.path is None:
                self.stage, self.reason = (
                    "failed",
                    "已驶过走廊内没有同时满足倒车净距与前进绕行约束的位置，保持停车",
                )
                return stop
            center = tracker.planner.blocking.center
            match = next(
                (a for a in self.attempts if np.linalg.norm(a[0] - center) < 0.8), None
            )
            if match is None:
                self.attempts.append([center.copy(), 1])
            else:
                match[1] += 1
            self.stage = "retreat"
            self.reason = (
                f"沿已驶过走廊倒车约 {self.target_distance:.2f} m，保留原路线身份"
            )
        if self.stage == "retreat":
            if (
                not self._safe_corridor(self.path, tracker.obstacles.items)
                or np.linalg.norm(self.path, axis=1).min() > 0.12
            ):
                self.stage, self.reason = "failed", "倒车走廊净距不足，立即制动"
                return stop
            near = int(np.argmin(np.linalg.norm(self.path, axis=1)))
            remaining = float(
                np.linalg.norm(np.diff(self.path[near:], axis=0), axis=1).sum()
            )
            # Predict the complete braking trajectory with acceleration memory.
            predicted, braking_distance = motion.state.copy(), 0.0
            for _ in range(120):
                if np.linalg.norm(predicted[3:5]) < 1e-6:
                    break
                after = integrate_motion(
                    predicted, motion.steering, 0, self.limits, 0.05
                )
                braking_distance += float(np.linalg.norm(after[:2] - predicted[:2]))
                predicted = after
            if remaining <= braking_distance + 0.005:
                self.stage, self.reason = (
                    "brake_after",
                    "已到倒车制动点，停稳后重新规划前进绕行",
                )
                return stop
            ahead = self.path[near:]
            distance = np.linalg.norm(ahead, axis=1)
            choices = np.flatnonzero(distance >= 0.38)
            target = ahead[choices[0] if len(choices) else -1]
            curvature = 2 * target[1] / max(float(target @ target), 0.04)
            steer = math.atan(self.limits["wheelbase_m"] * curvature)
            return Action(
                steering_angle_rad=float(
                    np.clip(
                        steer,
                        -self.limits["max_steering_rad"],
                        self.limits["max_steering_rad"],
                    )
                ),
                speed_mps=-min(0.28, self.limits.get("max_reverse_speed_mps", 0.5)),
            )
        if self.stage == "brake_after" and motion.speed < 1e-6:
            planner = tracker.planner
            planner.path = None
            planner.age = 0
            planner.peeking = planner.peek_attempted = False
            planner.recovery_pending = True
            self._resume_plan(tracker)
            self.retry_plan = None
            self.stage, self.wait_s = "idle", 0
            self.completed += 1
            self.reason = "倒车已停稳，保留原路线并重新规划前进绕行"
            # Remove the forward part just retraced; it must not become a future
            # reverse shortcut across a loop in the breadcrumb history.
            near = int(np.argmin(np.linalg.norm(self.history, axis=1)))
            self.history, self.headings = (
                self.history[: near + 1],
                self.headings[: near + 1],
            )
            self.path = None
        return stop
