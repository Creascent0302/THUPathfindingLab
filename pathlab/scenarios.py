"""Eight seeded scene families; legality is independent of any submitted policy."""

from __future__ import annotations

import math

import numpy as np

from .config import Appearance, CameraConfig, ObjectScatter, Pose, Scene
from .scene_objects import scatter_objects
from .simulation import Camera, world_to_vehicle

FAMILIES = {
    "straight": "直线",
    "bend": "单弯",
    "s_curve": "S 形连续弯",
    "sharp": "大角度转弯",
    "hairpin": "可通行回头弯",
    "parallel": "平行干扰线",
    "close_lines": "近距离断开线",
    "repeated": "同线多段可见",
}


class PathBuilder:
    def __init__(self):
        self.points = [[0.0, 0.0]]
        self.yaw = 0.0

    def segment(self, length: float, curvature: float = 0) -> PathBuilder:
        start = np.asarray(self.points[-1])
        distances = np.linspace(0, length, max(2, math.ceil(length / 0.04) + 1))[1:]
        for distance in distances:
            if abs(curvature) < 1e-9:
                delta = distance * np.array([math.cos(self.yaw), math.sin(self.yaw)])
            else:
                delta = (
                    np.array(
                        [
                            math.sin(self.yaw + curvature * distance)
                            - math.sin(self.yaw),
                            math.cos(self.yaw)
                            - math.cos(self.yaw + curvature * distance),
                        ]
                    )
                    / curvature
                )
            self.points.append((start + delta).tolist())
        self.yaw += length * curvature
        return self

    def turn(self, angle: float, radius: float) -> PathBuilder:
        return self.segment(abs(angle) * radius, math.copysign(1 / radius, angle))


def generate(family: str, seed: int = 7, split: str = "development") -> Scene:
    if family not in FAMILIES:
        raise ValueError(f"未知场景族：{family}")
    rng = np.random.default_rng(seed)
    radius = float(rng.uniform(1.05, 1.4))
    sign = int(rng.choice([-1, 1]))
    p = PathBuilder()
    if family in ("straight", "parallel", "close_lines"):
        p.segment(10 + float(rng.uniform(0, 2)))
    elif family == "bend":
        p.segment(3).turn(sign * math.pi / 2, radius).segment(5)
    elif family == "s_curve":
        p.segment(2).turn(sign * math.pi / 3, radius).turn(
            -sign * 2 * math.pi / 3, radius
        ).turn(sign * math.pi / 3, radius).segment(3)
    elif family == "sharp":
        p.segment(3).turn(sign * 5 * math.pi / 6, radius).segment(4)
    elif family == "hairpin":
        p.segment(4).turn(sign * math.pi, radius).segment(4)
    else:
        # Five adjacent passes with alternating return bends, followed by an S.
        # Staggered endpoints keep several distant portions visible together.
        p.segment(6)
        for i, length in enumerate((5.4, 6.4, 5.8, 5.2)):
            p.turn(sign * (-1) ** i * math.pi, radius * (1 + 0.08 * i))
            p.segment(length)
        p.turn(sign * math.pi / 4, radius).turn(-sign * math.pi / 4, radius).segment(2)
    distractors = []
    if family == "parallel":
        distractors.append([[x, -0.43] for x in np.linspace(-0.3, 11.5, 220)])
    elif family == "close_lines":
        distractors.append(
            [[x, -0.20 - 0.035 * math.sin(x)] for x in np.linspace(0.8, 8, 170)]
        )
    scene = Scene(
        render_version="3",
        name=FAMILIES[family],
        family=family,
        seed=seed,
        split=split,
        target_path=p.points,
        distractors=distractors,
        initial_pose=Pose(
            x_m=-1.5,
            y_m=float(rng.uniform(-0.32, 0.25)),
            yaw_rad=float(rng.uniform(-0.14, 0.14)),
        ),
        camera=CameraConfig(pitch_down_rad=0.38),
        appearance=Appearance(
            line_width_m=float(rng.uniform(0.045, 0.08)),
            illumination=float(rng.uniform(0.85, 1.08)),
        ),
    )
    scene.objects = scatter_objects(
        scene, ObjectScatter(count=18 if family == "repeated" else 10)
    )
    errors = validate_scene(scene)
    if errors:
        raise ValueError("生成场景未通过合法性检查：" + "; ".join(errors))
    return scene


def validate_scene(scene: Scene) -> list[str]:
    errors = []
    if scene.vehicle.braking_mps2 < 0.05:
        errors.append("新实验制动减速度至少为 0.05 m/s²；旧参数仍可用于历史回放")
    path = np.asarray(scene.target_path)
    if not np.isfinite(path).all() or np.max(np.abs(path)) > 40:
        return ["路径必须有限且位于 ±40 m 范围"]
    segments = np.diff(path, axis=0)
    lengths = np.linalg.norm(segments, axis=1)
    if np.any(lengths < 1e-6) or np.any(lengths > 0.25):
        errors.append("路径相邻点间距须在 (0, 0.25] m，请先加密折线")
    if np.any(lengths < 1e-6):
        return errors
    headings = np.unwrap(np.arctan2(segments[:, 1], segments[:, 0]))
    curvature = np.abs(np.diff(headings)) / ((lengths[:-1] + lengths[1:]) / 2)
    limit = math.tan(scene.vehicle.max_steering_rad) / scene.vehicle.wheelbase_m
    if scene.category == "core" and curvature.max(initial=0) > limit * 1.01:
        errors.append("核心路径曲率超过车辆转弯能力")
    for other in scene.distractors:
        line = np.asarray(other)
        if (
            line.shape[0] < 2
            or not np.isfinite(line).all()
            or np.max(np.abs(line)) > 40
        ):
            errors.append("干扰线几何无效")
            continue
        spacing = np.linalg.norm(np.diff(line, axis=0), axis=1)
        if np.any(spacing < 1e-6) or np.any(spacing > 0.25):
            errors.append("干扰线相邻点间距须在 (0, 0.25] m")
        # Sampled path spacing is bounded above; use a conservative clearance.
        minimum_clearance = min(
            float(
                np.linalg.norm(
                    path[start : start + 128, None] - line[None, offset : offset + 512],
                    axis=2,
                ).min()
            )
            for start in range(0, len(path), 128)
            for offset in range(0, len(line), 512)
        )
        if (
            scene.category == "core"
            and minimum_clearance < scene.appearance.line_width_m * 1.5
        ):
            errors.append("核心场景的干扰线与目标线过近或相交")
    hint = scene.task_hint
    if scene.category == "core":
        if hint.kind == "none" or (
            hint.kind == "marker" and not scene.appearance.marker_enabled
        ):
            errors.append("核心场景需要明确目标提示")
        if hint.kind == "marker" and hint.marker_rgb != scene.appearance.marker_rgb:
            errors.append("公开提示的标记颜色必须与渲染标记一致")
        cam = Camera(scene.camera)
        # Check start ring and arrow endpoint, not only its center.
        tangent = segments[0] / lengths[0]
        r = scene.appearance.marker_radius_m
        marker = np.array(
            [
                path[0],
                path[0] + [0, r],
                path[0] - [0, r],
                path[0] + tangent * scene.appearance.direction_length_m,
            ]
        )
        uv, front = cam.project(world_to_vehicle(marker, scene.initial_pose))
        if not np.all(
            front
            & (uv[:, 0] >= 8)
            & (uv[:, 0] < scene.camera.width - 8)
            & (uv[:, 1] >= 8)
            & (uv[:, 1] < scene.camera.height - 8)
        ):
            errors.append("起点区域或方向箭头不完整可见")
        local_start = world_to_vehicle(path[:1], scene.initial_pose)[0]
        relative_yaw = (headings[0] - scene.initial_pose.yaw_rad + math.pi) % (
            2 * math.pi
        ) - math.pi
        if not (
            1 <= local_start[0] <= 2.5
            and abs(local_start[1]) <= 0.65
            and abs(relative_yaw) <= 0.35
        ):
            errors.append("初始姿态超出核心接入范围，需标为 stress（不保证接入可行）")
    return errors
