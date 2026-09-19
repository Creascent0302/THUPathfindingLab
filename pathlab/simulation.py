"""Pinhole rendering and fixed-step vehicle dynamics."""

from __future__ import annotations

import math

import cv2
import numpy as np

from .config import CameraConfig, Pose, Scene, VehicleConfig
from .sdk import Action, Calibration, Model
from .dynamics import integrate_motion
from .scene_objects import ObjectRenderer, object_footprint


def wrap_angle(angle: float) -> float:
    return (angle + math.pi) % (2 * math.pi) - math.pi


class VehicleState(Pose):
    speed_mps: float = 0
    steering_angle_rad: float = 0
    velocity_x_mps: float = 0
    velocity_y_mps: float = 0
    yaw_rate_rad_s: float = 0
    acceleration_mps2: float = 0


class AppliedAction(Model):
    requested: Action
    bounded: Action
    actual: Action
    interventions: list[str]


class Vehicle:
    def __init__(self, config: VehicleConfig, pose: Pose):
        self.config = config
        self.state = VehicleState(**pose.model_dump())

    def advance(self, action: Action, dt: float) -> AppliedAction:
        if not 0 < dt <= 0.1:
            raise ValueError("物理步长必须在 (0, 0.1] s")
        c, s = self.config, self.state
        steer = float(
            np.clip(action.steering_angle_rad, -c.max_steering_rad, c.max_steering_rad)
        )
        speed = float(np.clip(action.speed_mps, 0, c.max_speed_mps))
        events = []
        if steer != action.steering_angle_rad:
            events.append("steering_saturated")
        if speed != action.speed_mps:
            events.append("speed_saturated")
        velocity = np.array([s.velocity_x_mps, s.velocity_y_mps])
        # Also support callers initializing a stationary/legacy state by speed.
        if abs(np.linalg.norm(velocity) - s.speed_mps) > 1e-9:
            velocity = s.speed_mps * np.array(
                [math.cos(s.yaw_rad), math.sin(s.yaw_rad)]
            )
        previous = np.array(
            [
                s.x_m,
                s.y_m,
                s.yaw_rad,
                *velocity,
                s.steering_angle_rad,
                s.yaw_rate_rad_s,
                s.acceleration_mps2,
            ]
        )
        values = integrate_motion(previous, steer, speed, c.model_dump(), dt)
        (
            s.x_m,
            s.y_m,
            s.yaw_rad,
            s.velocity_x_mps,
            s.velocity_y_mps,
            s.steering_angle_rad,
            s.yaw_rate_rad_s,
            s.acceleration_mps2,
        ) = map(float, values)
        s.speed_mps = math.hypot(s.velocity_x_mps, s.velocity_y_mps)
        if abs(s.steering_angle_rad - steer) > 1e-9:
            events.append("steering_rate_limited")
        if abs(s.speed_mps - speed) > 1e-9:
            events.append("acceleration_limited")
        return AppliedAction(
            requested=action,
            bounded=Action(steering_angle_rad=steer, speed_mps=speed),
            actual=Action(
                steering_angle_rad=s.steering_angle_rad, speed_mps=s.speed_mps
            ),
            interventions=events,
        )


class Camera:
    def __init__(self, config: CameraConfig):
        self.config = config
        c = config
        f = c.width / (2 * math.tan(math.radians(c.horizontal_fov_deg) / 2))
        self.k = np.array(
            [[f, 0, (c.width - 1) / 2], [0, f, (c.height - 1) / 2], [0, 0, 1]]
        )
        yaw, pitch = c.yaw_left_rad, c.pitch_down_rad
        forward = np.array(
            [
                math.cos(yaw) * math.cos(pitch),
                math.sin(yaw) * math.cos(pitch),
                -math.sin(pitch),
            ]
        )
        right = np.array([math.sin(yaw), -math.cos(yaw), 0])
        down = np.cross(forward, right)
        self.rotation = np.stack([right, down, forward])
        self.position = np.array([c.forward_m, c.left_m, c.height_m])
        self.h = self.k @ np.column_stack(
            (self.rotation[:, :2], -self.rotation @ self.position)
        )
        self.inv_h = np.linalg.inv(self.h)

    def calibration(self) -> Calibration:
        return Calibration(
            width=self.config.width,
            height=self.config.height,
            intrinsic=self.k.tolist(),
            ground_to_image=self.h.tolist(),
        )

    def project(self, points: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        points = np.asarray(points, dtype=float).reshape(-1, 2)
        homogeneous = np.column_stack((points, np.ones(len(points)))) @ self.h.T
        depth = homogeneous[:, 2]
        uv = homogeneous[:, :2] / np.where(abs(depth) > 1e-9, depth, np.nan)[:, None]
        return uv, depth > 0

    def project_3d(self, points: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """Project metric vehicle-frame XYZ; ground calibration stays unchanged."""
        local = np.asarray(points, dtype=float).reshape(-1, 3)
        homogeneous = (local - self.position) @ self.rotation.T @ self.k.T
        depth = homogeneous[:, 2]
        uv = homogeneous[:, :2] / np.where(abs(depth) > 1e-9, depth, np.nan)[:, None]
        return uv, depth > 0

    def unproject(self, pixels: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        pixels = np.asarray(pixels, dtype=float).reshape(-1, 2)
        ground = np.column_stack((pixels, np.ones(len(pixels)))) @ self.inv_h.T
        scale = ground[:, 2]
        xy = ground[:, :2] / np.where(abs(scale) > 1e-9, scale, np.nan)[:, None]
        valid = (
            (scale > 0)
            & np.isfinite(xy).all(axis=1)
            & (np.linalg.norm(xy, axis=1) <= self.config.far_m)
        )
        return xy, valid


def world_to_vehicle(points: np.ndarray, pose: Pose) -> np.ndarray:
    dx = np.asarray(points, dtype=float) - [pose.x_m, pose.y_m]
    c, s = math.cos(pose.yaw_rad), math.sin(pose.yaw_rad)
    return dx @ np.array([[c, -s], [s, c]])


def vehicle_to_world(points: np.ndarray, pose: Pose) -> np.ndarray:
    c, s = math.cos(pose.yaw_rad), math.sin(pose.yaw_rad)
    return np.asarray(points, dtype=float) @ np.array([[c, s], [-s, c]]) + [
        pose.x_m,
        pose.y_m,
    ]


class Renderer:
    def __init__(self, scene: Scene):
        self.scene = scene
        self.camera = Camera(scene.camera)
        all_points = np.concatenate(
            [
                np.asarray(scene.target_path),
                *[np.asarray(p) for p in scene.distractors],
                *[
                    object_footprint(obj)
                    for obj in scene.objects
                    if obj.enabled and scene.render_version == "3"
                ],
            ]
        )
        self.origin = all_points.min(axis=0) - 5
        extent = all_points.max(axis=0) + 5 - self.origin
        self.scale = min(100.0, 4096 / max(extent))
        self.raster = np.full(
            (int(extent[1] * self.scale) + 1, int(extent[0] * self.scale) + 1, 3),
            scene.appearance.ground_rgb,
            np.uint8,
        )
        a = scene.appearance
        if (
            scene.render_version in ("2", "3")
            and a.surface != "plain"
            and a.texture_strength
        ):
            # Texture belongs to world coordinates: it stays fixed as the car moves.
            rng = np.random.default_rng(np.random.SeedSequence([scene.seed, 937]))
            height, width = self.raster.shape[:2]
            coarse = rng.normal(
                0, 1, (max(2, height // 48), max(2, width // 48))
            ).astype(np.float32)
            texture = (
                cv2.resize(coarse, (width, height), interpolation=cv2.INTER_CUBIC) * 2
            )
            texture += rng.standard_normal((height, width), dtype=np.float32) * 0.9
            texture *= a.texture_strength
            if a.surface == "concrete":
                # Light expansion joints, never dark enough to impersonate tape.
                x = self.origin[0] + np.arange(width) / self.scale
                y = self.origin[1] + np.arange(height) / self.scale
                joints = (np.mod(x, 2) < 0.014)[None, :] | (np.mod(y, 2) < 0.014)[
                    :, None
                ]
                texture[joints] -= 9 * a.texture_strength
            # Keep one float plane instead of a full floating RGB raster.
            for channel, base in enumerate(a.ground_rgb):
                self.raster[:, :, channel] = np.clip(texture + base, 0, 255).astype(
                    np.uint8
                )
        for path in [scene.target_path, *scene.distractors]:
            cv2.polylines(
                self.raster,
                [self._raster_points(path)],
                False,
                a.line_rgb,
                max(1, round(a.line_width_m * self.scale)),
                cv2.LINE_AA,
            )
        target = np.asarray(scene.target_path)
        if a.marker_enabled:
            start = self._raster_points(target[:1])[0]
            cv2.circle(
                self.raster,
                tuple(start),
                round(a.marker_radius_m * self.scale),
                a.marker_rgb,
                max(2, round(0.045 * self.scale)),
                cv2.LINE_AA,
            )
            tangent = target[1] - target[0]
            tangent /= np.linalg.norm(tangent)
            arrow = self._raster_points(
                [target[0] + tangent * 0.23, target[0] + tangent * a.direction_length_m]
            )
            cv2.arrowedLine(
                self.raster,
                tuple(arrow[0]),
                tuple(arrow[1]),
                a.marker_rgb,
                max(2, round(0.05 * self.scale)),
                cv2.LINE_AA,
                tipLength=0.4,
            )
        end = self._raster_points(target[-1:])[0]
        cv2.circle(
            self.raster,
            tuple(end),
            round(0.13 * self.scale),
            (224, 143, 47),
            max(2, round(0.04 * self.scale)),
            cv2.LINE_AA,
        )
        yy, xx = np.mgrid[0 : scene.camera.height, 0 : scene.camera.width]
        self.ground, self.valid = self.camera.unproject(
            np.column_stack((xx.ravel(), yy.ravel()))
        )
        self.objects = (
            ObjectRenderer(scene, self.camera) if scene.render_version == "3" else None
        )
        homogeneous = (
            np.column_stack((self.ground, np.ones(len(self.ground)))) @ self.camera.h.T
        )
        self.ground_depth = np.where(self.valid, homogeneous[:, 2], np.inf).reshape(
            scene.camera.height, scene.camera.width
        )
        if self.objects:
            self.objects.cast_shadows(self.raster, self.origin, self.scale)
        self.modern_ground = (
            np.nan_to_num(self.ground, nan=0, posinf=0, neginf=0).astype(np.float32)
            if self.objects is not None
            else None
        )

    def _raster_points(self, path) -> np.ndarray:
        return np.rint((np.asarray(path) - self.origin) * self.scale).astype(np.int32)

    def render(self, pose: Pose, frame_id: int) -> np.ndarray:
        c, a = self.scene.camera, self.scene.appearance
        if self.modern_ground is not None:
            cosine, sine = math.cos(pose.yaw_rad), math.sin(pose.yaw_rad)
            gx, gy = self.modern_ground.T
            world = np.column_stack(
                (gx * cosine - gy * sine + pose.x_m, gx * sine + gy * cosine + pose.y_m)
            )
        else:
            ground = np.nan_to_num(self.ground, nan=0, posinf=0, neginf=0)
            world = vehicle_to_world(ground, pose)
        raster_xy = (world - self.origin) * self.scale
        mx = raster_xy[:, 0].reshape(c.height, c.width).astype(np.float32)
        my = raster_xy[:, 1].reshape(c.height, c.width).astype(np.float32)
        image = cv2.remap(
            self.raster,
            mx,
            my,
            cv2.INTER_LINEAR,
            borderMode=cv2.BORDER_CONSTANT,
            borderValue=a.ground_rgb,
        )
        image[~self.valid.reshape(c.height, c.width)] = (183, 202, 213)
        if self.objects is not None:
            # A quiet sky gradient remains behind distant objects above the floor.
            invalid = ~self.valid.reshape(c.height, c.width)
            sky = np.linspace((167, 192, 207), (219, 225, 225), c.height).astype(
                np.uint8
            )
            image[invalid] = np.broadcast_to(sky[:, None], image.shape)[invalid]
        shade = 1 - a.shadow * (
            0.5 + 0.5 * np.sin(world[:, 0] * 1.4 + world[:, 1] * 0.7)
        )
        if self.objects is not None:
            shade[~self.valid] = 1
        image = (
            image.astype(np.float32)
            * shade.reshape(c.height, c.width, 1)
            * a.illumination
        )
        if self.objects:
            self.objects.render(image, pose, self.ground_depth)
        if a.noise_std:
            rng = np.random.default_rng(
                np.random.SeedSequence([self.scene.seed, frame_id])
            )
            if self.objects is not None:
                image += (
                    rng.standard_normal(image.shape, dtype=np.float32) * a.noise_std
                )
            else:
                image += rng.normal(0, a.noise_std, image.shape).astype(np.float32)
        image = np.clip(image, 0, 255).astype(np.uint8)
        if a.blur_sigma:
            image = cv2.GaussianBlur(image, (0, 0), a.blur_sigma)
        if a.occlusion and 35 <= frame_id % 100 <= 45:
            image[
                c.height // 3 : 2 * c.height // 3, c.width // 3 : 2 * c.width // 3
            ] = a.ground_rgb
        return image
