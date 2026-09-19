"""Bounded experiment lifecycle. GUI cadence never changes integration dt."""

from __future__ import annotations

import base64
from collections import deque
from pathlib import Path
import threading
import time
import uuid

import cv2
import numpy as np

from .adapters import PurePursuit, execution_action
from .config import RunConfig
from .evaluation import Evaluator, summarize
from .registry import PluginSpec, registry
from .scenarios import generate, validate_scene
from .sdk import Action, AlgorithmOutput, Observation, TaskHint, VERSION
from .simulation import Renderer, Vehicle
from .sources import read_source
from .storage import RunStore
from .worker import WorkerClient, WorkerError

TERMINAL = {"completed", "failed", "cancelled"}


class Run:
    def __init__(
        self,
        config: RunConfig,
        root: Path,
        *,
        headless=False,
        spec: PluginSpec | None = None,
    ):
        self.id = uuid.uuid4().hex
        self.config, self.root, self.headless = config, root, headless
        self.spec = spec
        if config.algorithm != "manual":
            self.spec = spec or registry(artifact_root=root).get(config.algorithm)
            if self.spec is None:
                raise ValueError("算法尚未注册，请先上传算法 ZIP 或配置本地插件")
            if config.execution not in self.spec.capabilities:
                raise ValueError("所选算法不支持这个执行模式")
        elif config.mode != "simulation" or config.execution != "action":
            raise ValueError("手动驾驶仅适用于闭环仿真的 action 模式")
        self.scene = (
            (config.scene or generate(config.family, config.seed))
            if config.mode == "simulation"
            else None
        )
        if self.scene:
            if config.task_hint is not None:
                self.scene = self.scene.model_copy(
                    update={"task_hint": config.task_hint}
                )
            errors = validate_scene(self.scene)
            if errors:
                raise ValueError("; ".join(errors))
        self.source = (
            read_source(root, config.source_id or "") if not self.scene else None
        )
        self.dt = self.scene.dt_s if self.scene else 1 / self.source["fps"]
        self.hint = config.task_hint or (
            self.scene.task_hint
            if self.scene
            else TaskHint(kind="none", direction="unspecified")
        )
        self.config = config.model_copy(update={"task_hint": self.hint})
        self.state, self.paused, self.reason = "queued", True, None
        self.lock = threading.RLock()
        self.wake, self.cancelled = threading.Event(), threading.Event()
        self.single_steps = 0
        self.client_seen = time.monotonic()
        self.manual_seen = 0.0
        self.manual = Action(steering_angle_rad=0, speed_mps=0)
        self.records, self.failures = [], []
        self.logs = deque(maxlen=100)
        self.worker = None
        self.renderer = None
        self.vehicle = (
            Vehicle(self.scene.vehicle, self.scene.initial_pose) if self.scene else None
        )
        self.evaluator = Evaluator(self.scene) if self.scene else None
        self.adapter = (
            PurePursuit(
                self.scene.vehicle.wheelbase_m, self.scene.vehicle.max_speed_mps
            )
            if self.scene
            else None
        )
        self.observation = None
        self.preview = None
        self.frame_id = 0
        self.pending = deque(maxlen=64)
        self.last_action = Action(steering_angle_rad=0, speed_mps=0)
        self.last_action_frame = None
        self.rng = np.random.default_rng(config.seed)
        algorithm = (
            self.spec.model_dump()
            if self.spec
            else {
                "id": "manual",
                "name": "人工驾驶",
                "version": "1.0",
                "capabilities": ["action"],
            }
        )
        self.store = RunStore(
            root,
            self.id,
            self.config.model_dump(),
            algorithm,
            self.scene.model_dump() if self.scene else None,
        )
        self.thread = threading.Thread(
            target=self._run, name=f"experiment-{self.id[:8]}", daemon=True
        )

    def start(self):
        self.thread.start()

    def touch(self):
        self.client_seen = time.monotonic()

    def control(self, command: str):
        self.touch()
        if command == "stop":
            self.cancelled.set()
            self.wake.set()
            if self.worker:
                self.worker.kill()
            return
        with self.lock:
            if self.state in TERMINAL:
                raise ValueError("运行已结束，请重置或创建新运行")
            if command == "resume":
                self.paused = False
            elif command == "pause":
                self.paused = True
                self.single_steps = 0
            elif command == "step":
                self.paused = True
                self.single_steps = 1
            else:
                raise ValueError("未知控制命令")
            self.wake.set()

    def set_action(self, action: Action):
        if self.config.algorithm != "manual" or self.state in TERMINAL:
            raise ValueError("当前运行不接受手动动作")
        with self.lock:
            self.manual = action
            self.manual_seen = time.monotonic()
            self.touch()

    def _observe(self) -> Observation:
        if self.scene:
            rgb = self.renderer.render(self.vehicle.state, self.frame_id)
            calibration = self.renderer.camera.calibration()
            timestamp = self.frame_id * self.dt
        else:
            image_path = (
                self.root
                / "uploads"
                / self.config.source_id
                / f"{self.frame_id:06d}.png"
            )
            bgr = cv2.imread(str(image_path))
            if bgr is None:
                raise ValueError("素材帧损坏或已删除")
            rgb, calibration = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB), None
            timestamp = self.source["frames"][self.frame_id]["timestamp_s"]
        obs = Observation.from_rgb(
            rgb,
            episode_id=self.id,
            frame_id=self.frame_id,
            timestamp_s=timestamp,
            dt_s=self.dt,
            calibration=calibration,
            task_hint=self.hint,
        )
        if self.frame_id == 0 and self.hint.kind == "point":
            x, y = self.hint.point_px
            if not (0 <= x < obs.width and 0 <= y < obs.height):
                raise ValueError("初始化点击超出首帧范围")
        if self.frame_id == 0 and self.hint.kind == "region":
            left, top, right, bottom = self.hint.region_px
            if not (0 <= left < right <= obs.width and 0 <= top < bottom <= obs.height):
                raise ValueError("初始化矩形超出图像范围")
        return obs

    def _run(self):
        try:
            if self.scene:
                self.renderer = Renderer(self.scene)
            self.observation = self._observe()
            self.preview = self.observation.image
            if self.spec:
                self.worker = WorkerClient(self.spec)
                # Explicit public context only, never serialize a Scene into this call.
                context = {
                    "protocol_version": VERSION,
                    "observation_track": "pure_visual",
                    "execution": self.config.execution,
                    "coordinates": "rear axle: x forward, y left; steering positive left; m, rad, s",
                    "vehicle_limits": self.scene.vehicle.model_dump()
                    if self.scene
                    else None,
                }
                self.worker.initialize(
                    self.config.parameters,
                    context,
                    self.observation,
                    self.config.timeout_s,
                )
            self.state = "running"
            self.logs.append("已初始化；每次运行使用独立算法实例。")
            self.store.manifest["state"] = self.state
            self.store.save()
            while not self.cancelled.is_set():
                if not self.headless and time.monotonic() - self.client_seen > 30:
                    self.reason = "client_disconnected"
                    self.cancelled.set()
                    self.logs.append("浏览器 30 秒无心跳，自动停止。")
                    break
                with self.lock:
                    do_step = not self.paused or self.single_steps > 0
                    if self.single_steps:
                        self.single_steps -= 1
                if not do_step:
                    self.wake.wait(0.1)
                    self.wake.clear()
                    continue
                start = time.monotonic()
                self._step()
                if self.reason:
                    break
                if self.config.realtime:
                    self.cancelled.wait(max(0, self.dt - (time.monotonic() - start)))
            if self.cancelled.is_set():
                self.reason = self.reason or "user_cancelled"
                self._brake("cancelled")
                self.state = "cancelled"
            else:
                self.state = "completed"
        except Exception as error:
            if self.cancelled.is_set():
                self.reason = self.reason or "user_cancelled"
                self.state = "cancelled"
            else:
                kind = error.kind if isinstance(error, WorkerError) else "exception"
                self.failures.append(
                    {
                        "kind": kind,
                        "message": str(error)[:4096],
                        "frame_id": self.frame_id,
                        "raw_response": self.worker.last_raw if self.worker else None,
                        "validated_output": getattr(self, "last_output", None),
                    }
                )
                self.logs.append(f"{kind}: {error}")
                self.reason, self.state = f"algorithm_{kind}", "failed"
            self._brake("algorithm_failure")
        finally:
            if self.worker:
                self.logs.extend(self.worker.logs)
                self.worker.close()
            metrics = summarize(
                self.records, self.evaluator, self.reason, self.failures
            )
            self.store.finish(self.state, metrics, self.failures)

    def _step(self):
        obs = self.observation
        self.last_output = None
        pose_before = self.vehicle.state.model_dump() if self.vehicle else None
        output, inference_ms, events = None, None, []
        stress = self.config.stress
        dropped = (
            stress.mode == "stress" and self.rng.random() < stress.drop_probability
        )
        if dropped:
            events.append("observation_dropped")
        elif self.spec:
            start = time.perf_counter()
            output = self.worker.step(obs, self.config.timeout_s)
            inference_ms = (time.perf_counter() - start) * 1000
        else:
            with self.lock:
                action = self.manual.model_copy()
            if time.monotonic() - self.manual_seen > 0.6:
                action = Action(steering_angle_rad=0, speed_mps=0)
                events.append("manual_deadman")
            output = AlgorithmOutput(
                status="ACQUIRE",
                action=action,
                diagnostics=["人工驾驶；状态不代表视觉识别结果"],
            )
        if output is not None:
            # Preserve algorithm data even if subsequent execution validation fails.
            self.last_output = output.model_dump()
            if output.status == "ERROR":
                raise WorkerError(
                    "exception", "算法主动报告 ERROR：" + "; ".join(output.diagnostics)
                )
        applied, score = None, None
        if self.scene:
            if output is not None:
                action, action_events = execution_action(
                    output, self.config.execution, self.adapter
                )
                events.extend(action_events)
                delay = stress.delay_frames if stress.mode == "stress" else 0
                self.pending.append((self.frame_id + delay, self.frame_id, action))
            while self.pending and self.pending[0][0] <= self.frame_id:
                _, source_frame, self.last_action = self.pending.popleft()
                self.last_action_frame = source_frame
            expired = (
                self.last_action_frame is None
                or (self.frame_id - self.last_action_frame) * self.dt
                > stress.action_ttl_s
            )
            action = self.last_action
            if expired:
                action = Action(steering_angle_rad=0, speed_mps=0)
                events.append("action_expired")
            applied = self.vehicle.advance(action, self.dt).model_dump()
            events.extend(applied["interventions"])
            score = self.evaluator.update(
                self.vehicle.state, (self.frame_id + 1) * self.dt
            )
        row = {
            "frame_id": self.frame_id,
            "timestamp_s": (self.frame_id + 1) * self.dt,
            "observation_timestamp_s": obs.timestamp_s,
            "dt_s": self.dt,
            "output": output.model_dump() if output else None,
            "inference_ms": inference_ms,
            "applied": applied,
            "interventions": events,
            "evaluation": score,
            "pose_before": pose_before,
            "pose": self.vehicle.state.model_dump() if self.vehicle else None,
        }
        self._append(row, obs)
        if self.store.record_bytes >= 64 * 1024 * 1024:
            self.reason = "recording_quota"
        elif self.evaluator and self.evaluator.done_reason:
            self.reason = self.evaluator.done_reason
        elif output and output.status == "FINISHED":
            self.reason = "policy_finished"
        elif self.config.mode == "image" or (
            self.source and self.frame_id >= len(self.source["frames"])
        ):
            self.reason = "source_complete"
        elif self.frame_id >= self.config.max_steps:
            self.reason = "episode_timeout"
        if not self.reason:
            self.observation = self._observe()

    def _append(self, row: dict, observation: Observation | None):
        if observation and self.config.record_images:
            if not self.store.save_image(
                row["frame_id"], base64.b64decode(observation.image)
            ):
                row["interventions"].append("image_recording_quota")
        self.store.append(row)
        with self.lock:
            self.records.append(row)
            if observation:
                self.preview = observation.image
            self.frame_id += 1

    def _brake(self, event: str):
        if not self.vehicle:
            return
        # Fixed-step physical braking is recorded, never teleport speed to zero.
        while self.vehicle.state.speed_mps > 1e-8:
            before = self.vehicle.state.model_dump()
            applied = self.vehicle.advance(
                Action(steering_angle_rad=0, speed_mps=0), self.dt
            ).model_dump()
            self._append(
                {
                    "frame_id": self.frame_id,
                    "timestamp_s": (self.frame_id + 1) * self.dt,
                    "observation_timestamp_s": None,
                    "dt_s": self.dt,
                    "output": None,
                    "inference_ms": None,
                    "applied": applied,
                    "interventions": [
                        event,
                        "safety_braking",
                        *applied["interventions"],
                    ],
                    "pose_before": before,
                    "pose": self.vehicle.state.model_dump(),
                    "evaluation": None,
                },
                None,
            )

    def snapshot(self, *, touch=True) -> dict:
        if touch:
            self.touch()
        with self.lock:
            last = self.records[-1] if self.records else None
            history = [
                {
                    k: row.get(k)
                    for k in (
                        "frame_id",
                        "timestamp_s",
                        "pose",
                        "applied",
                        "evaluation",
                        "inference_ms",
                    )
                }
                for row in self.records[-240:]
            ]
            return {
                "id": self.id,
                "state": self.state,
                "paused": self.paused,
                "frame_count": len(self.records),
                "frame": last,
                "image": self.preview,
                "logs": list(self.logs),
                "reason": self.reason,
                "metrics": self.store.manifest["metrics"],
                "failures": self.failures,
                "scene": self.scene.model_dump() if self.scene else None,
                "config": self.config.model_dump(),
                "initial_pose": self.scene.initial_pose.model_dump()
                if self.scene
                else None,
                "calibration": self.renderer.camera.calibration().model_dump()
                if self.renderer
                else None,
                "history": history,
            }


class RunManager:
    def __init__(self, root: Path):
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)
        self.runs: dict[str, Run] = {}
        self.lock = threading.Lock()

    def create(self, config: RunConfig) -> Run:
        with self.lock:
            if sum(run.thread.is_alive() for run in self.runs.values()) >= 3:
                raise ValueError("最多同时运行 3 个实验，请先停止已有实验")
            if len(list((self.root / "runs").glob("*/manifest.json"))) >= 200:
                raise ValueError("已保存 200 次实验，请在运行记录中删除不需要的记录")
            if (
                sum(p.stat().st_size for p in self.root.rglob("*") if p.is_file())
                >= 2 * 1024**3
            ):
                raise ValueError("artifacts 已达到 2 GiB，请先归档并清理已有实验")
            # Retain few finished objects; disk recordings remain available.
            finished = [
                key
                for key, run in self.runs.items()
                if not run.thread.is_alive() and run.state in TERMINAL
            ]
            for key in finished[:-5]:
                del self.runs[key]
            run = Run(config, self.root)
            self.runs[run.id] = run
            run.start()
            return run

    def close(self):
        for run in list(self.runs.values()):
            if run.thread.is_alive():
                run.control("stop")
        for run in list(self.runs.values()):
            run.thread.join(timeout=4)
