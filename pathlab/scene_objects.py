"""Small metric solids, deterministic placement, and a CPU depth-buffer renderer."""

from __future__ import annotations

import math
from dataclasses import dataclass

import cv2
import numpy as np

from .config import ObjectScatter, Pose, Scene, SceneObject


def _world(points: np.ndarray, obj: SceneObject) -> np.ndarray:
    result = np.asarray(points, dtype=float).copy()
    c, s = math.cos(obj.yaw_rad), math.sin(obj.yaw_rad)
    result[:, :2] = result[:, :2] @ np.array([[c, s], [-s, c]]) + [obj.x_m, obj.y_m]
    return result


def object_footprint(obj: SceneObject) -> np.ndarray:
    """Conservative support footprint, shared by display and collision scoring."""
    # Cones have square rubber bases; barrels have circular bases.
    if obj.kind == "cylinder":
        angle = np.arange(16) * 2 * math.pi / 16
        local = np.column_stack(
            (np.cos(angle) * obj.length_m / 2, np.sin(angle) * obj.width_m / 2)
        )
    else:
        local = np.array([[-1, -1], [1, -1], [1, 1], [-1, 1]]) * [
            obj.length_m / 2,
            obj.width_m / 2,
        ]
    return _world(local, obj)


def scatter_objects(scene: Scene, options: ObjectScatter) -> list[SceneObject]:
    """Place clutter beside the whole route, never across its driving corridor."""
    rng = np.random.default_rng(np.random.SeedSequence([scene.seed, 7823]))
    path = np.asarray(scene.target_path)
    lines = np.concatenate([path, *[np.asarray(line) for line in scene.distractors]])
    existing = [obj for obj in scene.objects if obj.enabled]
    result: list[SceneObject] = []
    dimensions = {
        "cone": (0.34, 0.34, 0.52),
        "box": (0.5, 0.42, 0.46),
        "barrier": (0.85, 0.3, 0.55),
        "cylinder": (0.4, 0.4, 0.65),
    }
    colors = {
        "cone": (232, 108, 38),
        "box": (162, 124, 83),
        "barrier": (230, 179, 52),
        "cylinder": (67, 124, 158),
    }
    for _ in range(max(1, options.count) * 150):
        if len(result) >= options.count:
            break
        kind = str(rng.choice(options.kinds))
        size = np.asarray(dimensions[kind]) * options.scale * rng.uniform(0.85, 1.15)
        radius = float(np.linalg.norm(size[:2]) / 2)
        # Two props close to the entry make its perspective legible immediately.
        entry_prop = len(result) < 2
        entry_limit = min(60, len(path) - 1)
        index = (
            int(rng.integers(min(8, entry_limit - 1), entry_limit))
            if entry_prop
            else int(rng.integers(0, len(path) - 1))
        )
        tangent = path[index + 1] - path[index]
        tangent /= np.linalg.norm(tangent)
        normal = np.array([-tangent[1], tangent[0]]) * rng.choice([-1, 1])
        distance = (
            options.clearance_m
            + radius
            + rng.uniform(
                0, min(0.5, options.spread_m) if entry_prop else options.spread_m
            )
        )
        position = path[index] + normal * distance
        if (
            np.max(np.abs(position)) > 38
            or np.linalg.norm(
                position - [scene.initial_pose.x_m, scene.initial_pose.y_m]
            )
            < radius + 1
        ):
            continue
        if np.linalg.norm(lines - position, axis=1).min() < radius + max(
            options.clearance_m, scene.vehicle.width_m / 2 + 0.12
        ):
            continue
        if any(
            np.linalg.norm(position - [other.x_m, other.y_m])
            < radius + math.hypot(other.length_m, other.width_m) / 2 + 0.15
            for other in existing + result
        ):
            continue
        result.append(
            SceneObject(
                kind=kind,
                x_m=position[0],
                y_m=position[1],
                yaw_rad=float(rng.uniform(-math.pi, math.pi)),
                length_m=size[0],
                width_m=size[1],
                height_m=size[2],
                color_rgb=colors[kind],
            )
        )
    if len(result) != options.count:
        raise ValueError("当前路线周边放不下指定数量的物件，请减少数量或增大散布范围")
    return result


@dataclass
class Face:
    vertices: np.ndarray
    color: tuple[int, int, int]


def object_mesh(obj: SceneObject) -> list[Face]:
    faces: list[Face] = []
    color = obj.color_rgb
    white, dark = (226, 224, 211), (50, 54, 54)

    def face(vertices, tint):
        faces.append(Face(_world(np.asarray(vertices), obj), tint))

    def box(x, y, z, length, width, height, tint):
        vertices = np.array(
            [
                [x + dx * length / 2, y + dy * width / 2, z + dz * height / 2]
                for dz in [-1, 1]
                for dx, dy in [(-1, -1), (1, -1), (1, 1), (-1, 1)]
            ]
        )
        for indices in [
            (0, 4, 5, 1),
            (1, 5, 6, 2),
            (2, 6, 7, 3),
            (3, 7, 4, 0),
            (4, 7, 6, 5),
        ]:
            face(vertices[list(indices)], tint)

    length, width, height = obj.length_m, obj.width_m, obj.height_m
    if obj.kind == "box":
        box(0, 0, height / 2, length, width, height, color)
        # Packing tape is geometry on the lid, so it follows perspective.
        box(0, 0, height + 0.0005, length * 0.16, width, 0.001, (192, 158, 108))
    elif obj.kind == "barrier":
        for sign in [-1, 1]:
            box(
                sign * length * 0.35,
                0,
                height * 0.05,
                length * 0.2,
                width,
                height * 0.1,
                dark,
            )
            box(
                sign * length * 0.35,
                0,
                height * 0.42,
                length * 0.07,
                width * 0.3,
                height * 0.7,
                dark,
            )
        box(0, 0, height * 0.68, length, width * 0.4, height * 0.64, color)
        for x in [-0.3, 0, 0.3]:
            box(
                x * length,
                0,
                height * 0.68,
                length * 0.1,
                width * 0.405,
                height * 0.63,
                white,
            )
    else:
        is_cone = obj.kind == "cone"
        if is_cone:
            box(0, 0, height * 0.04, length, width, height * 0.08, dark)
        levels = (
            [(0.08, 0.87), (0.38, 0.61), (0.56, 0.46), (0.98, 0.06)]
            if is_cone
            else [(0, 1), (0.36, 1), (0.52, 1), (1, 1)]
        )
        rings = []
        for elevation, radius in levels:
            angle = np.arange(16) * math.pi / 8
            rings.append(
                np.column_stack(
                    (
                        np.cos(angle) * length / 2 * radius,
                        np.sin(angle) * width / 2 * radius,
                        np.full(16, elevation * height),
                    )
                )
            )
        for level, (lower, upper) in enumerate(zip(rings, rings[1:])):
            for i in range(16):
                j = (i + 1) % 16
                face(
                    [lower[j], lower[i], upper[i], upper[j]],
                    white if level == 1 else color,
                )
        face(rings[-1][::-1], color)
    return faces


class ObjectRenderer:
    """Perspective-correct visibility without graphics drivers or WebGL."""

    def __init__(self, scene: Scene, camera):
        self.scene, self.camera = scene, camera
        self.objects = [obj for obj in scene.objects if obj.enabled]
        self.faces = [face for obj in self.objects for face in object_mesh(obj)]
        a = scene.appearance
        self.sun = np.array(
            [
                math.cos(a.sun_azimuth_rad) * math.cos(a.sun_elevation_rad),
                math.sin(a.sun_azimuth_rad) * math.cos(a.sun_elevation_rad),
                math.sin(a.sun_elevation_rad),
            ]
        )
        self.shaded_faces = []
        self.normals = []
        self.centers = []
        for face in self.faces:
            normal = np.cross(
                face.vertices[1] - face.vertices[0], face.vertices[2] - face.vertices[0]
            )
            normal /= max(1e-9, float(np.linalg.norm(normal)))
            # Mesh faces are consistently clockwise as viewed from outside.
            light = 0.66 + 0.34 * max(0, float(-normal @ self.sun))
            self.shaded_faces.append(
                np.clip(np.asarray(face.color) * light * a.illumination, 0, 255).astype(
                    np.uint8
                )
            )
            self.normals.append(-normal)
            self.centers.append(face.vertices.mean(axis=0))
        self.normals = np.asarray(self.normals)
        self.centers = np.asarray(self.centers)
        self.vertices = (
            np.concatenate([face.vertices for face in self.faces])
            if self.faces
            else np.empty((0, 3))
        )
        self.offsets = np.r_[0, np.cumsum([len(face.vertices) for face in self.faces])]

    def cast_shadows(
        self, raster: np.ndarray, origin: np.ndarray, scale: float
    ) -> None:
        if not self.scene.appearance.object_shadows:
            return
        for obj in self.objects:
            vertices = np.concatenate([face.vertices for face in object_mesh(obj)])
            projection = vertices[:, :2] - vertices[:, 2:3] * self.sun[:2] / self.sun[2]
            polygon = cv2.convexHull(
                np.rint((projection - origin) * scale).astype(np.int32)
            )
            x, y, width, height = cv2.boundingRect(polygon)
            margin = max(2, round(scale * 0.07))
            x0, y0 = max(0, x - margin), max(0, y - margin)
            x1, y1 = (
                min(raster.shape[1], x + width + margin),
                min(raster.shape[0], y + height + margin),
            )
            if x0 >= x1 or y0 >= y1:
                continue
            mask = np.zeros((y1 - y0, x1 - x0), np.uint8)
            cv2.fillConvexPoly(mask, polygon - [x0, y0], 255, cv2.LINE_AA)
            mask = cv2.GaussianBlur(mask, (0, 0), max(0.6, scale * 0.025))
            shade = 1 - mask.astype(np.float32) / 255 * 0.24
            raster[y0:y1, x0:x1] = (raster[y0:y1, x0:x1] * shade[:, :, None]).astype(
                np.uint8
            )

    @staticmethod
    def _clip(vertices: np.ndarray, near: float = 0.04) -> np.ndarray:
        """Clip in camera coordinates; close objects must not explode on screen."""
        clipped = []
        for first, second in zip(vertices, np.roll(vertices, -1, axis=0)):
            inside_first, inside_second = first[2] >= near, second[2] >= near
            if inside_first:
                clipped.append(first)
            if inside_first != inside_second:
                clipped.append(
                    first
                    + (second - first) * (near - first[2]) / (second[2] - first[2])
                )
        return np.asarray(clipped)

    def render(self, image: np.ndarray, pose: Pose, ground_depth: np.ndarray) -> None:
        if not self.faces:
            return
        c, s = math.cos(pose.yaw_rad), math.sin(pose.yaw_rad)
        rotation = np.array([[c, -s], [s, c]])
        depth_buffer = np.divide(
            1,
            ground_depth,
            out=np.zeros_like(ground_depth, dtype=np.float32),
            where=np.isfinite(ground_depth) & (ground_depth > 0),
        )
        camera_world = self.camera.position.copy()
        camera_world[:2] = camera_world[:2] @ rotation.T + [pose.x_m, pose.y_m]
        visible = np.sum(self.normals * (camera_world - self.centers), axis=1) > 0
        local = self.vertices.copy()
        local[:, :2] = (local[:, :2] - [pose.x_m, pose.y_m]) @ rotation
        all_camera = (local - self.camera.position) @ self.camera.rotation.T
        for index in np.flatnonzero(visible):
            color = self.shaded_faces[index]
            camera_points = all_camera[self.offsets[index] : self.offsets[index + 1]]
            if camera_points[:, 2].min() > self.scene.camera.far_m:
                continue
            if camera_points[:, 2].max() < 0.04:
                continue
            vertices = (
                self._clip(camera_points)
                if camera_points[:, 2].min() < 0.04
                else camera_points
            )
            if len(vertices) < 3:
                continue
            projected = vertices @ self.camera.k.T
            uv = projected[:, :2] / projected[:, 2:3]
            if (
                uv[:, 0].max() < 0
                or uv[:, 0].min() >= image.shape[1]
                or uv[:, 1].max() < 0
                or uv[:, 1].min() >= image.shape[0]
            ):
                continue
            self._polygon(image, depth_buffer, uv, vertices[:, 2], color)

    @staticmethod
    def _polygon(image, buffer, vertices, depths, color):
        """Rasterize one convex planar face; inverse depth is affine in pixels."""
        height, width = image.shape[:2]
        lo = np.maximum(np.floor(vertices.min(axis=0)), [0, 0]).astype(int)
        hi = np.minimum(np.ceil(vertices.max(axis=0)), [width - 1, height - 1]).astype(
            int
        )
        if np.any(lo > hi):
            return
        # The last vertex makes a wide triangle even for a many-sided cap.
        selected = [0, 1, len(vertices) - 1]
        matrix = np.column_stack((vertices[selected], np.ones(3)))
        if abs(float(np.linalg.det(matrix))) < 1e-8:
            return
        coefficients = np.linalg.solve(matrix, 1 / depths[selected]).astype(np.float32)
        xx = np.arange(lo[0], hi[0] + 1, dtype=np.float32)[None, :]
        yy = np.arange(lo[1], hi[1] + 1, dtype=np.float32)[:, None]
        inverse_depth = coefficients[0] * xx + coefficients[1] * yy + coefficients[2]
        mask = np.zeros(inverse_depth.shape, np.uint8)
        polygon = np.rint((vertices - lo) * 256).astype(np.int32)
        cv2.fillConvexPoly(mask, polygon, 1, shift=8)
        region = buffer[lo[1] : hi[1] + 1, lo[0] : hi[0] + 1]
        valid = (mask != 0) & (inverse_depth > region)
        image[lo[1] : hi[1] + 1, lo[0] : hi[0] + 1][valid] = color
        region[valid] = inverse_depth[valid]
