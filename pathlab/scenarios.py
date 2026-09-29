"""Obstacle-free classroom maps and policy-independent legality checks."""

from __future__ import annotations

import math

import numpy as np

from .config import Appearance, CameraConfig, Pose, Scene
from .simulation import Camera, world_to_vehicle

FAMILIES = {
    "straight": "01 · 直线入门",
    "bend": "02 · 单弯",
    "s_curve": "03 · 连续 S 弯",
    "sharp": "04 · 大角度急弯",
    "hairpin": "05 · 紧凑回头弯",
    "parallel": "06 · 双侧平行干扰",
    "close_lines": "07 · 近贴断续干扰",
    "repeated": "08 · 密集往返路段",
    "tight_s": "09 · 极限连续反向弯",
    "spiral": "10 · 内收螺旋",
    "spiral_reverse": "11 · 外展螺旋与伴随干扰",
    "spiral_dense": "12 · 密绕螺旋与双侧干扰",
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
    """Obstacle-free teaching curriculum; increasing geometry/identity difficulty."""
    if family not in FAMILIES:
        raise ValueError(f"未知场景族：{family}")
    rng = np.random.default_rng(seed)
    sign = int(rng.choice([-1, 1]))
    radius = float(rng.uniform(0.82, 1.05))
    p = PathBuilder()
    distractors = []
    notes = ["无障碍物；车辆直接从起点沿箭头出发。"]
    if family in ("straight", "parallel", "close_lines"):
        p.segment(6)
    elif family == "bend":
        p.segment(2).turn(sign * math.pi / 2, radius).segment(3)
    elif family == "s_curve":
        p.segment(1.2).turn(sign * math.pi / 3, radius).turn(
            -sign * 2 * math.pi / 3, radius
        ).turn(sign * math.pi / 3, radius).segment(2)
    elif family == "sharp":
        p.segment(1.2).turn(sign * 5 * math.pi / 6, 0.70).segment(2.5)
    elif family == "hairpin":
        p.segment(3).turn(sign * math.pi, 0.62).segment(3)
    elif family == "repeated":
        p.segment(3.5)
        for i in range(4):
            p.turn(sign * (-1) ** i * math.pi, 0.60).segment(3.5)
    elif family == "tight_s":
        for i in range(6):
            p.turn(sign * (-1) ** i * math.pi / 2, 0.58)
        p.segment(1.2)
    else:
        # Archimedean spiral: nonlocal turns are only 0.38/0.40 m apart.
        # Smallest radius still exceeds the vehicle's physical turning radius.
        spacing = 0.38 if family == "spiral_dense" else 0.40
        turns = 2.6 if family == "spiral_dense" else 2.2
        theta = np.linspace(0, turns * 2 * math.pi, 1500)
        radii = 0.68 + spacing * theta / (2 * math.pi)
        if family != "spiral_reverse":
            radii = radii[::-1]
        path = np.column_stack((radii * np.cos(theta), sign * radii * np.sin(theta)))
        if family in {"spiral_reverse", "spiral_dense"}:
            # Offset curves follow the target but never touch it; end sections
            # are omitted so the first image establishes identity unambiguously.
            tangent = np.gradient(path, axis=0)
            tangent /= np.linalg.norm(tangent, axis=1)[:, None]
            normal = np.column_stack((-tangent[:, 1], tangent[:, 0]))
            for offset in [0.12, -0.12] if family == "spiral_dense" else [0.14]:
                distractors.append((path + offset * normal)[100:-80].tolist())
        p.points = path.tolist()
        notes.append(f"螺旋每圈径向间距 {spacing:.2f} m；中心线最小半径 0.68 m。")
    if family == "parallel":
        distractors = [
            [[float(x), side * 0.16] for x in np.linspace(0.6, 6, 150)]
            for side in (-1, 1)
        ]
    elif family == "close_lines":
        distractors = [
            [
                [float(x), side * (0.115 + 0.01 * math.sin(3 * x))]
                for x in np.linspace(start, start + 1.05, 40)
            ]
            for side in (-1, 1)
            for start in (0.7, 2.1, 3.5, 4.9)
        ]
    scene = Scene(
        render_version="3",
        name=FAMILIES[family],
        family=family,
        seed=seed,
        split=split,
        target_path=p.points,
        distractors=distractors,
        initial_pose=Pose(x_m=0, y_m=0, yaw_rad=0),
        camera=CameraConfig(pitch_down_rad=0.65, horizontal_fov_deg=95),
        appearance=Appearance(
            line_width_m=0.045, illumination=float(rng.uniform(0.90, 1.05))
        ),
        objects=[],
        notes=notes,
    ).at_start()
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
    if scene.start_mode == "on_path":
        arc = np.r_[0, np.cumsum(lengths)]
        local = world_to_vehicle(path[arc <= 1.5], scene.initial_pose)
        pixels, front = Camera(scene.camera).project(local)
        visible = (
            front
            & (pixels[:, 0] >= 4)
            & (pixels[:, 0] < scene.camera.width - 4)
            & (pixels[:, 1] >= 4)
            & (pixels[:, 1] < scene.camera.height - 4)
        )
        if np.count_nonzero(visible) < 3:
            errors.append(
                "相机看不到起点之后 1.5 m 内的路线；请增大俯角/视场角或降低相机高度，再预览确认。车辆不会盲驶去猜测隐藏路线"
            )
    if scene.category == "core":
        sample = path[::3]
        arc = np.r_[0, np.cumsum(np.linalg.norm(np.diff(sample, axis=0), axis=1))]
        clearance = scene.vehicle.width_m + 0.08
        for offset in range(0, len(sample), 128):
            distance = np.linalg.norm(
                sample[offset : offset + 128, None] - sample[None], axis=2
            )
            separated = np.abs(arc[offset : offset + 128, None] - arc[None]) > max(
                1, clearance * 3
            )
            if np.any(separated & (distance < clearance)):
                errors.append(
                    "路径存在交叉或间距小于车宽 + 0.08 m 的非相邻路段，请移动控制点"
                )
                break
    hint = scene.task_hint
    if scene.category == "core" and scene.start_mode == "approach":
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
