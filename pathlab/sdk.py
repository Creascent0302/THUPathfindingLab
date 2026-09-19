"""Versioned public SDK. This module has no backend or simulator dependencies."""

from __future__ import annotations

import base64
import json
from typing import Any, Literal, Protocol

import cv2
import numpy as np
from pydantic import BaseModel, ConfigDict, Field, model_validator

VERSION = "1.0"
MAX_MESSAGE_BYTES = 8 * 1024 * 1024
MAX_OUTPUT_BYTES = 64 * 1024
MAX_PIXELS = 1280 * 720
Point = tuple[float, float]


class Model(BaseModel):
    model_config = ConfigDict(
        extra="forbid", allow_inf_nan=False, validate_assignment=True
    )


class Action(Model):
    steering_angle_rad: float
    speed_mps: float


class TaskHint(Model):
    kind: Literal["marker", "point", "region", "none"] = "marker"
    point_px: Point | None = None
    region_px: tuple[float, float, float, float] | None = None
    marker_rgb: tuple[int, int, int] = (34, 160, 94)
    direction: Literal["arrow", "unspecified"] = "arrow"

    @model_validator(mode="after")
    def valid_hint(self):
        if self.kind == "point" and self.point_px is None:
            raise ValueError("point 提示必须包含 point_px")
        if self.kind == "region":
            if (
                self.region_px is None
                or self.region_px[2] <= self.region_px[0]
                or self.region_px[3] <= self.region_px[1]
            ):
                raise ValueError("region 必须是 [left, top, right, bottom]")
        if any(not 0 <= c <= 255 for c in self.marker_rgb):
            raise ValueError("marker_rgb 超出范围")
        return self


class Calibration(Model):
    width: int = Field(ge=16, le=1280)
    height: int = Field(ge=16, le=720)
    intrinsic: list[list[float]]
    ground_to_image: list[list[float]]
    frame: Literal["rear_axle_x_forward_y_left_m"] = "rear_axle_x_forward_y_left_m"

    @model_validator(mode="after")
    def matrices(self):
        for matrix in (self.intrinsic, self.ground_to_image):
            a = np.asarray(matrix)
            if a.shape != (3, 3) or abs(np.linalg.det(a)) < 1e-9:
                raise ValueError("标定矩阵必须为可逆 3×3 矩阵")
        return self


class Observation(Model):
    protocol_version: Literal["1.0"] = VERSION
    episode_id: str
    frame_id: int = Field(ge=0)
    timestamp_s: float = Field(ge=0)
    dt_s: float = Field(gt=0)
    width: int = Field(ge=16, le=1280)
    height: int = Field(ge=16, le=720)
    color_space: Literal["RGB"] = "RGB"
    dtype: Literal["uint8"] = "uint8"
    encoding: Literal["png_base64"] = "png_base64"
    image: str = Field(max_length=MAX_MESSAGE_BYTES)
    calibration: Calibration | None = None
    task_hint: TaskHint

    @model_validator(mode="after")
    def consistent_calibration(self):
        if self.calibration and (
            self.calibration.width != self.width
            or self.calibration.height != self.height
        ):
            raise ValueError("标定分辨率必须与当前图像一致")
        return self

    def rgb(self) -> np.ndarray:
        try:
            raw = base64.b64decode(self.image, validate=True)
            # Read PNG dimensions before allocating decoder memory.
            if raw[:8] != b"\x89PNG\r\n\x1a\n" or len(raw) < 24:
                raise ValueError("不是 PNG")
            dims = (
                int.from_bytes(raw[16:20], "big"),
                int.from_bytes(raw[20:24], "big"),
            )
            if dims != (self.width, self.height) or dims[0] * dims[1] > MAX_PIXELS:
                raise ValueError("PNG 尺寸与 Observation 不一致或超限")
            bgr = cv2.imdecode(np.frombuffer(raw, np.uint8), cv2.IMREAD_COLOR)
            if bgr is None:
                raise ValueError("图像解码失败")
            return cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
        except (ValueError, cv2.error) as error:
            raise ValueError(f"图像损坏：{error}") from error

    @classmethod
    def from_rgb(cls, rgb: np.ndarray, **metadata) -> Observation:
        if rgb.dtype != np.uint8 or rgb.ndim != 3 or rgb.shape[2] != 3:
            raise ValueError("图像必须是 H×W×3 uint8 RGB")
        return cls(
            width=rgb.shape[1], height=rgb.shape[0], image=encode_png(rgb), **metadata
        )


def encode_png(rgb: np.ndarray) -> str:
    ok, data = cv2.imencode(".png", cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR))
    if not ok:
        raise ValueError("PNG 编码失败")
    return base64.b64encode(data).decode("ascii")


Status = Literal[
    "UNINITIALIZED",
    "ACQUIRE",
    "ALIGN",
    "TRACK",
    "LOST",
    "AMBIGUOUS",
    "FINISHED",
    "ERROR",
]
Capability = Literal["perception", "path", "action"]


class AlgorithmOutput(Model):
    protocol_version: Literal["1.0"] = VERSION
    status: Status
    confidence: float | None = Field(default=None, ge=0, le=1)
    centerline_px: list[Point] | None = Field(default=None, max_length=4096)
    candidates_px: list[list[Point]] | None = Field(default=None, max_length=128)
    local_path_m: list[Point] | None = Field(
        default=None, min_length=2, max_length=4096
    )
    action: Action | None = None
    lateral_error_m: float | None = None
    heading_error_rad: float | None = None
    curvature_per_m: float | None = None
    debug: dict[str, Any] = Field(default_factory=dict)
    diagnostics: list[str] = Field(default_factory=list, max_length=100)

    @model_validator(mode="after")
    def bounded_output(self):
        encoded = json.dumps(self.model_dump(), allow_nan=False, separators=(",", ":"))
        if len(encoded.encode()) > MAX_OUTPUT_BYTES:
            raise ValueError("单帧算法输出超过 64 KiB，请减少候选点或调试数据")
        return self


class Algorithm(Protocol):
    def initialize(self, config: dict, public_context: dict) -> None: ...
    def reset(self, initial_observation: Observation, task_hint: TaskHint) -> None: ...
    def step(self, observation: Observation) -> AlgorithmOutput: ...
    def close(self) -> None: ...
