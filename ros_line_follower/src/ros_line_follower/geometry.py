"""Image-time localization and calibrated flat-ground projection (SI units)."""

from __future__ import annotations

from bisect import bisect_left
from dataclasses import dataclass
import math

import numpy as np


def wrap_angle(angle):
    return math.atan2(math.sin(angle), math.cos(angle))


def rotation(yaw):
    c, s = math.cos(yaw), math.sin(yaw)
    return np.array([[c, -s], [s, c]], dtype=float)


@dataclass(frozen=True)
class Pose2:
    stamp: float
    x: float
    y: float
    yaw: float
    speed: float = 0.0
    roll: float = 0.0
    pitch: float = 0.0

    def __post_init__(self):
        if not np.isfinite(list(self.__dict__.values())).all() or self.stamp <= 0:
            raise ValueError("定位时间和位姿必须有限，timestamp 必须大于零")


class PoseBuffer:
    """Caller holds its state lock; no extrapolation beyond measured poses."""

    def __init__(self, max_gap_s=0.2, capacity=200):
        if not 0 < max_gap_s <= 1 or capacity < 2:
            raise ValueError("定位缓存参数无效")
        self.max_gap_s, self.capacity = max_gap_s, capacity
        self.poses = []

    def clear(self):
        self.poses.clear()

    def push(self, pose):
        if self.poses and pose.stamp <= self.poses[-1].stamp:
            raise ValueError("定位时间戳重复或倒退")
        self.poses.append(pose)
        self.poses = self.poses[-self.capacity :]

    def at(self, stamp):
        times = [pose.stamp for pose in self.poses]
        index = bisect_left(times, stamp)
        if index < len(times) and abs(times[index] - stamp) < 1e-6:
            return self.poses[index]
        if not 0 < index < len(times):
            raise ValueError("尚无包围图像时间的定位，禁止无界外推")
        a, b = self.poses[index - 1 : index + 1]
        if b.stamp - a.stamp > self.max_gap_s:
            raise ValueError("定位采样间隔过大，无法可靠插值")
        t = (stamp - a.stamp) / (b.stamp - a.stamp)
        return Pose2(
            stamp,
            a.x + t * (b.x - a.x),
            a.y + t * (b.y - a.y),
            wrap_angle(a.yaw + t * wrap_angle(b.yaw - a.yaw)),
            a.speed + t * (b.speed - a.speed),
            a.roll + t * (b.roll - a.roll),
            a.pitch + t * (b.pitch - a.pitch),
        )


def relative_motion(previous, current):
    """Translation in the previous vehicle axes, then counterclockwise yaw."""
    displacement = np.array([current.x - previous.x, current.y - previous.y])
    return displacement @ rotation(previous.yaw), wrap_angle(current.yaw - previous.yaw)


def rigid_transform(translation, quaternion_xyzw):
    translation = np.asarray(translation, dtype=float)
    q = np.asarray(quaternion_xyzw, dtype=float)
    if translation.shape != (3,) or q.shape != (4,):
        raise ValueError("TF 需要三维平移和 xyzw 四元数")
    if not np.isfinite(translation).all() or not np.isfinite(q).all():
        raise ValueError("TF 含非有限值")
    norm = np.linalg.norm(q)
    if abs(norm - 1) > 0.01:
        raise ValueError("TF 四元数未归一化")
    x, y, z, w = q / norm
    result = np.eye(4)
    result[:3, :3] = [
        [1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
        [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
        [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)],
    ]
    result[:3, 3] = translation
    return result


def ground_homography(projection, rectification, camera_from_vehicle, ground_z_m):
    """Rectified RGB: K_rect R_rect T_optical_from_vehicle [x,y,z_ground,1].

    TF already refers to this camera's optical center. Stereo P[:,3] is a
    baseline relative to the *other* camera and must not be applied again.
    """
    p = np.asarray(projection, dtype=float).reshape(3, 4)
    r = np.asarray(rectification, dtype=float).reshape(3, 3)
    transform = np.asarray(camera_from_vehicle, dtype=float).reshape(4, 4)
    if not all(np.isfinite(a).all() for a in (p, r, transform)):
        raise ValueError("相机标定含非有限值")
    if not math.isfinite(ground_z_m) or p[0, 0] <= 0 or p[1, 1] <= 0:
        raise ValueError("相机未标定，或地面高度无效")
    for matrix in (r, transform[:3, :3]):
        if not np.allclose(matrix.T @ matrix, np.eye(3), atol=1e-4) or not np.isclose(
            np.linalg.det(matrix), 1, atol=1e-4
        ):
            raise ValueError("相机/TF 旋转矩阵无效")
    if not np.allclose(transform[3], [0, 0, 0, 1]):
        raise ValueError("TF 不是刚体变换")
    embedding = np.array([[1, 0, 0], [0, 1, 0], [0, 0, ground_z_m], [0, 0, 1]])
    h = p[:, :3] @ r @ transform[:3] @ embedding
    if abs(np.linalg.det(h)) < 1e-8 or np.linalg.cond(h) > 1e9:
        raise ValueError("地面投影退化，请检查离地高度和相机外参")
    return h


class PublicationGate:
    """Normal paths are rate-limited and never re-stamped; first stop is immediate."""

    def __init__(self, rate_hz=2.0):
        if not 0.2 <= rate_hz <= 5:
            raise ValueError("参考路径发布频率应为 0.2～5 Hz")
        self.period = 1.0 / rate_hz
        self.last_wall = -math.inf
        self.last_stamp = None
        self.stopped = False

    def ready(self, wall_time, source_stamp, valid):
        due = wall_time - self.last_wall >= self.period
        if valid:
            if not due or source_stamp == self.last_stamp:
                return False
        elif self.stopped and not due:
            return False
        self.last_wall = wall_time
        self.last_stamp = source_stamp if valid else None
        self.stopped = not valid
        return True
