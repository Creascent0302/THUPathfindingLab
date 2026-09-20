"""Monocular obstacle footprints and identity-preserving local detours.

Only RGB, calibration and command-based ego motion enter this module. No scene
objects, simulator pose, route truth or evaluation feedback are available.
"""

from dataclasses import dataclass
from itertools import product
import math

import cv2
import numpy as np

from .vision import (
    BirdEye,
    TargetTracker,
    principal_direction,
    trace_component,
    transform_points,
)


@dataclass
class Obstacle:
    center: np.ndarray
    radius: float
    age: float = 0


def rotation(yaw):
    return np.array([[math.cos(yaw), -math.sin(yaw)], [math.sin(yaw), math.cos(yaw)]])


def smooth_path(points, sigma=3):
    """Suppress pixel staircases before computing normals, without endpoint kinks."""
    count = math.ceil(3 * sigma)
    kernel = np.exp(-0.5 * (np.arange(-count, count + 1) / sigma) ** 2)
    kernel /= kernel.sum()
    distances = np.arange(count, 0, -1)[:, None]
    front = points[0] - distances * (points[1] - points[0])
    back = points[-1] + distances[::-1] * (points[-1] - points[-2])
    padded = np.vstack([front, points, back])
    return np.column_stack(
        [np.convolve(padded[:, axis], kernel, mode="valid") for axis in range(2)]
    )


def path_curvature(points):
    delta = np.diff(points, axis=0)
    heading = np.unwrap(np.arctan2(delta[:, 1], delta[:, 0]))
    return np.abs(np.diff(heading)) / np.maximum(
        (np.linalg.norm(delta, axis=1)[:-1] + np.linalg.norm(delta, axis=1)[1:]) / 2,
        0.01,
    )


class ObstacleMemory:
    def __init__(self):
        self.items = []

    def advance(self, translation, yaw):
        for item in self.items:
            item.center = (item.center - translation) @ rotation(yaw)

    def observe(self, rgb, camera, hint, dt):
        hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV)
        hue = cv2.cvtColor(np.uint8([[hint.marker_rgb]]), cv2.COLOR_RGB2HSV)[0, 0, 0]
        difference = np.abs(hsv[:, :, 0].astype(int) - int(hue))
        spread = rgb.max(axis=2).astype(int) - rgb.min(axis=2).astype(int)
        chromatic = (hsv[:, :, 1] > 65) & (hsv[:, :, 2] > 35) & (spread > 40)
        chromatic &= np.minimum(difference, 180 - difference) > 13
        mask = cv2.morphologyEx(
            chromatic.astype(np.uint8), cv2.MORPH_CLOSE, np.ones((19, 3), np.uint8)
        )
        # Neutral road paint must not become an obstacle proposal. Colored props
        # are the supported perception domain; untextured gray solids remain a
        # documented limitation of this monocular teaching baseline.
        gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
        support_threshold = min(120, float(np.percentile(gray, 65)) * 0.65)
        count, labels, stats, _ = cv2.connectedComponentsWithStats(mask, 8)
        for item in self.items:
            item.age += dt
        detections = []
        for label in range(1, count):
            x, y, w, h, area = stats[label]
            if x <= 1 or x + w >= rgb.shape[1] - 2:
                continue  # The ground contact of a cropped prop is unknown.
            # Cone bands can split one physical prop into several colored blobs.
            # Only the lowest aligned face supplies a ground-contact estimate.
            # This also postpones a collinear, occluded prop behind a nearer one.
            if any(
                other_area >= 28
                and other_y >= y + h
                and other_y - y - h < max(w, other_w) * 1.5
                and abs(x + w / 2 - other_x - other_w / 2) < max(w, other_w) * 0.35
                for other_x, other_y, other_w, _, other_area in stats[1:]
            ):
                continue
            if area < 28 or h < 8 or w < 4 or y + h >= rgb.shape[0] - 2:
                continue
            rows, cols = np.where(labels == label)
            ground = transform_points(np.c_[cols[::3], rows[::3]], camera.inv)
            # Flat finish rings occupy a compact patch on the ground plane.
            # Upright faces project to a much longer patch or across the horizon.
            span = np.ptp(ground, axis=0)
            if (
                np.all(ground[:, 0] > 0)
                and span[0] < 0.65
                and span[0] < 1.6 * max(span[1], 0.05)
            ):
                continue
            bottom = float(y + h - 1)
            # Locate a broad dark support below the colored face. Back-projecting
            # the cone's elevated orange skirt overestimates range substantially.
            for row in range(y + h, min(rgb.shape[0] - 2, y + h + max(4, h // 4))):
                if np.mean(gray[row, x : x + w] < support_threshold) < 0.45:
                    break
                bottom = float(row)
            edge = transform_points([[x, bottom], [x + w - 1, bottom]], camera.inv)
            front = edge.mean(axis=0)
            width = float(np.linalg.norm(edge[1] - edge[0]))
            if not (0.4 < front[0] < 5.5 and abs(front[1]) < 3 and 0.06 < width < 2):
                continue
            radius = max(0.16, width * 0.65 + 0.04)
            center = front + [radius - 0.08, 0]
            detections.append(Obstacle(center, radius))
        for found in detections:
            nearest = min(
                self.items,
                key=lambda item: np.linalg.norm(item.center - found.center),
                default=None,
            )
            if nearest is not None and np.linalg.norm(
                nearest.center - found.center
            ) < max(0.4, found.radius):
                nearest.center = 0.7 * nearest.center + 0.3 * found.center
                nearest.radius = max(nearest.radius * 0.99, found.radius)
                nearest.age = 0
            else:
                self.items.append(found)
        self.items = [
            item
            for item in self.items
            if item.age < 12
            and item.center[0] > -1.2
            and np.linalg.norm(item.center) < 7
        ]


class DetourPlanner:
    def __init__(self, limits):
        self.limits = limits
        self.path = None
        self.reference = None
        self.age = 0
        self.reason = "沿目标路线行驶"
        self.blocking = None
        self.rejections = {}
        self.peeking = False
        self.peek_attempted = False
        self.road_memory = np.empty((0, 2))
        self.rejoin_observed = False

    def advance(self, translation, yaw):
        self.road_memory = (self.road_memory - translation) @ rotation(yaw)
        self.road_memory = self.road_memory[
            (self.road_memory[:, 0] > -2)
            & (np.linalg.norm(self.road_memory, axis=1) < 8)
        ]
        for field in ("path", "reference"):
            points = getattr(self, field)
            if points is not None:
                points = (points - translation) @ rotation(yaw)
                nearest = int(np.argmin(np.linalg.norm(points, axis=1)))
                setattr(self, field, points[max(0, nearest - 2) :])

    def extend(self, path, components, blocker):
        """Bridge only an obstacle-explained gap to a unique aligned continuation."""
        path = path[np.argmin(np.linalg.norm(path, axis=1)) :]
        if len(path) < 5:
            return None
        distance = np.linalg.norm(path - blocker.center, axis=1)
        before = np.flatnonzero(
            (distance > blocker.radius + 0.15) & (path[:, 0] < blocker.center[0])
        )
        if len(before) < 3:
            return None
        index = before[-1]
        heading = principal_direction(
            path[max(0, index - 15) : index + 1], path[index] - path[max(0, index - 4)]
        )
        if (path[-1] - blocker.center) @ heading > blocker.radius + 1:
            return path
        tail = path[index]
        matches = []
        for pixels, metric in components:
            delta = metric - tail
            along = delta @ heading
            across = np.abs(delta @ np.array([-heading[1], heading[0]]))
            beyond = (metric - blocker.center) @ heading > blocker.radius + 0.15
            choices = np.flatnonzero(
                beyond & (along > 0) & (along < 2.5) & (across < 0.18)
            )
            if not len(choices):
                continue
            chosen = choices[np.argmin(along[choices] + 3 * across[choices])]
            if along[chosen] > blocker.radius * 2 + 0.6:
                continue
            local = metric[np.linalg.norm(metric - metric[chosen], axis=1) < 0.25]
            if len(local) < 4:
                continue
            direction = principal_direction(local, heading)
            if direction @ heading < 0.85:
                continue
            segment = trace_component(pixels, metric, chosen, direction)
            keep = (segment - tail) @ heading > along[chosen] - 0.06
            segment = segment[keep]
            if len(segment) < 8:
                continue
            matches.append((float(across[chosen]), segment))
        matches.sort(key=lambda item: item[0])
        if not matches or (len(matches) > 1 and matches[1][0] - matches[0][0] < 0.05):
            return None
        continuation = matches[0][1]
        bridge = np.linspace(
            tail,
            continuation[0],
            max(2, round(np.linalg.norm(continuation[0] - tail) / 0.04)),
        )
        return np.vstack([path[:index], bridge, continuation[1:]])

    def command_path(self, track, components, obstacles, dt):
        route = None if track is None else np.asarray(track)
        pending_peek = None
        if self.path is not None and self.peeking:
            self.age += dt
            visible = self.extend(
                self.reference,
                components,
                self.blocking,
            )
            if (
                visible is not None
                and np.linalg.norm(visible[-1] - self.blocking.center) > 1.3
            ):
                route = visible
                pending_peek = self.path, self.reference
                self.path = self.reference = None
                self.peeking = False
            elif self.age > 12 or self.path[-1, 0] < 0.15:
                self.reason = "有限侧移后仍看不到原路线续段，制动保留身份"
                return None, True
            else:
                return self.path, True
        if self.path is not None:
            self.age += dt
            rejoined = (
                self.reference is not None
                and np.min(np.linalg.norm(self.reference, axis=1)) < 0.12
            )
            if (
                self.blocking.center[0] < -0.3
                and rejoined
                and route is not None
                and self.rejoin_observed
            ):
                self.path = self.reference = None
                self.peek_attempted = False
                self.reason = "已重新接入原目标路线"
            elif self.age > 18 or len(self.path) < 3 or self.path[-1, 0] < 0.1:
                self.reason = "绕行预算耗尽或无法确认接回原路线，制动"
                return None, True
            else:
                return self.path, True
        if route is None or len(route) < 4:
            return None, False
        clearance = self.limits.get("width_m", 0.28) / 2 + 0.12
        blocking = [
            item
            for item in obstacles
            if 0.4 < item.center[0] < 3.2
            and np.min(np.linalg.norm(route - item.center, axis=1))
            # The radius already contains a 4 cm planning margin. Use the
            # estimated physical footprint to decide whether a road is blocked.
            < item.radius - 0.04 + self.limits.get("width_m", 0.28) / 2
        ]
        if pending_peek is not None:
            blocking.append(self.blocking)
        if not blocking:
            return route, False
        blocker = min(blocking, key=lambda item: item.center[0])
        self.blocking = blocker
        reference = self.extend(route, components, blocker)
        if reference is None:
            if not self.peek_attempted:
                peek = self.peek_path(route, components, obstacles, blocker)
                if peek is not None:
                    self.path, self.reference = peek, route.copy()
                    self.peeking = self.peek_attempted = True
                    self.age = 0
                    self.reason = "遮挡后续段不可见，在已观测走廊内有限侧移以恢复视野"
                    return self.path, True
            self.reason = "占道物件后方目标路线尚未确认，制动等待"
            return None, True
        heading = principal_direction(
            reference[: min(12, len(reference))],
            reference[min(5, len(reference) - 1)] - reference[0],
        )
        foot = reference[0] - heading * (reference[0] @ heading)
        reference = np.vstack(
            [foot, reference[np.sum((reference - foot) * heading, axis=1) > 0.04]]
        )
        arc = np.r_[0, np.cumsum(np.linalg.norm(np.diff(reference, axis=0), axis=1))]
        sample = np.arange(0, arc[-1], 0.05)
        reference = np.column_stack(
            [np.interp(sample, arc, reference[:, axis]) for axis in range(2)]
        )
        reference = smooth_path(reference)
        self.latest_reference = reference
        tangent = np.gradient(reference, axis=0)
        tangent /= np.maximum(np.linalg.norm(tangent, axis=1, keepdims=True), 1e-6)
        normal = np.c_[-tangent[:, 1], tangent[:, 0]]
        obstacle_arc = sample[
            np.argmin(np.linalg.norm(reference - blocker.center, axis=1))
        ]
        cloud = self.road_memory.copy()
        if len(cloud):
            distance = np.linalg.norm(cloud[:, None] - reference[None], axis=2).min(
                axis=1
            )
            cloud = cloud[distance > 0.2]
        best = None
        self.rejections = {
            key: 0
            for key in (
                "visibility",
                "corridor",
                "curvature",
                "obstacle",
                "other_route",
            )
        }
        for side in (-1, 1):
            for offset, departure in product((0.45, 0.6, 0.75, 0.9), (1.2, 1.6, 2.0)):
                start = max(0.15, obstacle_arc - blocker.radius - 1.8)
                end = obstacle_arc + blocker.radius + departure
                if end > sample[-1] + 0.1:
                    self.rejections["visibility"] += 1
                    continue
                phase = np.clip((sample - start) / (end - start), 0, 1)
                displacement = side * offset * np.sin(np.pi * phase) ** 2
                initial_offset = float(-reference[0] @ normal[0])
                blend = np.clip(sample / max(obstacle_arc, 0.5), 0, 1)
                displacement += initial_offset * (1 - 3 * blend**2 + 2 * blend**3)
                if np.max(np.abs(displacement)) > max(
                    0.8, blocker.radius + clearance + 0.2
                ):
                    self.rejections["corridor"] += 1
                    continue
                candidate = reference + normal * displacement[:, None]
                candidate = candidate[sample <= end + 0.2]
                kernel = np.array([1, 6, 15, 20, 15, 6, 1]) / 64
                candidate = np.column_stack(
                    [
                        np.convolve(
                            np.pad(candidate[:, axis], (3, 3), mode="edge"),
                            kernel,
                            mode="valid",
                        )
                        for axis in range(2)
                    ]
                )
                curvature = path_curvature(candidate)
                self.rejections["peak_curvature"] = float(curvature.max(initial=0))
                if (
                    curvature.max(initial=0)
                    > math.tan(self.limits["max_steering_rad"])
                    / self.limits["wheelbase_m"]
                    * 0.9
                ):
                    self.rejections["curvature"] += 1
                    continue
                if any(
                    np.min(np.linalg.norm(candidate - item.center, axis=1))
                    < item.radius + clearance
                    for item in obstacles
                ):
                    self.rejections["obstacle"] += 1
                    continue
                if len(cloud) and np.any(
                    np.min(
                        np.linalg.norm(candidate[:, None] - cloud[None], axis=2), axis=1
                    )
                    < np.minimum(0.32, np.abs(displacement[: len(candidate)]) + 0.08)
                ):
                    self.rejections["other_route"] += 1
                    continue
                cost = offset + 0.08 * np.sum(curvature**2)
                if best is None or cost < best[0]:
                    best = cost, candidate
        if best is None:
            if pending_peek is not None:
                self.path, self.reference = pending_peek
                self.peeking = True
                if self.age < 12 and self.path[-1, 0] >= 0.15:
                    self.reason = "续段尚不足以规划可行绕行，继续已验证的有限侧移"
                    return self.path, True
            else:
                self.reference = reference
            self.reason = "没有满足转弯、障碍物净距和邻线隔离约束的绕行路线，制动"
            return None, True
        self.path, self.reference, self.age = best[1], reference, 0
        self.reason = "锁定原路线身份，沿碰撞检查通过的局部绕行轨迹行驶"
        return self.path, True

    def peek_path(self, route, components, obstacles, blocker):
        length = min(1.7, blocker.center[0] - blocker.radius - 0.8)
        if length < 1.2:
            return None
        x = np.linspace(0, length, 45)
        points = route[route[:, 0] < length + 0.3]
        if len(points) < 4 or np.max(np.abs(points[:, 1])) > 0.2:
            return None
        cloud = np.concatenate([metric for _, metric in components])
        cloud = np.vstack([cloud, self.road_memory])
        cloud = cloud[np.abs(cloud[:, 1]) > 0.2]
        candidates = []
        for side in (-1, 1):
            path = np.c_[x, side * 0.7 * (1 - np.cos(np.pi * x / length)) / 2]
            if path_curvature(path).max(initial=0) > (
                0.9
                * math.tan(self.limits["max_steering_rad"])
                / self.limits["wheelbase_m"]
            ):
                continue
            if any(
                np.min(np.linalg.norm(path - item.center, axis=1)) < item.radius + 0.3
                for item in obstacles
            ):
                continue
            separation = (
                np.min(np.linalg.norm(path[:, None] - cloud[None], axis=2))
                if len(cloud)
                else 3
            )
            if separation > 0.2:
                candidates.append((separation, path))
        return max(candidates, key=lambda item: item[0])[1] if candidates else None


class AvoidanceTracker(TargetTracker):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.obstacles = ObstacleMemory()
        self.planner = None

    def advance(self, translation, yaw):
        super().advance(translation, yaw)
        self.obstacles.advance(translation, yaw)
        self.planner.advance(translation, yaw)

    def observe(self, observation, dt):
        if observation.calibration is not None:
            if self.camera is None or not np.array_equal(
                self.camera.h, observation.calibration.ground_to_image
            ):
                self.camera = BirdEye(observation.calibration)
            self.obstacles.observe(
                observation.rgb(), self.camera, observation.task_hint, dt
            )
        if self.planner.reference is not None:
            self.path = self.planner.reference.copy()
        result = super().observe(observation, dt)
        self.planner.rejoin_observed = False
        remembered = self.planner.reference
        if (
            remembered is not None
            and result.path is not None
            and not result.predicted
            and self.planner.blocking is not None
            and self.planner.blocking.center[0] < 0.4
        ):
            # Refresh the visible suffix only after the blocker is being passed.
            # Keep the blind near prefix: it carries the original route identity.
            visible = remembered[
                (remembered[:, 0] > 0.65) & (np.linalg.norm(remembered, axis=1) < 2.5)
            ]
            if len(visible) >= 3:
                error = np.linalg.norm(
                    visible[:, None] - result.path[None], axis=2
                ).min(axis=1)
                if np.median(error) < 0.1 and np.percentile(error, 80) < 0.2:
                    join = np.argmin(
                        np.linalg.norm(remembered - result.path[0], axis=1)
                    )
                    self.planner.reference = np.vstack([remembered[:join], result.path])
                    self.planner.rejoin_observed = True
        if self.components:
            observed = np.vstack(
                [*[metric for _, metric in self.components], self.planner.road_memory]
            )
            _, indices = np.unique(
                np.round(observed / 0.06).astype(int), axis=0, return_index=True
            )
            self.planner.road_memory = observed[indices]
        return result
