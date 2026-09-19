"""Deployment only: image preprocessing → CNN/GRU → actions. No expert fallback."""

import hashlib
import io
from pathlib import Path

import numpy as np

from pathlab.sdk import Action, AlgorithmOutput

DEFAULT_CHECKPOINT = Path(__file__).parent / "weights" / "driver.pt"


class RecurrentPolicy:
    def initialize(self, config, public_context):
        try:
            import torch
            from .model import RecurrentDriver
        except ImportError as error:
            raise RuntimeError(
                "学习算法需要可选 PyTorch：python scripts/setup_learning.py"
            ) from error
        self.torch = torch
        torch.set_num_threads(1)
        checkpoint = Path(config.get("checkpoint", DEFAULT_CHECKPOINT))
        if not checkpoint.is_file():
            raise RuntimeError(
                "学习模型不可用：缺少权重。请运行 python run.py learning fit --data artifacts/learning/data"
            )
        raw_checkpoint = checkpoint.read_bytes()
        self.checkpoint_sha256 = hashlib.sha256(raw_checkpoint).hexdigest()
        data = torch.load(
            io.BytesIO(raw_checkpoint), map_location="cpu", weights_only=True
        )
        if data.get("format_version") != 1 or data.get("architecture") != "cnn_gru_v1":
            raise ValueError("不支持的学习模型格式")
        self.model = RecurrentDriver()
        self.model.load_state_dict(data["model"])
        self.model.eval()
        self.limits = public_context.get("vehicle_limits") or {
            "wheelbase_m": 0.32,
            "max_steering_rad": 0.52,
            "max_speed_mps": 1.5,
        }
        self.model_id = data["model_id"]
        self.supported_hints = data.get("supported_hints", ["marker"])
        self.marker_rgb = tuple(data.get("marker_rgb", [34, 160, 94]))
        self.interval = float(data.get("control_interval_s", 0.1))

    def reset(self, initial_observation, task_hint):
        if task_hint.kind not in self.supported_hints or (
            task_hint.kind == "marker"
            and tuple(task_hint.marker_rgb) != self.marker_rgb
        ):
            raise ValueError(
                "当前学习权重仅验证默认绿色标记初始化；其他提示请使用模块化算法或重新训练"
            )
        self.hidden = None
        self.previous = np.zeros(2, np.float32)
        self.raw_action = self.previous.copy()
        self.last_update = None
        self.last_seen = None
        self.hint = task_hint
        self.visibility = 0.0

    def step(self, observation):
        from .model import context_input, image_input

        torch = self.torch
        if self.last_seen is not None and observation.timestamp_s < self.last_seen:
            raise ValueError("时间倒退，请重置时序模型")
        self.last_seen = observation.timestamp_s
        updated = (
            self.last_update is None
            or observation.timestamp_s - self.last_update >= self.interval - 1e-6
        )
        if updated:
            dt = (
                self.interval
                if self.last_update is None
                else observation.timestamp_s - self.last_update
            )
            if dt < 0:
                raise ValueError("时间倒退，请重置时序模型")
            image = image_input(observation.rgb(), self.hint, self.last_update is None)
            tensor = (
                torch.from_numpy(image.transpose(2, 0, 1).copy())
                .float()
                .div(255)[None, None]
            )
            context = torch.from_numpy(context_input(self.limits, self.previous, dt))[
                None, None
            ]
            with torch.inference_mode():
                action, visible, self.hidden = self.model(tensor, context, self.hidden)
            normalized = action[0, 0].numpy()
            self.raw_action = normalized * [
                self.limits["max_steering_rad"],
                min(1.0, self.limits["max_speed_mps"]),
            ]
            self.visibility = float(torch.sigmoid(visible[0, 0]))
            self.previous = (
                self.raw_action.copy()
                if self.visibility >= 0.2
                else np.zeros(2, np.float32)
            )
            self.last_update = observation.timestamp_s
        return AlgorithmOutput(
            status="TRACK" if self.visibility >= 0.2 else "LOST",
            confidence=None,
            action=Action(
                steering_angle_rad=float(self.raw_action[0]),
                speed_mps=float(self.raw_action[1]),
            ),
            debug={
                "model_id": self.model_id,
                "checkpoint_sha256": self.checkpoint_sha256,
                "network_updated": updated,
                "visibility_probability": self.visibility,
            },
            diagnostics=[
                "端到端 CNN/GRU 直接动作；可见性头不等同于闭环成功概率；无几何控制器回退"
            ],
        )

    def close(self):
        self.hidden = None
