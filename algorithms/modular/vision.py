"""Metric image geometry, narrow-line skeletons and gated temporal association."""

from dataclasses import dataclass
import math

import cv2
import numpy as np


def transform_points(points, matrix):
    p = np.c_[np.asarray(points), np.ones(len(points))] @ matrix.T
    return p[:, :2] / p[:, 2:3]


def thinning(mask):
    """Vectorized two-subiteration Zhang–Suen thinning; never closes line gaps."""
    image = np.pad((mask > 0).astype(np.uint8), 1)
    for _ in range(24):
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
    resolution = 0.025
    forward = 6.0
    half_width = 3.0

    def __init__(self, calibration):
        self.size = (calibration.width, calibration.height)
        self.h = np.array(calibration.ground_to_image, dtype=float)
        self.inv = np.linalg.inv(self.h)
        rows, cols = np.mgrid[:241, :241]
        ground = self.metric(np.c_[cols.ravel(), rows.ravel()])
        pixels = transform_points(ground, self.h)
        homogeneous = np.c_[ground, np.ones(len(ground))] @ self.h.T
        valid = (
            (homogeneous[:, 2] > 0.05)
            & (pixels[:, 0] >= 1)
            & (pixels[:, 0] < calibration.width - 1)
            & (pixels[:, 1] >= 1)
            & (pixels[:, 1] < calibration.height - 1)
        )
        self.valid = valid.reshape(rows.shape)
        self.mx = pixels[:, 0].reshape(rows.shape).astype(np.float32)
        self.my = pixels[:, 1].reshape(rows.shape).astype(np.float32)

    def metric(self, pixels):
        pixels = np.asarray(pixels)
        return np.c_[
            self.forward - pixels[:, 1] * self.resolution,
            self.half_width - pixels[:, 0] * self.resolution,
        ]

    def pixels(self, metric):
        return transform_points(metric, self.h)

    def extract(self, rgb, hint):
        bird = cv2.remap(
            rgb, self.mx, self.my, cv2.INTER_LINEAR, borderValue=(255, 255, 255)
        )
        gray = cv2.cvtColor(bird, cv2.COLOR_RGB2GRAY)
        background = cv2.morphologyEx(
            gray, cv2.MORPH_CLOSE, np.ones((15, 15), np.uint8)
        )
        contrast = background.astype(float) - gray
        threshold = max(25, float(np.percentile(gray[self.valid], 70)) * 0.72)
        neutral = bird.max(axis=2).astype(int) - bird.min(axis=2) < 50
        mask = (
            self.valid
            & neutral
            & (gray < threshold)
            & (contrast > np.maximum(10, background * 0.18))
        )
        hsv = cv2.cvtColor(bird, cv2.COLOR_RGB2HSV)
        reference = cv2.cvtColor(np.uint8([[hint.marker_rgb]]), cv2.COLOR_RGB2HSV)[0, 0]
        hue_distance = np.abs(hsv[:, :, 0].astype(int) - int(reference[0]))
        marker = (
            self.valid
            & (np.minimum(hue_distance, 180 - hue_distance) < 12)
            & (hsv[:, :, 1] > max(65, reference[1] * 0.55))
            & (hsv[:, :, 2] > 45)
        )
        # Antialiased colored glyph edges must not become line junctions in
        # shadow. Expanding only the exclusion mask cannot join dark branches.
        mask &= ~cv2.dilate(marker.astype(np.uint8), np.ones((3, 3), np.uint8)).astype(
            bool
        )
        skeleton = thinning(mask)
        count, labels, stats, _ = cv2.connectedComponentsWithStats(skeleton, 8)
        components = []
        for i in range(1, count):
            if stats[i, cv2.CC_STAT_AREA] < 12:
                continue
            row, col = np.where(labels == i)
            pixel = np.c_[col, row]
            components.append((pixel, self.metric(pixel)))
        row, col = np.where(marker)
        marker_points = self.metric(np.c_[col, row])
        orange = (
            self.valid
            & (hsv[:, :, 0] >= 10)
            & (hsv[:, :, 0] <= 27)
            & (hsv[:, :, 1] > 100)
            & (hsv[:, :, 2] > 65)
        )
        count, labels, stats, _ = cv2.connectedComponentsWithStats(
            orange.astype(np.uint8), 8
        )
        ends = []
        for i in range(1, count):
            if stats[i, cv2.CC_STAT_AREA] >= 8:
                row, col = np.where(labels == i)
                ends.append(self.metric(np.c_[col, row]).mean(axis=0))
        return components, marker_points, ends


def principal_direction(points, reference=np.array([1.0, 0.0])):
    _, _, vectors = np.linalg.svd(points - points.mean(axis=0), full_matrices=False)
    direction = vectors[0]
    return direction if np.dot(direction, reference) >= 0 else -direction


def trace_component(pixels, metric, index, direction, resolution=0.025):
    """Walk adjacent skeleton vertices; a nearby disconnected line is unreachable."""
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
            # A diagonal across an existing orthogonal corner creates a tiny
            # artificial cycle; following its spare vertex would end the walk.
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
        for _ in range(700):
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
    indices = backward[:0:-1] + forward
    path = metric[indices]
    # Local averaging reduces one-pixel steering jitter without blending branches.
    if len(path) >= 7:
        path = np.column_stack(
            [
                np.convolve(
                    np.pad(path[:, i], (2, 2), mode="edge"),
                    np.ones(5) / 5,
                    mode="valid",
                )
                for i in range(2)
            ]
        )
    return path[::2]


@dataclass
class Track:
    path: np.ndarray | None
    candidates: list
    confidence: float
    status: str
    reason: str
    predicted: bool = False


class TargetTracker:
    def __init__(
        self, temporal=True, topology=True, association_gate=0.16, memory_s=0.45
    ):
        self.temporal, self.topology = temporal, topology
        self.gate, self.memory_s = association_gate, memory_s
        self.path = None
        self.start = None
        self.missing_s = 0.0
        self.camera = None
        self.initialized = False
        self.end = None

    def advance(self, translation, yaw):
        rotation = np.array(
            [[math.cos(yaw), -math.sin(yaw)], [math.sin(yaw), math.cos(yaw)]]
        )
        if self.path is not None:
            self.path = (self.path - translation) @ rotation
            # Drop points safely behind the rear axle, preserving route ordering.
            near = int(np.argmin(np.linalg.norm(self.path, axis=1)))
            self.path = self.path[max(0, near - 2) :]
        if self.start is not None:
            self.start = (self.start - translation) @ rotation
        if self.end is not None:
            self.end = (self.end - translation) @ rotation

    def observe(self, observation, dt):
        if observation.calibration is None:
            return Track(
                None,
                [],
                0,
                "ERROR",
                "米制视觉算法需要相机标定；可对无标定图像使用扫描线基线",
            )
        if (
            self.camera is None
            or self.camera.size != (observation.width, observation.height)
            or not np.array_equal(
                self.camera.h, observation.calibration.ground_to_image
            )
        ):
            self.camera = BirdEye(observation.calibration)
        if not self.camera.valid.any():
            return Track(None, [], 0, "ERROR", "相机标定没有有效的前方地面视野")
        components, marker, ends = self.camera.extract(
            observation.rgb(), observation.task_hint
        )
        candidates = [
            self.camera.pixels(p[:: max(1, len(p) // 80)]).tolist()
            for _, p in components[:20]
        ]
        reference = np.array([1.0, 0.0])
        anchor = None
        previous = self.path if self.temporal else None
        support = None
        if previous is not None and len(previous) > 3:
            usable = previous[
                (previous[:, 0] > 0.65) & (np.linalg.norm(previous, axis=1) < 2.5)
            ]
            if len(usable):
                anchor_index = min(8, len(usable) // 2)
                anchor = usable[anchor_index]
                support = usable[:30:3]
                reference = (
                    usable[min(anchor_index + 4, len(usable) - 1)]
                    - usable[max(0, anchor_index - 4)]
                )
                if np.linalg.norm(reference) < 0.02:
                    reference = np.array([1.0, 0.0])
                reference /= np.linalg.norm(reference)
        hint = observation.task_hint
        marker_initialization = hint.kind == "marker" and (
            not self.initialized or (not self.temporal and len(marker) >= 8)
        )
        if anchor is None and (not self.initialized or marker_initialization):
            if hint.kind == "marker" and len(marker) >= 8:
                reference = principal_direction(marker)
                center = np.median(marker, axis=0)
                projection = (marker - center) @ reference
                anchor = center + reference * (np.percentile(projection, 97) + 0.06)
                self.start = center
            elif hint.kind in {"point", "region"}:
                point = (
                    hint.point_px
                    if hint.kind == "point"
                    else [
                        (hint.region_px[0] + hint.region_px[2]) / 2,
                        (hint.region_px[1] + hint.region_px[3]) / 2,
                    ]
                )
                anchor = transform_points([point], self.camera.inv)[0]
            elif len(components) > 1:
                return Track(
                    None,
                    candidates,
                    0,
                    "AMBIGUOUS",
                    "多个候选缺少可辨识的目标初始化提示",
                )
            elif hint.kind == "marker":
                return Track(None, candidates, 0, "UNINITIALIZED", "等待可见起点标记")
        if anchor is None:
            anchor = np.array([0.75, 0.0])
        matches = []
        for pixels, metric in components:
            distance = np.linalg.norm(metric - anchor, axis=1)
            index = int(np.argmin(distance))
            local = metric[np.linalg.norm(metric - metric[index], axis=1) < 0.23]
            if len(local) < 4:
                continue
            direction = principal_direction(local, reference)
            fit = (
                float(
                    np.median(
                        np.linalg.norm(support[:, None] - metric[None], axis=2).min(
                            axis=1
                        )
                    )
                )
                if support is not None
                else float(distance[index])
            )
            score = fit + 0.08 * (1 - float(np.dot(direction, reference)))
            matches.append((score, pixels, metric, index, direction))
        matches.sort(key=lambda item: item[0])
        allowed = (
            0.42
            if marker_initialization
            else 0.5
            if not self.initialized
            else self.gate
        )
        if not self.temporal and self.initialized and not marker_initialization:
            allowed = 1.2
        if not matches or matches[0][0] > allowed:
            self.missing_s += dt
            if (
                self.end is not None
                and previous is not None
                and np.linalg.norm(self.end) < 1.2
                and self.missing_s < 3
            ):
                tail = previous[previous[:, 0] > -0.1]
                if len(tail) < 2:
                    tail = np.array([[0.0, 0.0], self.end])
                return Track(
                    tail,
                    candidates,
                    0.75,
                    "TRACK",
                    "沿已观测终点进入相机近端盲区；有界运动预测",
                    True,
                )
            if (
                previous is not None
                and len(previous) >= 4
                and self.missing_s <= self.memory_s
            ):
                return Track(
                    previous,
                    candidates,
                    0.65 * math.exp(-self.missing_s / self.memory_s),
                    "TRACK",
                    "短时缺失：仅沿已观测目标预测，置信度随时间衰减",
                    True,
                )
            return Track(
                None, candidates, 0, "LOST", "目标关联门限未通过，停车保留身份"
            )
        if len(matches) > 1 and matches[1][0] - matches[0][0] < 0.035:
            return Track(
                None,
                candidates,
                0,
                "AMBIGUOUS",
                "两个目标候选的关联代价接近，停止而不换线",
            )
        score, pixels, metric, index, direction = matches[0]
        if self.topology:
            path = trace_component(pixels, metric, index, direction)
        else:
            # Explicit ablation: row-wise centroids can join unrelated branches.
            cloud = np.concatenate([p for _, p in components])
            path = np.array(
                [
                    cloud[(cloud[:, 0] >= x) & (cloud[:, 0] < x + 0.08)].mean(axis=0)
                    for x in np.arange(0.5, 4, 0.08)
                    if np.any((cloud[:, 0] >= x) & (cloud[:, 0] < x + 0.08))
                ]
            )
        if len(path) < 4 or np.linalg.norm(path[-1] - path[0]) < 0.15:
            self.missing_s += dt
            return Track(None, candidates, 0, "LOST", "可见目标结构不足，等待恢复")
        self.path, self.initialized, self.missing_s = path, True, 0
        for endpoint in ends:
            if np.linalg.norm(path[-1] - endpoint) < 0.25:
                self.end = endpoint
                path = np.vstack([path, endpoint])
                self.path = path
        confidence = float(np.clip(0.98 - score * 0.8, 0.4, 0.98))
        status = (
            "ACQUIRE" if self.start is not None and self.start[0] > 0.15 else "TRACK"
        )
        return Track(path, candidates, confidence, status, "时序身份与局部连通性已核验")
