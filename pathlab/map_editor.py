"""Tangent circular fillets turn editable waypoints into a feasible centerline."""

from __future__ import annotations

import math

import numpy as np
from pydantic import Field, model_validator

from .config import (
    Appearance,
    CameraConfig,
    DistractorDesign,
    MapDesign,
    ObjectScatter,
    Pose,
    Scene,
    SceneObject,
    VehicleConfig,
)
from .scene_objects import scatter_objects
from .scenarios import validate_scene
from .sdk import Model


class MapRequest(Model):
    name: str = Field(default="我的地图", min_length=1, max_length=80)
    seed: int = Field(default=7, ge=0, le=2**32 - 1)
    design: MapDesign
    vehicle: VehicleConfig = Field(default_factory=VehicleConfig)
    camera: CameraConfig = Field(
        default_factory=lambda: CameraConfig(pitch_down_rad=0.38)
    )
    appearance: Appearance = Field(default_factory=Appearance)
    objects: list[SceneObject] | None = Field(default=None, max_length=80)
    scatter: ObjectScatter | None = None
    source_scene: Scene | None = None

    @model_validator(mode="before")
    @classmethod
    def inherit_source_settings(cls, value):
        if isinstance(value, dict) and value.get("source_scene") is not None:
            source = Scene.model_validate(value["source_scene"])
            value = dict(value)
            for field in ("vehicle", "camera", "appearance"):
                inherited = getattr(source, field).model_dump()
                supplied = value.get(field)
                if supplied is None or isinstance(supplied, dict):
                    value[field] = {**inherited, **(supplied or {})}
        return value


def rounded_path(design: MapDesign, vehicle: VehicleConfig) -> list[list[float]]:
    points = np.asarray(design.waypoints, dtype=float)
    if not np.isfinite(points).all() or np.max(np.abs(points)) > 35:
        raise ValueError("控制点须在 ±35 m 范围内")
    minimum = vehicle.wheelbase_m / math.tan(vehicle.max_steering_rad)
    radius = design.radius_m
    if radius < minimum * 1.02:
        raise ValueError(f"圆角半径至少为 {minimum * 1.02:.3f} m（含 2% 采样余量）")
    delta = np.diff(points, axis=0)
    lengths = np.linalg.norm(delta, axis=1)
    if np.any(lengths < 0.2):
        raise ValueError("相邻控制点至少相距 0.2 m")
    directions = delta / lengths[:, None]
    trims = np.zeros(len(points))
    angles = np.zeros(len(points))
    for i in range(1, len(points) - 1):
        u, v = directions[i - 1], directions[i]
        angle = math.atan2(u[0] * v[1] - u[1] * v[0], np.dot(u, v))
        if abs(angle) > math.radians(170):
            raise ValueError(f"控制点 {i + 1} 接近原路折返，请增加控制点形成回头弯")
        angles[i] = angle
        trims[i] = radius * math.tan(abs(angle) / 2)
    for i, length in enumerate(lengths):
        required = trims[i] + trims[i + 1] + 0.06
        if required >= length:
            raise ValueError(
                f"第 {i + 1} 段长度不足：圆角需至少 {required:.2f} m，请拉开控制点或减小半径"
            )
    result = [points[0]]

    def line_to(end):
        start = result[-1]
        distance = float(np.linalg.norm(end - start))
        if distance > 1e-8:
            result.extend(np.linspace(start, end, math.ceil(distance / 0.04) + 1)[1:])

    for i in range(1, len(points) - 1):
        u, v = directions[i - 1], directions[i]
        angle = angles[i]
        entry = points[i] - u * trims[i]
        line_to(entry)
        if abs(angle) < 1e-8:
            continue
        side = math.copysign(1, angle)
        center = entry + side * radius * np.array([-u[1], u[0]])
        start_angle = math.atan2(entry[1] - center[1], entry[0] - center[0])
        steps = math.ceil(abs(angle) * radius / 0.04)
        for theta in np.linspace(start_angle, start_angle + angle, steps + 1)[1:]:
            result.append(
                center + radius * np.array([math.cos(theta), math.sin(theta)])
            )
    line_to(points[-1])
    return np.asarray(result).tolist()


def distractor_path(design: DistractorDesign) -> list[list[float]]:
    """Sample independent visual lines, with optional corner cutting smoothing."""
    points = np.asarray(design.waypoints, dtype=float)
    if len(points) < 2:
        raise ValueError("每条干扰线至少需要 2 个控制点；请继续点按画布或删除空线")
    if not np.isfinite(points).all() or np.max(np.abs(points)) > 40:
        raise ValueError("干扰线控制点须在 ±40 m 范围内")
    if np.any(np.linalg.norm(np.diff(points, axis=0), axis=1) < 1e-6):
        raise ValueError("干扰线不能有重合的相邻控制点")
    if design.interpolation == "smooth":
        for _ in range(3):
            corners = np.stack(
                (
                    0.75 * points[:-1] + 0.25 * points[1:],
                    0.25 * points[:-1] + 0.75 * points[1:],
                ),
                axis=1,
            ).reshape(-1, 2)
            points = np.vstack((points[0], corners, points[-1]))
    result = [points[0].tolist()]
    for start, end in zip(points[:-1], points[1:]):
        count = math.ceil(float(np.linalg.norm(end - start)) / 0.12)
        result.extend(np.linspace(start, end, count + 1)[1:].tolist())
        if len(result) > 5000:
            raise ValueError("干扰线过长或控制点过多，采样后不能超过 5000 点")
    return result


def build_scene(request: MapRequest) -> Scene:
    source = request.source_scene
    same_route = (
        source is not None
        and source.design is not None
        and (
            source.design.waypoints == request.design.waypoints
            and source.design.radius_m == request.design.radius_m
        )
    )
    path = (
        source.target_path
        if same_route
        else rounded_path(request.design, request.vehicle)
    )
    tangent = np.array(path[1]) - path[0]
    tangent /= np.linalg.norm(tangent)
    start = np.array(path[0]) - tangent * 1.5
    distractors = (
        [
            line.waypoints
            if source
            and line.interpolation == "polyline"
            and line.waypoints in source.distractors
            else distractor_path(line)
            for line in request.design.distractors
        ]
        if request.design.distractors is not None
        else source.distractors
        if source
        else []
    )
    metadata = source.model_dump() if source else {}
    metadata.update(
        render_version="3",
        name=request.name,
        family="custom",
        seed=request.seed,
        target_path=path,
        distractors=distractors,
        initial_pose=source.initial_pose
        if same_route
        else Pose(
            x_m=start[0], y_m=start[1], yaw_rad=math.atan2(tangent[1], tangent[0])
        ),
        vehicle=request.vehicle,
        camera=request.camera,
        appearance=request.appearance,
        design=request.design,
        objects=request.objects
        if request.objects is not None
        else source.objects
        if source
        else [],
    )
    scene = Scene.model_validate(metadata)
    if request.scatter:
        generated = scatter_objects(scene, request.scatter)
        if len(scene.objects) + len(generated) > 80:
            raise ValueError("显式物件与自动布置物件总数不能超过 80")
        scene.objects.extend(generated)
    if any(obj.enabled for obj in scene.objects):
        note = "物件按真实尺寸遮挡画面。手动放在线路或起点标记上的物件可构成遮挡/碰撞压力场景；路径几何通过不代表有无障碍通路。"
        if note not in scene.notes:
            scene.notes.append(note)
    errors = validate_scene(scene)
    # Exclude nearby points along the same arc; check distinct stretches against
    # the body width so crossing or overlapping routes cannot pass this editor.
    sample = np.asarray(path)[::3]
    arc = np.r_[0, np.cumsum(np.linalg.norm(np.diff(sample, axis=0), axis=1))]
    clearance = request.vehicle.width_m + 0.08
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
    if errors:
        raise ValueError("；".join(errors))
    return scene


def geometry_summary(scene: Scene) -> dict:
    delta = np.diff(scene.target_path, axis=0)
    lengths = np.linalg.norm(delta, axis=1)
    curvature = np.abs(np.diff(np.unwrap(np.arctan2(delta[:, 1], delta[:, 0])))) / (
        (lengths[:-1] + lengths[1:]) / 2
    )
    maximum = float(curvature.max(initial=0))
    return {
        "length_m": float(lengths.sum()),
        "minimum_vehicle_radius_m": scene.vehicle.wheelbase_m
        / math.tan(scene.vehicle.max_steering_rad),
        "minimum_path_radius_m": 1 / maximum if maximum > 1e-8 else None,
        "object_count": sum(obj.enabled for obj in scene.objects),
        "distractor_count": len(scene.distractors),
    }
