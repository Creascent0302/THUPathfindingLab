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
from .prediction import RouteForecast


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


def bezier_path(end, heading, handle, end_handle=None, count=60):
    """A vehicle-aligned departure and a tangent-aligned endpoint."""
    t = np.linspace(0, 1, count)[:, None]
    return (
        3 * (1 - t) ** 2 * t * np.array([handle, 0])
        + 3
        * (1 - t)
        * t**2
        * (end - heading * (handle if end_handle is None else end_handle))
        + t**3 * end
    )


class ObstacleMemory:
    def __init__(self):
        self.items = []
        self.image_boxes = []

    def advance(self, translation, yaw):
        for item in self.items:
            item.center = (item.center - translation) @ rotation(yaw)

    def observe(self, rgb, camera, hint, dt, pinned=None):
        self.image_boxes = []
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
            if area < 28 or h < 8 or w < 4:
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
            top = min(
                other_y
                for other_x, other_y, other_w, _, _ in stats[1:]
                if y - 3 * h <= other_y <= y
                and abs(x + w / 2 - other_x - other_w / 2) < max(w, other_w) * 0.35
            )
            cropped = x <= 1 or x + w >= rgb.shape[1] - 2 or y + h >= rgb.shape[0] - 2
            padding = max(3, round(w * (0.35 if cropped else 0.2)))
            self.image_boxes.append(
                (
                    max(0, x - padding),
                    max(0, top - 2),
                    min(rgb.shape[1], x + w + padding),
                    min(rgb.shape[0], int(bottom) + 3),
                )
            )
            # Cropping prevents a metric footprint estimate, but does not turn
            # a known upright face into road pixels. Exclude its image first.
            if cropped:
                continue
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
            if item is pinned
            or (
                item.age < 30
                and item.center[0] > -3
                and np.linalg.norm(item.center) < 7
            )
        ]


class DetourPlanner:
    def __init__(self, limits):
        self.limits = limits
        self.path = None
        self.reference = None
        self.last_route = None
        self.age = 0
        self.reason = "沿目标路线行驶"
        self.blocking = None
        self.rejections = {}
        self.peeking = False
        self.peek_attempted = False
        self.road_memory = np.empty((0, 2))
        self.target_memory = np.empty((0, 2))
        self.target_age = np.empty(0)
        self.rejoin_observed = False
        self.recovery_pending = False
        self.corridor_m = 0.8
        self.handoffs = 0
        self.route_unseen_s = self.route_unseen_m = 0.0
        self.planned_obstacles = 0
        self.forecast = RouteForecast()
        self.predicted_route = False
        self.continuation_ambiguous = False
        self.prediction_rejection = ""
        self.continuing = False

    @property
    def visibility_exhausted(self):
        reliable = (
            self.predicted_route
            and self.forecast.trustworthy
            and abs(self.forecast.curvature) <= 0.12
            and not self.prediction_rejection
        )
        seconds, distance = (20.0, 4.5) if reliable else (6.0, 1.5)
        return self.reference is not None and (
            self.route_unseen_s > seconds or self.route_unseen_m > distance
        )

    def advance(self, translation, yaw):
        self.forecast.advance(translation, rotation(yaw), yaw)
        if self.reference is not None and self.route_unseen_s > 0:
            self.route_unseen_m += float(np.linalg.norm(translation))
        self.target_memory = (self.target_memory - translation) @ rotation(yaw)
        self.road_memory = (self.road_memory - translation) @ rotation(yaw)
        self.road_memory = self.road_memory[
            (self.road_memory[:, 0] > -2)
            & (np.linalg.norm(self.road_memory, axis=1) < 8)
        ]
        for field in ("path", "reference", "last_route"):
            points = getattr(self, field)
            if points is not None:
                points = (points - translation) @ rotation(yaw)
                nearest = int(np.argmin(np.linalg.norm(points, axis=1)))
                # An off-line car's nearest road point can jump to an occluder
                # edge. Keep a metric history for route tangents through the gap.
                history = 45 if field != "path" else 2
                setattr(self, field, points[max(0, nearest - history) :])

    def remember_target(self, path, dt):
        self.target_age += dt
        keep = (self.target_age < 3) & (self.target_memory[:, 0] > -0.5)
        self.target_memory, self.target_age = (
            self.target_memory[keep],
            self.target_age[keep],
        )
        if path is None or self.reference is not None:
            return
        self.last_route = np.asarray(path).copy()
        arc = np.r_[0, np.cumsum(np.linalg.norm(np.diff(path, axis=0), axis=1))]
        path = path[arc < 4]
        points = np.vstack([path, self.target_memory])
        age = np.r_[np.zeros(len(path)), self.target_age]
        _, selected = np.unique(
            np.round(points / 0.05).astype(int), axis=0, return_index=True
        )
        self.target_memory, self.target_age = points[selected], age[selected]

    def other_roads(self, reference):
        """Do not mislabel our recently observed blind near curve as a neighbor."""
        cloud = self.road_memory
        support = np.vstack([reference, self.target_memory])
        if len(cloud):
            distance = np.linalg.norm(cloud[:, None] - support[None], axis=2).min(
                axis=1
            )
            cloud = cloud[distance > 0.15]
        return cloud

    def remember_roads(self, components, camera):
        """Refresh visible ground; keep blind near-field lines for side isolation.

        Upright prop edges do not have a fixed ground-plane position. Retaining
        their old projections forever would create phantom parallel roads.
        """
        if not components:
            return
        observed = np.vstack([metric for _, metric in components])
        old = self.road_memory
        if len(old):
            pixels = camera.pixels(old)
            visible = (
                (old[:, 0] > 0.7)
                & (pixels[:, 0] > 5)
                & (pixels[:, 0] < camera.size[0] - 5)
                & (pixels[:, 1] > 5)
                & (pixels[:, 1] < camera.size[1] - 5)
            )
            supported = (
                np.linalg.norm(old[:, None] - observed[None], axis=2).min(axis=1) < 0.1
            )
            old = old[~visible | supported]
        points = np.vstack([observed, old])
        _, indices = np.unique(
            np.round(points / 0.06).astype(int), axis=0, return_index=True
        )
        self.road_memory = points[indices]

    def extend(self, path, components, blocker):
        """Bridge only an obstacle-explained gap to a unique aligned continuation."""
        self.continuation_ambiguous = False
        if len(path) < 3:
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
            # During a verified side-view maneuver the camera's near blind wedge
            # can hide extra ground beyond the prop. Association still requires
            # one aligned continuation; distance alone cannot pick a road.
            gap_limit = 2.5 if self.peeking else blocker.radius * 2 + 0.6
            if along[chosen] > gap_limit:
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
        if len(matches) > 1 and matches[1][0] - matches[0][0] < 0.05:
            self.continuation_ambiguous = True
            return None
        if not matches:
            return None
        continuation = matches[0][1]
        # A uniquely matched visible suffix is fresh route evidence even when
        # the ordinary near-line tracker is temporarily occluded. Reusing an
        # already stored suffix above must NOT refresh this budget.
        self.route_unseen_s = self.route_unseen_m = 0.0
        self.forecast.observe(continuation, [blocker])
        bridge = np.linspace(
            tail,
            continuation[0],
            max(2, round(np.linalg.norm(continuation[0] - tail) / 0.04)),
        )
        return np.vstack([path[:index], bridge, continuation[1:]])

    def predict_reference(self, route, visible, blocker):
        """Extend a short observed horizon, while preserving measured geometry."""
        model = self.forecast
        prediction = model.continuation()
        if prediction is None or abs(model.curvature) > 0.12:
            return None
        heading = np.array([math.cos(model.heading), math.sin(model.heading)])
        if visible is not None:
            # A working measured continuation takes precedence over extrapolation.
            if (visible[-1] - blocker.center) @ heading > blocker.radius + 1.0:
                return None
            error = np.linalg.norm(visible[:, None] - prediction[None], axis=2).min(
                axis=1
            )
            if np.percentile(error, 80) > 0.12:
                self.prediction_rejection = "新观测与预测几何不一致，等待原线续段"
                return None
        cloud = self.other_roads(route)
        tail = prediction[len(model.observed) :]
        if len(cloud):
            distance = np.linalg.norm(cloud[:, None] - tail[None], axis=2)
            closest = distance.argmin(axis=1)
            separation = distance[np.arange(len(cloud)), closest]
            # Collinear ground support is compatible with the hypothesis. It
            # does not refresh its lifetime or count as confirmed rejoining.
            compatible = np.zeros(len(cloud), dtype=bool)
            for index in np.flatnonzero(separation < 0.10):
                local = cloud[np.linalg.norm(cloud - cloud[index], axis=1) < 0.2]
                if len(local) >= 4:
                    compatible[index] = (
                        principal_direction(local, heading) @ heading > 0.97
                    )
            margin = 0.16 + model.uncertainty((closest + 1) * 0.05)
            if np.any((separation < margin) & ~compatible):
                self.prediction_rejection = (
                    "预测误差走廊与其他可见道路重叠，等待唯一续段"
                )
                return None
        self.prediction_rejection = ""
        return prediction

    def command_path(self, track, components, obstacles, dt):
        if self.visibility_exhausted:
            # Permit new visual evidence to release the stop. A cached suffix
            # returned by extend() does not count as a new observation.
            if self.blocking is not None:
                self.extend(self.reference, components, self.blocking)
                if self.visibility_exhausted and not self.continuation_ambiguous:
                    prediction = self.predict_reference(
                        self.reference, None, self.blocking
                    )
                    if prediction is not None:
                        # Exhausting the short visual budget is itself a reason
                        # to try the bounded model. It must still produce a new
                        # feasible path below; it cannot extend the old maneuver.
                        self.reference = prediction
                        self.path = None
                        self.predicted_route = self.peek_attempted = True
                        self.peeking = self.continuing = False
                        self.recovery_pending = True
                        track = prediction
        if self.visibility_exhausted:
            self.reason = "原目标路线持续不可见，停止接续绕行并制动保留身份"
            return None, True
        route = None if track is None else np.asarray(track)
        if route is None or len(route) < 4:
            route = self.last_route
        if (
            self.reference is not None
            and self.blocking is not None
            and self.blocking.center[0] < -0.3
            and self.rejoin_observed
            and np.min(np.linalg.norm(self.reference, axis=1)) < 0.12
        ):
            self.last_route = self.reference.copy()
            self.path = self.reference = None
            self.peeking = self.peek_attempted = self.continuing = False
            self.recovery_pending = self.predicted_route = False
            self.reason = "已重新接入原目标路线"
        if self.path is not None and self.continuing and self.path[-1, 0] < 0.8:
            route = self.reference.copy()
            self.path = None
            self.recovery_pending = True
        if self.path is not None:
            near = int(np.argmin(np.linalg.norm(self.path, axis=1)))
            remaining = self.path[near:]
            obstructed = [
                item
                for item in obstacles
                if item.center[0] > 0.3
                and np.linalg.norm(remaining - item.center, axis=1).min()
                < item.radius + self.limits.get("width_m", 0.28) / 2 + 0.12
            ]
            if obstructed:
                blocker = min(obstructed, key=lambda item: item.center[0])
                self.handoffs += int(blocker is not self.blocking)
                route = self.reference.copy()
                self.path = None
                self.blocking = blocker
                self.peeking = self.peek_attempted = False
                self.recovery_pending = True
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
                self.last_route = self.reference.copy()
                self.path = self.reference = None
                self.peeking = False
            elif (
                self.path[-1, 0] < 0.2
                and self.forecast.trustworthy
                and not self.continuation_ambiguous
                and abs(self.forecast.curvature) <= 0.12
            ):
                # First use the measured side-view maneuver. Prediction is a
                # fallback at its horizon, not a reason to replace a working
                # visual plan with a guess about a hidden bend.
                route = self.reference.copy()
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
            # Look ahead while still beside the first prop. The stored road,
            # never the offset detour, remains the identity reference. A newly
            # blocked return must not force us back onto the line before planning.
            following = (
                self.blockers(self.reference, obstacles)
                if self.blocking.center[0] < -0.4 and self.reference is not None
                else []
            )
            following = [item for item in following if item is not self.blocking]
            if following:
                route = self.reference.copy()
                self.last_route = route.copy()
                self.path = None
                self.peeking = self.peek_attempted = False
                self.blocking = min(following, key=lambda item: item.center[0])
                self.recovery_pending = True
                self.handoffs += 1
        if self.path is not None:
            if self.age > 18 or len(self.path) < 3 or self.path[-1, 0] < 0.1:
                self.reason = "绕行预算耗尽或无法确认接回原路线，制动"
                return None, True
            return self.path, True
        if route is None or len(route) < 4:
            return None, False
        clearance = self.limits.get("width_m", 0.28) / 2 + 0.12
        blocking = self.blockers(route, obstacles)
        if self.recovery_pending and self.blocking is not None:
            # A retreat must not forget the blockage merely because its stored
            # reference ends before the next prop. Keep the previously confirmed
            # blocker through the retry; no new road identity is inferred here.
            if -1.5 < self.blocking.center[0] < 4:
                blocking.append(self.blocking)
        if pending_peek is not None:
            blocking.append(self.blocking)
        if not blocking:
            if self.reference is not None and self.predicted_route:
                self.reason = "预测走廊结束，制动等待原路线的新观测"
                return None, True
            return route, False
        blocker = min(blocking, key=lambda item: item.center[0])
        self.blocking = blocker
        reference = self.extend(route, components, blocker)
        if self.peek_attempted and not self.continuation_ambiguous:
            prediction = self.predict_reference(route, reference, blocker)
            if prediction is not None:
                reference = prediction
                self.predicted_route = True
        if reference is None:
            if pending_peek is not None:
                self.path, self.reference = pending_peek
                self.peeking = True
                if self.age < 12 and self.path[-1, 0] >= 0.15:
                    self.reason = "续段关联暂不稳定，保留已验证的侧移与原路线身份"
                    return self.path, True
                self.reason = "预测无法接续已验证路径，制动等待新观测"
                return None, True
            if not self.peek_attempted:
                peek = self.peek_path(route, obstacles, blocker)
                if peek is not None:
                    self.path, self.reference = peek, route.copy()
                    self.peeking = self.peek_attempted = True
                    self.continuing = False
                    self.recovery_pending = False
                    self.age = 0
                    self.reason = "遮挡后续段不可见，在已观测走廊内有限侧移以恢复视野"
                    return self.path, True
            self.reason = "占道物件后方目标路线尚未确认，制动等待"
            self.reference = route.copy()
            return None, True
        nearest = int(np.argmin(np.linalg.norm(reference, axis=1)))
        begin, end_index = max(0, nearest - 6), min(len(reference) - 1, nearest + 8)
        heading = principal_direction(
            reference[begin : end_index + 1], reference[end_index] - reference[begin]
        )
        foot = reference[nearest] - heading * (reference[nearest] @ heading)
        reference = reference[max(0, nearest - 1) :]
        reference = np.vstack(
            [foot, reference[np.sum((reference - foot) * heading, axis=1) > 0.04]]
        )
        arc = np.r_[0, np.cumsum(np.linalg.norm(np.diff(reference, axis=0), axis=1))]
        sample = np.arange(0, arc[-1], 0.05)
        reference = np.column_stack(
            [np.interp(sample, arc, reference[:, axis]) for axis in range(2)]
        )
        reference = smooth_path(reference)
        tangent = np.gradient(reference, axis=0)
        tangent /= np.maximum(np.linalg.norm(tangent, axis=1, keepdims=True), 1e-6)
        normal = np.c_[-tangent[:, 1], tangent[:, 0]]
        obstacle_arc = sample[
            np.argmin(np.linalg.norm(reference - blocker.center, axis=1))
        ]
        group = [(obstacle_arc, blocker)]
        for item in sorted(blocking, key=lambda item: item.center[0]):
            if item is blocker:
                continue
            at = int(np.argmin(np.linalg.norm(reference - item.center, axis=1)))
            along = sample[at]
            if group[-1][0] < along <= group[-1][0] + 2.0:
                group.append((along, item))
        last_arc, last_blocker = group[-1]
        self.planned_obstacles = len(group)
        cloud = self.other_roads(reference)
        self.corridor_m = self.corridor_limit(reference, blocker)
        if self.predicted_route:
            # A model can justify a longer observation gap, not a wider blind
            # excursion. Large detours require measured road geometry.
            self.corridor_m = min(self.corridor_m, 0.8)
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
            needed = 0.35
            for _, item in group:
                at = int(np.argmin(np.linalg.norm(reference - item.center, axis=1)))
                lateral = float((item.center - reference[at]) @ normal[at])
                needed = max(needed, side * lateral + item.radius + clearance + 0.04)
            offsets = sorted({0.45, 0.6, 0.75, 0.9, needed, needed + 0.05})
            for offset, approach, departure in product(
                offsets, (0.9, 1.15, 1.4, 1.8), (0.85, 1.15, 1.6, None)
            ):
                continuing = departure is None
                if continuing and not (
                    self.predicted_route
                    and self.forecast.trustworthy
                    and abs(self.forecast.curvature) <= 0.12
                ):
                    continue
                start = max(0.0, obstacle_arc - blocker.radius - approach)
                end = (
                    sample[-1]
                    if continuing
                    else last_arc + last_blocker.radius + departure
                )
                if continuing and end < 1.0:
                    continue
                if end > sample[-1] + 0.1:
                    self.rejections["visibility"] += 1
                    continue
                initial_offset = float(-reference[0] @ normal[0])
                heading_error = math.atan2(tangent[0, 1], tangent[0, 0])
                if abs(initial_offset) > 0.1 or abs(heading_error) > 0.12:
                    start = 0.0
                rise = np.clip((sample - start) / max(obstacle_arc - start, 0.4), 0, 1)
                fall = (
                    np.zeros(len(sample))
                    if continuing
                    else np.clip((sample - last_arc) / max(end - last_arc, 0.4), 0, 1)
                )
                rise, fall = rise**2 * (3 - 2 * rise), fall**2 * (3 - 2 * fall)
                displacement = initial_offset + (side * offset - initial_offset) * rise
                if start == 0:
                    u = np.clip(sample / max(obstacle_arc, 0.4), 0, 1)
                    displacement -= (
                        math.tan(np.clip(heading_error, -0.7, 0.7))
                        * sample
                        * (1 - u) ** 2
                    )
                displacement *= 1 - fall
                if np.max(np.abs(displacement)) > self.corridor_m:
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
                cost = self.detour_cost(
                    candidate,
                    np.abs(displacement[: len(candidate)]),
                    cloud,
                    obstacles,
                )
                if cost is None:
                    continue
                # Crossing back through the road solely to change passing side
                # adds an unnecessary slalom when already beside a previous prop.
                if side * initial_offset < -0.18:
                    cost += 1.5 * abs(initial_offset)
                rank = continuing, cost
                if best is None or rank < best[0]:
                    best = rank, candidate
        # A side-view maneuver has already left the line. Its return must start
        # at the current position AND heading, rather than replay a zero-offset
        # departure profile. Search tangent-matched returns to observed points.
        if np.linalg.norm(reference[0]) > 0.25 and blocker.center[0] < 1.5:
            for departure, scale, end_scale in product(
                (1.2, 1.6, 2.0, 2.4), (0.35, 0.5), (0.35, 0.5)
            ):
                end_arc = last_arc + last_blocker.radius + departure
                if end_arc > sample[-1]:
                    continue
                index = int(np.searchsorted(sample, end_arc))
                length = float(np.linalg.norm(reference[index]))
                candidate = bezier_path(
                    reference[index], tangent[index], length * scale, length * end_scale
                )
                distance = np.linalg.norm(
                    candidate[:, None] - reference[None, : index + 1], axis=2
                ).min(axis=1)
                cost = self.detour_cost(candidate, distance, cloud, obstacles)
                if cost is None:
                    continue
                rank = False, cost
                if best is None or rank < best[0]:
                    best = rank, candidate
        if best is None:
            if self.recovery_pending and not self.peek_attempted:
                peek = self.peek_path(route, obstacles, blocker)
                if peek is not None:
                    self.path, self.reference, self.age = peek, route.copy(), 0
                    self.peeking = self.peek_attempted = True
                    self.continuing = False
                    self.recovery_pending = False
                    self.reason = "完整绕行暂受视野限制，先执行净距和曲率检查通过的侧移"
                    return self.path, True
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
        self.continuing = best[0][0]
        self.recovery_pending = False
        self.reason = "锁定原路线身份，沿碰撞检查通过的局部绕行轨迹行驶"
        if self.predicted_route:
            self.reason = "沿已确认原线的有界预测绕行，等待新观测校正与接回确认"
        if self.continuing:
            self.reason = "连续遮挡下沿预测原线旁的有限走廊前进，滚动寻找接回窗口"
        return self.path, True

    @property
    def max_curvature(self):
        return (
            0.9 * math.tan(self.limits["max_steering_rad"]) / self.limits["wheelbase_m"]
        )

    def blockers(self, route, obstacles):
        """Detect a truncated road behind a prop's exclusion halo as blocked.

        A short tangent extension is only a blockage test, never an accepted
        hidden continuation. Lateral separation still rejects roadside props.
        """
        tangent = principal_direction(
            route[-8:], route[-1] - route[max(0, len(route) - 5)]
        )
        result = []
        for item in obstacles:
            if not 0.4 < item.center[0] < 3.2:
                continue
            length = np.clip((item.center - route[-1]) @ tangent, 0, item.radius + 0.25)
            end = route[-1] + length * tangent
            distance = min(
                np.linalg.norm(route - item.center, axis=1).min(),
                np.linalg.norm(end - item.center),
            )
            if distance < item.radius - 0.04 + self.limits.get("width_m", 0.28) / 2:
                result.append(item)
        return result

    def detour_cost(self, path, displacement, cloud, obstacles):
        """Use identical feasibility checks for departures and side-view returns."""
        clearance = self.limits.get("width_m", 0.28) / 2 + 0.12
        curvature = path_curvature(path)
        peak = float(curvature.max(initial=0))
        self.rejections["peak_curvature"] = peak
        reason = None
        if np.max(displacement) > self.corridor_m:
            reason = "corridor"
        elif peak > self.max_curvature:
            reason = "curvature"
        elif any(
            np.linalg.norm(path - item.center, axis=1).min() < item.radius + clearance
            for item in obstacles
        ):
            reason = "obstacle"
        elif not self.neighbor_clearance(path, displacement, cloud):
            reason = "other_route"
        if reason is not None:
            self.rejections[reason] += 1
            return None
        return self.compact_cost(path, displacement, curvature)

    @staticmethod
    def compact_cost(path, displacement, curvature):
        # Integrate per metre: a sampling-dependent curvature sum used to reward
        # long sweeping turns. Stay near the road and return promptly, with
        # curvature remaining a hard constraint rather than the main objective.
        ds = np.linalg.norm(np.diff(path, axis=0), axis=1)
        area = float(np.sum((displacement[:-1] + displacement[1:]) * ds / 2))
        bending = float(np.sum(curvature**2 * (ds[:-1] + ds[1:]) / 2))
        excess = float(ds.sum() - np.linalg.norm(path[-1] - path[0]))
        return 0.7 * float(np.max(displacement)) + area + 0.2 * excess + 0.015 * bending

    def corridor_limit(self, reference, blocker):
        index = int(np.argmin(np.linalg.norm(reference - blocker.center, axis=1)))
        tangent = (
            reference[min(index + 2, len(reference) - 1)] - reference[max(0, index - 2)]
        )
        tangent /= max(float(np.linalg.norm(tangent)), 1e-8)
        normal = np.array([-tangent[1], tangent[0]])
        lateral = abs(float((blocker.center - reference[index]) @ normal))
        return min(
            1.0,
            max(
                0.8,
                lateral + blocker.radius + self.limits.get("width_m", 0.28) / 2 + 0.32,
            ),
        )

    @staticmethod
    def neighbor_clearance(path, displacement, cloud):
        if not len(cloud):
            return True
        # A car already near a neighbor can move AWAY from it. Demanding full
        # clearance at the current pose would reject every recovery path. The
        # required separation grows with arc length; it never permits moving
        # closer than the current separation just to complete a candidate.
        initial = np.linalg.norm(cloud, axis=1).min()
        arc = np.r_[0, np.cumsum(np.linalg.norm(np.diff(path, axis=0), axis=1))]
        required = np.minimum(
            np.minimum(0.32, displacement + 0.08), initial + 0.25 * arc
        )
        distance = np.linalg.norm(path[:, None] - cloud[None], axis=2).min(axis=1)
        return bool(np.all(distance + 1e-9 >= required))

    def peek_path(self, route, obstacles, blocker):
        closest = int(np.argmin(np.linalg.norm(route - blocker.center, axis=1)))
        clean = route[: closest + 1]
        clean = clean[
            np.linalg.norm(clean - blocker.center, axis=1) > blocker.radius + 0.22
        ]
        if len(clean) < 4:
            return None
        heading = principal_direction(
            clean[-15:], clean[-1] - clean[max(0, len(clean) - 5)]
        )
        foot = clean[-1] - heading * (clean[-1] @ heading)
        reference = np.vstack([foot, route])
        cloud = self.other_roads(reference)
        candidates = []
        self.rejections = {
            key: 0 for key in ("peek_curvature", "peek_obstacle", "peek_neighbor")
        }
        # The dark rubber base is not a road tangent. A viewpoint may extend the
        # last clean tangent a short distance, but it never confirms a hidden line.
        extension = min(0.65, max(0, (blocker.center - clean[-1]) @ heading - 0.12))
        endpoint = clean[-1] + extension * heading
        maximum = min(2.5, float(endpoint @ heading))
        for length, lead, scale, end_scale in product(
            (maximum, maximum * 0.8),
            (0.0, 0.35, 0.7, 1.05),
            (0.35, 0.45, 0.55),
            (0.35, 0.5),
        ):
            if length - lead < 0.8:
                continue
            if lead and (abs(foot[1]) > 0.12 or abs(heading[1]) > 0.15):
                continue
            target = foot + heading * length
            tangent = heading
            normal = np.array([-tangent[1], tangent[0]])
            choices = []
            for side in (-1, 1):
                lateral = float((blocker.center - foot) @ normal)
                needed = max(
                    0.35,
                    side * lateral
                    + blocker.radius
                    + self.limits.get("width_m", 0.28) / 2
                    + 0.12
                    + 0.025,
                )
                maximum_offset = self.corridor_limit(reference, blocker)
                offsets = {needed, needed + 0.06}
                offsets = {value for value in offsets if value <= maximum_offset}
                choices.extend((side, offset) for offset in sorted(offsets))
            for side, offset in choices:
                end = target + side * offset * normal
                origin = np.array([lead, 0])
                path = (
                    bezier_path(
                        end - origin,
                        tangent,
                        (length - lead) * scale,
                        (length - lead) * end_scale,
                    )
                    + origin
                )
                if lead:
                    prefix = np.c_[
                        np.arange(0, lead, 0.04),
                        np.zeros(len(np.arange(0, lead, 0.04))),
                    ]
                    path = np.vstack([prefix, path])
                curvature = path_curvature(path)
                if curvature.max(initial=0) > self.max_curvature:
                    self.rejections["peek_curvature"] += 1
                    continue
                if any(
                    np.min(np.linalg.norm(path - item.center, axis=1))
                    < item.radius + self.limits.get("width_m", 0.28) / 2 + 0.12
                    for item in obstacles
                ):
                    self.rejections["peek_obstacle"] += 1
                    continue
                distance = (
                    np.min(np.linalg.norm(path[:, None] - cloud[None], axis=2), axis=1)
                    if len(cloud)
                    else np.full(len(path), 3.0)
                )
                if np.any(
                    distance
                    < np.minimum(0.28, np.linalg.norm(path, axis=1) * 0.2 + 0.1)
                ):
                    self.rejections["peek_neighbor"] += 1
                    continue
                displacement = np.abs((path - foot) @ normal)
                score = self.compact_cost(path, displacement, curvature) + 0.4 * (
                    maximum - length
                )
                candidates.append((score, path))
        return min(candidates, key=lambda item: item[0])[1] if candidates else None


class ObstacleCamera(BirdEye):
    """An upright object's pixels cannot supply a ground-plane road tangent."""

    image_boxes = ()
    ground_obstacles = ()
    dark_line_ratio = 0.55

    def extract(self, rgb, hint):
        if self.image_boxes:
            neutral_ground = int(
                np.percentile(cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY), 65)
            )
            rgb = rgb.copy()
            for x0, y0, x1, y1 in self.image_boxes:
                rgb[y0:y1, x0:x1] = neutral_ground
        excluded = np.zeros(self.valid.shape, dtype=bool)
        for item in self.ground_obstacles:
            # Projected prop edges and near-contact shadows cannot certify a
            # road. This halo stays INSIDE the forbidden obstacle clearance, so
            # masking a nearby real line cannot permit driving onto that line.
            excluded |= (
                np.linalg.norm(self.ground - item.center, axis=2) < item.radius + 0.13
            )
        return super().extract(rgb, hint, excluded)


class AvoidanceTracker(TargetTracker):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.obstacles = ObstacleMemory()
        self.planner = None
        self.recovery = None

    def advance(self, translation, yaw):
        super().advance(translation, yaw)
        self.obstacles.advance(translation, yaw)
        self.planner.advance(translation, yaw)
        if self.recovery is not None:
            self.recovery.advance(translation, yaw)

    def observe(self, observation, dt):
        if observation.calibration is not None:
            if self.camera is None or not np.array_equal(
                self.camera.h, observation.calibration.ground_to_image
            ):
                self.camera = ObstacleCamera(observation.calibration)
            self.obstacles.observe(
                observation.rgb(),
                self.camera,
                observation.task_hint,
                dt,
                pinned=self.planner.blocking
                if self.planner.reference is not None
                else None,
            )
            self.camera.image_boxes = self.obstacles.image_boxes
            self.camera.ground_obstacles = self.obstacles.items
        if self.planner.reference is not None:
            self.path = self.planner.reference.copy()
        result = super().observe(observation, dt)
        self.planner.forecast.age += dt
        if not result.predicted and result.path is not None:
            self.planner.route_unseen_s = 0.0
            self.planner.route_unseen_m = 0.0
            self.planner.forecast.observe(result.path, self.obstacles.items)
        else:
            self.planner.route_unseen_s += dt
        self.planner.remember_target(None if result.predicted else result.path, dt)
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
                    if self.planner.predicted_route:
                        # Replace a hypothetical return with the newly measured
                        # road, from the current offset and heading.
                        self.planner.path = None
                        self.planner.continuing = self.planner.peeking = False
                        self.planner.recovery_pending = True
                    self.planner.predicted_route = False
        self.planner.remember_roads(self.components, self.camera)
        for item in self.obstacles.items:
            cloud = self.planner.road_memory
            self.planner.road_memory = cloud[
                np.linalg.norm(cloud - item.center, axis=1) >= item.radius + 0.13
            ]
        return result
