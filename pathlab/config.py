"""All experiment assumptions are serialized in these validated configurations."""

from __future__ import annotations

import json
from typing import Annotated, Literal

from pydantic import Field, model_validator

from .sdk import Model, Point, TaskHint


class VehicleConfig(Model):
    wheelbase_m: float = Field(default=0.32, gt=0.05, le=2)
    track_width_m: float = Field(default=0.24, gt=0.05, le=2)
    length_m: float = Field(default=0.46, gt=0.05, le=3)
    width_m: float = Field(default=0.28, gt=0.05, le=3)
    max_steering_rad: float = Field(default=0.52, gt=0.01, le=1.0)
    max_speed_mps: float = Field(default=1.5, gt=0, le=5)
    acceleration_mps2: float = Field(default=0.8, gt=0, le=10)
    braking_mps2: float = Field(default=1.8, gt=0, le=20)
    steering_rate_rad_s: float = Field(default=1.2, gt=0, le=10)
    reverse_allowed: Literal[False] = False


class CameraConfig(Model):
    width: int = Field(default=640, ge=160, le=1280)
    height: int = Field(default=360, ge=90, le=720)
    forward_m: float = Field(default=0.18, ge=-1, le=1)
    left_m: float = Field(default=0, ge=-1, le=1)
    height_m: float = Field(default=0.48, ge=0.1, le=3)
    pitch_down_rad: float = Field(default=0.52, ge=0.15, le=1.3)
    yaw_left_rad: float = Field(default=0, ge=-1.5, le=1.5)
    horizontal_fov_deg: float = Field(default=80, ge=30, le=120)
    far_m: float = Field(default=16, ge=3, le=40)


class Appearance(Model):
    line_width_m: float = Field(default=0.06, ge=0.02, le=0.2)
    line_rgb: tuple[int, int, int] = (39, 48, 57)
    ground_rgb: tuple[int, int, int] = (224, 228, 223)
    marker_rgb: tuple[int, int, int] = (34, 160, 94)
    marker_radius_m: float = Field(default=0.16, ge=0.08, le=0.3)
    direction_length_m: float = Field(default=0.6, ge=0.3, le=1)
    marker_enabled: bool = True
    illumination: float = Field(default=1, ge=0.4, le=1.3)
    shadow: float = Field(default=0.12, ge=0, le=0.7)
    noise_std: float = Field(default=0.6, ge=0, le=25)
    blur_sigma: float = Field(default=0, ge=0, le=3)
    occlusion: bool = False
    surface: Literal["concrete", "mat", "plain"] = "concrete"
    texture_strength: float = Field(default=0.65, ge=0, le=1)

    @model_validator(mode="after")
    def colors(self):
        if any(
            not 0 <= c <= 255
            for color in (self.line_rgb, self.ground_rgb, self.marker_rgb)
            for c in color
        ):
            raise ValueError("颜色通道必须在 0..255 范围")
        return self


class Pose(Model):
    x_m: float = 0
    y_m: float = 0
    yaw_rad: float = 0


class MapDesign(Model):
    waypoints: list[Point] = Field(min_length=2, max_length=60)
    radius_m: float = Field(default=1, ge=0.1, le=10)


class Scene(Model):
    format_version: Literal["1.0"] = "1.0"
    render_version: Literal["1", "2"] = "1"
    name: str
    family: str
    seed: int = Field(ge=0, le=2**32 - 1)
    split: Literal["development", "validation", "test"] = "development"
    category: Literal["core", "stress"] = "core"
    target_path: list[Point] = Field(min_length=3, max_length=5000)
    distractors: list[Annotated[list[Point], Field(min_length=2, max_length=5000)]] = (
        Field(default_factory=list, max_length=20)
    )
    initial_pose: Pose
    vehicle: VehicleConfig = Field(default_factory=VehicleConfig)
    camera: CameraConfig = Field(default_factory=CameraConfig)
    appearance: Appearance = Field(default_factory=Appearance)
    dt_s: float = Field(default=0.05, ge=0.01, le=0.1)
    task_hint: TaskHint = Field(default_factory=TaskHint)
    notes: list[str] = Field(default_factory=list)
    design: MapDesign | None = None

    @model_validator(mode="after")
    def bounded_geometry(self):
        if len(self.target_path) + sum(map(len, self.distractors)) > 12000:
            raise ValueError("场景总顶点数超过 12000")
        return self


class StressConfig(Model):
    mode: Literal["deterministic", "stress"] = "deterministic"
    delay_frames: int = Field(default=0, ge=0, le=30)
    drop_probability: float = Field(default=0, ge=0, le=0.95)
    action_ttl_s: float = Field(default=0.4, gt=0, le=5)


class RunConfig(Model):
    mode: Literal["simulation", "image", "sequence"] = "simulation"
    algorithm: str = "manual"
    execution: Literal["perception", "path", "action"] = "action"
    family: str = "straight"
    seed: int = Field(default=7, ge=0, le=2**32 - 1)
    scene: Scene | None = None
    source_id: str | None = None
    parameters: dict = Field(default_factory=dict)
    task_hint: TaskHint | None = None
    max_steps: int = Field(default=4000, ge=1, le=6000)
    timeout_s: float = Field(default=1, ge=0.05, le=10)
    record_images: bool = False
    stress: StressConfig = Field(default_factory=StressConfig)
    realtime: bool = True

    @model_validator(mode="after")
    def public_parameters(self):
        encoded = json.dumps(self.parameters, allow_nan=False)
        if len(encoded.encode()) > 16 * 1024:
            raise ValueError("算法参数超过 16 KiB")
        return self
