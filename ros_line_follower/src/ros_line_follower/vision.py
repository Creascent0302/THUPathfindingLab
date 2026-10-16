"""Metric line perception adapted from algorithms/modular/vision.py.

The reference origin must initially lie on the intended line and point along it.
Images are rectified RGB; the homography maps reference-ground metres to pixels.
No ROS, simulator, controller, coloured start marker or end marker is required.
"""

from __future__ import annotations

from dataclasses import dataclass, fields
import math
from typing import Optional

import cv2
import numpy as np


@dataclass(frozen=True)
class VisionConfig:
    bev_forward_m: float = 15.0
    bev_half_width_m: float = 4.0
    resolution_m: float = 0.04
    association_gate_m: float = 0.25
    memory_s: float = 0.35
    minimum_radius_m: float = 2.0
    line_polarity: str = "dark"
    association_range_m: float = 6.0
    initial_anchor_m: float = 1.0
    local_direction_radius_m: float = 0.35
    background_width_m: float = 0.60
    minimum_component_length_m: float = 0.32
    minimum_path_length_m: float = 0.30
    initial_gate_m: float = 0.30
    ambiguity_margin_m: float = 0.06
    heading_weight_m: float = 0.12
    support_length_m: float = 3.0
    support_spacing_m: float = 0.20
    anchor_lookahead_m: float = 0.60
    progress_search_m: float = 2.0
    max_trace_vertices: int = 2000

    def __post_init__(self):
        for field in fields(self):
            if field.name in {"line_polarity", "max_trace_vertices"}:
                continue
            value = getattr(self, field.name)
            if isinstance(value, bool) or not math.isfinite(value) or value <= 0:
                raise ValueError("{} must be finite and positive".format(field.name))
        if self.line_polarity not in {"dark", "light"}:
            raise ValueError("line_polarity must be dark or light")
        if (
            not isinstance(self.max_trace_vertices, int)
            or isinstance(self.max_trace_vertices, bool)
            or not 20 <= self.max_trace_vertices <= 10000
        ):
            raise ValueError("max_trace_vertices must be an integer in [20, 10000]")
        rows = math.ceil(self.bev_forward_m / self.resolution_m) + 1
        cols = math.ceil(2 * self.bev_half_width_m / self.resolution_m) + 1
        if rows < 4 or cols < 4 or rows * cols > 1_000_000:
            raise ValueError(
                "BEV grid must have at least 4 rows/columns and <=1M cells"
            )
        if self.background_width_m / self.resolution_m > 201:
            raise ValueError("Background morphology kernel is too large")
        if self.initial_anchor_m > self.bev_forward_m:
            raise ValueError("initial_anchor_m must be within the BEV")
        if self.ambiguity_margin_m >= self.association_gate_m:
            raise ValueError("ambiguity margin must be smaller than association gate")
        if self.support_length_m / self.support_spacing_m > 128:
            raise ValueError("association support must contain at most 129 points")


def transform_points(points, matrix):
    points = np.asarray(points, dtype=float)
    homogeneous = np.c_[points, np.ones(len(points))] @ matrix.T
    with np.errstate(divide="ignore", invalid="ignore"):
        return homogeneous[:, :2] / homogeneous[:, 2:3]


def thinning(mask):
    """Zhang–Suen thinning; no closing or dilation can join separate lines."""
    image = np.pad((mask > 0).astype(np.uint8), 1)
    for _ in range(128):
        changed = False
        for phase in (0, 1):
            p = [
                image[:-2, 1:-1],
                image[:-2, 2:],
                image[1:-1, 2:],
                image[2:, 2:],
                image[2:, 1:-1],
                image[2:, :-2],
                image[1:-1, :-2],
                image[:-2, :-2],
            ]
            count = sum(p)
            transitions = sum((p[i] == 0) & (p[(i + 1) % 8] != 0) for i in range(8))
            a, b = (
                (p[0] * p[2] * p[4], p[2] * p[4] * p[6])
                if phase == 0
                else (p[0] * p[2] * p[6], p[0] * p[4] * p[6])
            )
            remove = (
                (image[1:-1, 1:-1] != 0)
                & (count >= 2)
                & (count <= 6)
                & (transitions == 1)
                & (a == 0)
                & (b == 0)
            )
            if remove.any():
                image[1:-1, 1:-1][remove] = 0
                changed = True
        if not changed:
            break
    return image[1:-1, 1:-1]


class BirdEye:
    def __init__(self, width, height, ground_to_image, config):
        self.config = config
        self.size = (width, height)
        self.h = np.asarray(ground_to_image, dtype=float).copy()
        if (
            self.h.shape != (3, 3)
            or not np.isfinite(self.h).all()
            or np.linalg.matrix_rank(self.h) != 3
            or np.linalg.cond(self.h) > 1e12
        ):
            raise ValueError("ground_to_image must be a finite nonsingular 3x3 matrix")
        self.inv = np.linalg.inv(self.h)
        rows = math.ceil(config.bev_forward_m / config.resolution_m) + 1
        cols = math.ceil(2 * config.bev_half_width_m / config.resolution_m) + 1
        self.row_step_m = config.bev_forward_m / (rows - 1)
        self.col_step_m = 2 * config.bev_half_width_m / (cols - 1)
        rr, cc = np.mgrid[:rows, :cols]
        ground = self.metric(np.c_[cc.ravel(), rr.ravel()])
        self.ground = ground.reshape(rows, cols, 2)
        pixels = self.pixels(ground)
        depth = np.c_[ground, np.ones(len(ground))] @ self.h[2]
        self.valid = (
            (depth > 1e-6 * np.linalg.norm(self.h[2]))
            & np.isfinite(pixels).all(axis=1)
            & (pixels[:, 0] >= 1)
            & (pixels[:, 0] < width - 1)
            & (pixels[:, 1] >= 1)
            & (pixels[:, 1] < height - 1)
        ).reshape(rows, cols)
        # Do not pass inf/NaN maps into OpenCV even at invalid grid positions.
        pixels[~self.valid.ravel()] = -1
        self.mx = pixels[:, 0].reshape(rows, cols).astype(np.float32)
        self.my = pixels[:, 1].reshape(rows, cols).astype(np.float32)
        kernel_size = max(3, round(config.background_width_m / config.resolution_m))
        self.kernel = np.ones((kernel_size | 1, kernel_size | 1), np.uint8)

    def metric(self, pixels):
        pixels = np.asarray(pixels)
        return np.c_[
            self.config.bev_forward_m - pixels[:, 1] * self.row_step_m,
            self.config.bev_half_width_m - pixels[:, 0] * self.col_step_m,
        ]

    def pixels(self, metric):
        return transform_points(metric, self.h)

    def extract(self, rgb):
        light = self.config.line_polarity == "light"
        background_value = 0 if light else 255
        bird = cv2.remap(
            rgb, self.mx, self.my, cv2.INTER_LINEAR, borderValue=(background_value,) * 3
        )
        gray = cv2.cvtColor(bird, cv2.COLOR_RGB2GRAY)
        background = cv2.morphologyEx(
            gray, cv2.MORPH_OPEN if light else cv2.MORPH_CLOSE, self.kernel
        ).astype(float)
        if light:
            floor = float(np.percentile(gray[self.valid], 30))
            threshold = min(230, floor + max(25, (255 - floor) * 0.30))
            contrast = gray.astype(float) - background
            mask = (gray > threshold) & (
                contrast > np.maximum(10, (255 - background) * 0.12)
            )
        else:
            threshold = max(25, float(np.percentile(gray[self.valid], 70)) * 0.72)
            contrast = background - gray
            mask = (gray < threshold) & (contrast > np.maximum(10, background * 0.18))
        neutral = bird.max(axis=2).astype(int) - bird.min(axis=2) < 50
        skeleton = thinning(mask & neutral & self.valid)
        count, labels, stats, _ = cv2.connectedComponentsWithStats(skeleton, 8)
        components = []
        minimum_pixels = max(
            4,
            math.ceil(
                self.config.minimum_component_length_m
                / max(self.row_step_m, self.col_step_m)
            ),
        )
        for label in range(1, count):
            if stats[label, cv2.CC_STAT_AREA] < minimum_pixels:
                continue
            row, col = np.where(labels == label)
            pixels = np.c_[col, row]
            components.append((pixels, self.metric(pixels)))
        return components


def principal_direction(points, reference):
    _, _, vectors = np.linalg.svd(points - points.mean(axis=0), full_matrices=False)
    direction = vectors[0]
    return direction if np.dot(direction, reference) >= 0 else -direction


def trace_component(pixels, metric, index, direction, max_vertices=2000):
    """Trace connected skeleton neighbours, preserving route order around bends."""
    lookup = {tuple(p): i for i, p in enumerate(pixels)}
    adjacency = []
    for col, row in pixels:
        neighbors = []
        for dx, dy in (
            (-1, -1),
            (0, -1),
            (1, -1),
            (-1, 0),
            (1, 0),
            (-1, 1),
            (0, 1),
            (1, 1),
        ):
            neighbor = lookup.get((col + dx, row + dy))
            if neighbor is None:
                continue
            if dx and dy and ((col + dx, row) in lookup or (col, row + dy) in lookup):
                continue
            neighbors.append(neighbor)
        adjacency.append(neighbors)

    def continuation(vertex, blocked, depth=6):
        if depth == 0:
            return 0
        choices = [i for i in adjacency[vertex] if i not in blocked]
        return 1 + max(
            (continuation(i, blocked | {i}, depth - 1) for i in choices), default=0
        )

    def walk(initial_direction):
        current, heading, visited, route = (
            index,
            initial_direction.copy(),
            {index},
            [index],
        )
        for _ in range(max_vertices):
            candidates = [i for i in adjacency[current] if i not in visited]
            if not candidates:
                break
            vectors = metric[candidates] - metric[current]
            scores = (vectors @ heading) / np.linalg.norm(vectors, axis=1)
            priority = scores.copy()
            if len(candidates) > 1:
                priority += np.array(
                    [0.25 * continuation(i, visited | {i}) for i in candidates]
                )
            chosen = int(np.argmax(priority))
            if scores[chosen] < -0.25:
                break
            current = candidates[chosen]
            visited.add(current)
            route.append(current)
            if len(route) > 4:
                heading = metric[current] - metric[route[-5]]
                heading /= max(np.linalg.norm(heading), 1e-6)
        return route

    backward, forward = walk(-direction), walk(direction)
    path = metric[backward[:0:-1] + forward]
    if len(path) >= 7:
        endpoints = path[[0, -1]].copy()
        path = np.column_stack(
            [
                np.convolve(
                    np.pad(path[:, axis], (2, 2), mode="edge"),
                    np.ones(5) / 5,
                    mode="valid",
                )
                for axis in range(2)
            ]
        )
        path[[0, -1]] = endpoints
    indices = np.unique(np.r_[np.arange(0, len(path), 2), len(path) - 1])
    return path[indices]


@dataclass
class Track:
    path: Optional[np.ndarray]
    confidence: float
    status: str
    reason: str
    predicted: bool = False


class TargetTracker:
    def __init__(self, config=VisionConfig()):
        self.config = config
        self.path = None
        self.missing_s = 0.0
        self.camera = None
        self.initialized = False
        self.components = []

    def advance(self, translation, yaw):
        """Move old points into new body frame; translation is in OLD body axes."""
        translation = np.asarray(translation, dtype=float)
        if (
            translation.shape != (2,)
            or not np.isfinite(translation).all()
            or not math.isfinite(yaw)
        ):
            raise ValueError("motion increment must be a finite 2D translation and yaw")
        rotation = np.array(
            [[math.cos(yaw), -math.sin(yaw)], [math.sin(yaw), math.cos(yaw)]]
        )
        if self.path is not None:
            arc = np.r_[
                0, np.cumsum(np.linalg.norm(np.diff(self.path, axis=0), axis=1))
            ]
            self.path = (self.path - translation) @ rotation
            # Search only the next ordered prefix: a later return leg may be
            # spatially closer without having been reached along the route.
            count = max(
                1,
                int(
                    np.searchsorted(
                        arc,
                        self.config.progress_search_m + np.linalg.norm(translation),
                        side="right",
                    )
                ),
            )
            near = int(np.argmin(np.linalg.norm(self.path[:count], axis=1)))
            self.path = self.path[max(0, near - 2) :]

    def _missing(self, dt, reason):
        self.missing_s += dt
        if (
            self.path is not None
            and len(self.path) >= 4
            and self.missing_s <= self.config.memory_s
        ):
            return Track(
                self.path.copy(),
                0.65 * math.exp(-self.missing_s / self.config.memory_s),
                "TRACK",
                reason + "; bounded odometry prediction",
                True,
            )
        return Track(None, 0.0, "LOST", reason)

    def invalidate_prediction(self):
        """Retain target identity but revoke stale geometry's permission to drive.

        Call this on external transport/TF/decode faults as well. Only a fresh
        successful association to the original target can restore prediction.
        """
        self.missing_s = max(self.missing_s, self.config.memory_s + 1.0)

    def _error(self, reason):
        self.invalidate_prediction()
        return Track(None, 0.0, "ERROR", reason)

    def observe(self, rgb, ground_to_image, dt):
        try:
            valid_dt = not isinstance(dt, bool) and math.isfinite(dt) and dt > 0
        except (TypeError, ValueError):
            valid_dt = False
        if not valid_dt:
            return self._error("dt must be finite and positive")
        if (
            not isinstance(rgb, np.ndarray)
            or rgb.dtype != np.uint8
            or rgb.ndim != 3
            or rgb.shape[2] != 3
            or min(rgb.shape[:2]) < 4
        ):
            return self._error("expected HxWx3 uint8 rectified RGB")
        height, width = rgb.shape[:2]
        try:
            if (
                self.camera is None
                or self.camera.size != (width, height)
                or not np.array_equal(self.camera.h, ground_to_image)
            ):
                self.camera = BirdEye(width, height, ground_to_image, self.config)
        except (ValueError, TypeError, np.linalg.LinAlgError) as error:
            return self._error("invalid ground calibration: " + str(error))
        if not self.camera.valid.any():
            return self._error("calibration has no visible forward ground")
        self.components = self.camera.extract(rgb)
        reference = np.array([1.0, 0.0])
        anchor, support = None, None
        previous = self.path
        if previous is not None and len(previous) > 3:
            projected = self.camera.pixels(previous)
            in_view = (
                (previous[:, 0] > 0)
                & (previous @ self.camera.h[2, :2] + self.camera.h[2, 2] > 0)
                & (np.linalg.norm(previous, axis=1) < self.config.association_range_m)
                & np.isfinite(projected).all(axis=1)
                & (projected[:, 0] >= 2)
                & (projected[:, 0] < width - 2)
                & (projected[:, 1] >= 2)
                & (projected[:, 1] < height - 2)
            )
            usable = previous[in_view]
            if len(usable) >= 2:
                arc = np.r_[
                    0, np.cumsum(np.linalg.norm(np.diff(usable, axis=0), axis=1))
                ]
                anchor_index = min(
                    len(usable) - 1,
                    int(
                        np.searchsorted(
                            arc, min(self.config.anchor_lookahead_m, arc[-1] * 0.5)
                        )
                    ),
                )
                anchor = usable[anchor_index]
                distances = np.arange(
                    0,
                    min(arc[-1], self.config.support_length_m) + 1e-8,
                    self.config.support_spacing_m,
                )
                support = np.column_stack(
                    [np.interp(distances, arc, usable[:, axis]) for axis in range(2)]
                )
                reference = (
                    usable[min(anchor_index + 3, len(usable) - 1)]
                    - usable[max(0, anchor_index - 3)]
                )
                norm = np.linalg.norm(reference)
                reference = reference / norm if norm > 1e-6 else np.array([1.0, 0.0])
        if anchor is None:
            if self.initialized:
                return self._missing(
                    dt, "previous target has no usable visible support"
                )
            anchor = np.array([self.config.initial_anchor_m, 0.0])
        matches = []
        for pixels, metric in self.components:
            distance = np.linalg.norm(metric - anchor, axis=1)
            index = int(np.argmin(distance))
            local = metric[
                np.linalg.norm(metric - metric[index], axis=1)
                < self.config.local_direction_radius_m
            ]
            if len(local) < 4:
                continue
            direction = principal_direction(local, reference)
            if not self.initialized:
                direction = principal_direction(local, metric[index])
                score = self.initial_connection_cost(metric[index], direction)
            else:
                fit = float(
                    np.median(
                        np.linalg.norm(support[:, None] - metric[None], axis=2).min(
                            axis=1
                        )
                    )
                )
                score = fit + self.config.heading_weight_m * (
                    1 - float(np.dot(direction, reference))
                )
            matches.append((score, pixels, metric, index, direction))
        matches.sort(key=lambda item: item[0])
        allowed = (
            self.config.association_gate_m
            if self.initialized
            else self.config.initial_gate_m
        )
        if not matches or matches[0][0] > allowed:
            return self._missing(dt, "target association gate failed")
        if (
            len(matches) > 1
            and matches[1][0] - matches[0][0] < self.config.ambiguity_margin_m
        ):
            self.missing_s += dt
            return Track(
                None, 0.0, "AMBIGUOUS", "nearby candidates are not distinguishable"
            )
        score, pixels, metric, index, direction = matches[0]
        path = trace_component(
            pixels, metric, index, direction, self.config.max_trace_vertices
        )
        length = np.linalg.norm(np.diff(path, axis=0), axis=1).sum()
        if len(path) < 4 or length < self.config.minimum_path_length_m:
            self.missing_s += dt
            return Track(None, 0.0, "LOST", "insufficient connected target geometry")
        self.path, self.initialized, self.missing_s = path, True, 0.0
        confidence = float(np.clip(0.98 - 0.5 * score / allowed, 0.40, 0.98))
        return Track(
            path.copy(),
            confidence,
            "TRACK",
            "temporal identity and skeleton connectivity verified",
        )

    def initial_connection_cost(self, point, direction):
        """Feasible forward straight+arc connection from the known start tangent."""
        x, y = point
        angle = math.atan2(direction[1], direction[0])
        sine, cosine = abs(math.sin(angle)), math.cos(angle)
        if sine < 0.08:
            residual = abs(y) + (self.config.minimum_radius_m if cosine < 0 else 0)
        else:
            radius = max(self.config.minimum_radius_m, abs(y) / max(1 - cosine, 1e-6))
            lead = x - radius * sine
            expected_y = math.copysign(radius * (1 - cosine), angle)
            residual = abs(y - expected_y) + max(0.0, -lead)
        return float(residual + 0.04 * np.linalg.norm(point))
