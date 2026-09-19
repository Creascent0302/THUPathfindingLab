"""Persistent, bounded, paired evaluations using the normal isolated Run lifecycle."""

from __future__ import annotations

import copy
import csv
import hashlib
import io
import json
from pathlib import Path
import re
import threading
from datetime import datetime, timezone
import uuid

from pydantic import Field, model_validator

from .config import RunConfig, Scene, StressConfig
from .engine import RunManager, TERMINAL
from .evaluation import EVALUATOR_VERSION, SCORE_VERSION, SCORE_WEIGHTS
from .registry import ROOT, PluginSpec, registry
from .scenarios import FAMILIES, generate, validate_scene
from .sdk import Capability, Model
from .storage import write_json

FINAL_ITEMS = {"completed", "failed", "cancelled"}


class BenchmarkMethod(Model):
    algorithm: str
    execution: Capability = "action"
    parameters: dict = Field(default_factory=dict)


class BenchmarkRequest(Model):
    name: str = Field(default="多方法对比", min_length=1, max_length=80)
    algorithms: list[BenchmarkMethod] = Field(min_length=1, max_length=12)
    families: list[str] = Field(default_factory=list, max_length=8)
    map_ids: list[str] = Field(default_factory=list, max_length=16)
    seeds: list[int] = Field(
        default_factory=lambda: [101, 102, 103], min_length=1, max_length=16
    )
    max_steps: int = Field(default=4000, ge=1, le=6000)
    timeout_s: float = Field(default=1, ge=0.05, le=10)
    stress: StressConfig = Field(default_factory=StressConfig)

    @model_validator(mode="after")
    def bounded_plan(self):
        if not self.families and not self.map_ids:
            raise ValueError("请选择至少一张地图")
        if len(set(self.seeds)) != len(self.seeds) or any(
            not 0 <= s <= 2**32 - 1 for s in self.seeds
        ):
            raise ValueError("种子必须唯一且在 0..4294967295 范围")
        for values in (self.families, self.map_ids):
            if len(values) != len(set(values)):
                raise ValueError("地图不可重复")
        if any(family not in FAMILIES for family in self.families):
            raise ValueError("未知内置地图")
        if any(not re.fullmatch(r"[0-9a-f]{32}", value) for value in self.map_ids):
            raise ValueError("自定义地图编号无效")
        ids = [f"{m.algorithm}:{m.execution}" for m in self.algorithms]
        if len(ids) != len(set(ids)):
            raise ValueError("算法与执行模式组合不可重复")
        if len({method.execution for method in self.algorithms}) > 1:
            raise ValueError("同一批次的算法须使用相同执行模式")
        if any(
            m.algorithm == "manual" or m.execution == "perception"
            for m in self.algorithms
        ):
            raise ValueError(
                "批量闭环评测需要 action 或 path 算法，不支持手动与纯感知模式"
            )
        if (
            len(self.algorithms)
            * (len(self.families) + len(self.map_ids))
            * len(self.seeds)
            > 128
        ):
            raise ValueError("每批最多 128 次运行，请减少算法、地图或种子")
        for method in self.algorithms:
            RunConfig(algorithm=method.algorithm, parameters=method.parameters)
        return self


def stable_hash(value) -> str:
    return hashlib.sha256(
        json.dumps(
            value, sort_keys=True, separators=(",", ":"), allow_nan=False
        ).encode()
    ).hexdigest()


def test_set_key(cases: list[dict], versions: dict, request: BenchmarkRequest) -> str:
    return stable_hash(
        {
            "cases": cases,
            "versions": versions,
            "execution": request.algorithms[0].execution,
            "max_steps": request.max_steps,
            "timeout_s": request.timeout_s,
            "stress": request.stress.model_dump(),
        }
    )


def implementation_hash(spec: PluginSpec) -> str:
    """Detect changed code/weights while a queued batch waits to execute."""
    paths = list((ROOT / "algorithms").rglob("*.py"))
    if spec.working_directory:
        paths += [
            p
            for p in Path(spec.working_directory).rglob("*")
            if p.is_file() and "__pycache__" not in p.parts
        ]
    if spec.checkpoint_file:
        paths.append(ROOT / spec.checkpoint_file)
    digest = hashlib.sha256(json.dumps(spec.model_dump(), sort_keys=True).encode())
    for path in sorted(set(paths)):
        digest.update(str(path).encode())
        with path.open("rb") as source:
            while block := source.read(1024 * 1024):
                digest.update(block)
    return digest.hexdigest()


def aggregate(batch: dict) -> dict:
    """A ranking only exists when every method has the same complete case set."""
    items, methods = batch["items"], batch["methods"]
    done = sum(item["state"] in FINAL_ITEMS for item in items)
    complete = (
        done == len(items)
        and not batch.get("invalidated")
        and not any(item["state"] == "cancelled" for item in items)
    )
    rows = []
    for method in methods:
        subset = [item for item in items if item["method_id"] == method["id"]]
        completed = [item for item in subset if item["state"] in FINAL_ITEMS]
        scored = [item for item in completed if item.get("metrics")]
        metrics = [item["metrics"] for item in scored]

        def mean(key, nested=None):
            values = [
                m.get(key) if nested is None else (m.get(key) or {}).get(nested)
                for m in metrics
            ]
            values = [v for v in values if v is not None]
            return sum(values) / len(values) if values else None

        # An execution failure with no frames counts as zero; it never disappears.
        score_sum = sum(
            ((item.get("metrics") or {}).get("score") or {}).get("total", 0)
            for item in completed
        )
        successes = sum(m.get("success") is True for m in metrics)
        rows.append(
            {
                "method_id": method["id"],
                "name": method["name"],
                "algorithm": method["algorithm"],
                "execution": method["execution"],
                "planned": len(subset),
                "finished": len(completed),
                "successes": successes,
                "success_rate": successes / len(subset) if complete else None,
                "score": score_sum / len(subset) if complete else None,
                "observed_score": score_sum / len(completed) if completed else None,
                "completion": sum(
                    (item.get("metrics") or {}).get("completion") or 0
                    for item in completed
                )
                / len(subset)
                if complete
                else None,
                "tracking_error_m": mean("tracking_lateral_error_m", "mean"),
                "tracking_p95_m": mean("tracking_lateral_error_m", "p95"),
                "inference_p95_ms": mean("inference_ms", "p95"),
                "completion_time_s": mean("completion_time_s"),
                "collisions": sum(m.get("collision_count") or 0 for m in metrics),
                "illegal_switches": sum(
                    len(m.get("illegal_switches") or []) for m in metrics
                ),
                "execution_failures": sum(
                    item["state"] == "failed" for item in completed
                ),
                "measured_runs": len(metrics),
            }
        )
    if complete:
        rows.sort(
            key=lambda row: (-row["success_rate"], -row["score"], row["method_id"])
        )
    note = (
        "全量配对结果；执行失败计零分"
        if complete
        else "作业尚未完整配对，暂不排名或计算成功率"
    )
    if batch.get("invalidated"):
        note = "执行期间代码发生变化，批次失效；请重新创建批次"
    return {
        "finished": done,
        "total": len(items),
        "comparable": complete,
        "comparison_note": note,
        "methods": rows,
    }


class BenchmarkManager:
    def __init__(self, manager: RunManager):
        self.manager, self.root = manager, manager.root
        self.folder = self.root / "benchmarks"
        self.folder.mkdir(exist_ok=True)
        self.lock = threading.RLock()
        self.wake, self.closed = threading.Event(), threading.Event()
        self.batches: dict[str, dict] = {}
        self.active_run = None
        self.thread = threading.Thread(
            target=self._dispatch, name="benchmark-queue", daemon=True
        )

    def start(self):
        for path in self.folder.glob("*.json"):
            batch = json.loads(path.read_text(encoding="utf-8"))
            if batch["state"] not in TERMINAL or any(
                item["state"] not in FINAL_ITEMS for item in batch["items"]
            ):
                batch["state"] = "failed"
                batch["reason"] = "服务重启，未完成作业已中断；请创建新批次重新比较"
                for item in batch["items"]:
                    if item["state"] not in FINAL_ITEMS:
                        item.update(state="cancelled", error="server_restart")
                write_json(path, batch)
            self.batches[batch["id"]] = batch
        self.thread.start()

    def _save(self, batch):
        batch["updated_at"] = datetime.now(timezone.utc).isoformat()
        write_json(self.folder / f"{batch['id']}.json", batch)

    def create(self, request: BenchmarkRequest) -> dict:
        specs = registry(artifact_root=self.root)
        methods = []
        for index, method in enumerate(request.algorithms):
            spec = specs.get(method.algorithm)
            if spec is None or method.execution not in spec.capabilities:
                raise ValueError("算法未注册或不支持此执行模式")
            if reason := spec.unavailable_reason():
                raise ValueError(reason)
            methods.append(
                {
                    "id": str(index),
                    **method.model_dump(),
                    "name": spec.name,
                    "spec": spec.model_dump(),
                    "implementation_sha256": implementation_hash(spec),
                }
            )
        scenes = [
            (family, generate(family, seed))
            for family in request.families
            for seed in request.seeds
        ]
        for identifier in request.map_ids:
            path = self.root / "maps" / f"{identifier}.json"
            scene = Scene.model_validate_json(path.read_text(encoding="utf-8"))
            for seed in request.seeds:
                scenes.append((identifier, scene.model_copy(update={"seed": seed})))
        cases = []
        for source, scene in scenes:
            if errors := validate_scene(scene):
                raise ValueError("；".join(errors))
            cases.append(
                {
                    "id": str(len(cases)),
                    "source": source,
                    "name": scene.name,
                    "seed": scene.seed,
                    "scene": scene.model_dump(),
                }
            )
        with self.lock:
            if self.closed.is_set():
                raise ValueError("服务正在关闭")
            if sum(b["state"] not in TERMINAL for b in self.batches.values()) >= 3:
                raise ValueError("最多排队 3 个批次，请等待或取消已有批次")
            if len(self.batches) >= 100:
                raise ValueError("已保存 100 个批次，请先删除已结束的批次")
            pending = sum(
                item["state"] == "queued"
                for b in self.batches.values()
                for item in b["items"]
            )
            if (
                len(list((self.root / "runs").glob("*/manifest.json")))
                + pending
                + len(cases) * len(methods)
                > 200
            ):
                raise ValueError(
                    "本批次将超过 200 条运行记录配额，请先删除或归档旧记录"
                )
            versions = {
                path.name: hashlib.sha256(path.read_bytes()).hexdigest()
                for path in sorted((ROOT / "pathlab").glob("*.py"))
            }
            batch = {
                "id": uuid.uuid4().hex,
                "name": request.name,
                "state": "queued",
                "reason": None,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "request": request.model_dump(),
                "methods": methods,
                "cases": cases,
                "implementation_versions": versions,
                "evaluator_version": EVALUATOR_VERSION,
                "score_version": SCORE_VERSION,
                "score_weights": SCORE_WEIGHTS,
                "items": [
                    {
                        "case_id": case["id"],
                        "method_id": method["id"],
                        "state": "queued",
                        "run_id": None,
                        "metrics": None,
                        "error": None,
                    }
                    for case in cases
                    for method in methods
                ],
            }
            batch["test_set_sha256"] = test_set_key(cases, versions, request)
            self.batches[batch["id"]] = batch
            self._save(batch)
            self.wake.set()
            return self._public(batch)

    def _public(self, batch, *, detail=True):
        source = (
            batch
            if detail
            else {
                key: value
                for key, value in batch.items()
                if key not in {"items", "cases", "methods"}
            }
        )
        public = copy.deepcopy(source)
        public["summary"] = aggregate(batch)
        return public

    def list(self):
        with self.lock:
            return [
                self._public(batch, detail=False)
                for batch in reversed(list(self.batches.values()))
            ]

    def get(self, identifier: str):
        with self.lock:
            if identifier not in self.batches:
                raise FileNotFoundError(identifier)
            result = self._public(self.batches[identifier])
            if (
                self.active_run
                and self.active_run.store.manifest.get("benchmark_id") == identifier
            ):
                result["active_frame"] = self.active_run.frame_id
            return result

    def cancel(self, identifier):
        with self.lock:
            if identifier not in self.batches:
                raise FileNotFoundError(identifier)
            batch = self.batches[identifier]
            if batch["state"] in TERMINAL:
                return self._public(batch)
            batch.update(state="cancelled", reason="用户取消；未完成案例不进入排名")
            for item in batch["items"]:
                if item["state"] == "queued":
                    item.update(state="cancelled", error="user_cancelled")
            if (
                self.active_run
                and self.active_run.store.manifest.get("benchmark_id") == identifier
            ):
                self.active_run.control("stop")
            self._save(batch)
            self.wake.set()
            return self._public(batch)

    def delete(self, identifier):
        with self.lock:
            if identifier not in self.batches:
                raise FileNotFoundError(identifier)
            batch = self.batches[identifier]
            if batch["state"] not in TERMINAL or any(
                item["state"] == "running" for item in batch["items"]
            ):
                raise ValueError("请等待批次结束后再删除")
            (self.folder / f"{identifier}.json").unlink()
            del self.batches[identifier]
            return {"deleted": identifier}

    def _dispatch(self):
        while not self.closed.is_set():
            with self.lock:
                batch = next(
                    (
                        b
                        for b in self.batches.values()
                        if b["state"] in {"queued", "running"}
                    ),
                    None,
                )
                if batch:
                    item = next(
                        (i for i in batch["items"] if i["state"] == "queued"), None
                    )
                    if item is None:
                        batch["state"] = (
                            "failed" if batch.get("invalidated") else "completed"
                        )
                        self._save(batch)
                        continue
                    batch["state"] = "running"
            if batch:
                self._execute(batch, item)
            else:
                self.wake.wait(0.2)
                self.wake.clear()

    def _execute(self, batch, item):
        method = next(m for m in batch["methods"] if m["id"] == item["method_id"])
        case = next(c for c in batch["cases"] if c["id"] == item["case_id"])
        try:
            spec = PluginSpec.model_validate(method["spec"])
            if implementation_hash(spec) != method["implementation_sha256"]:
                batch["invalidated"] = True
                raise ValueError("排队期间算法文件发生变化，请重新创建批次")
            for name, digest in batch["implementation_versions"].items():
                if (
                    hashlib.sha256((ROOT / "pathlab" / name).read_bytes()).hexdigest()
                    != digest
                ):
                    batch["invalidated"] = True
                    raise ValueError("评测或物理代码发生变化，请重新创建批次")
            request = batch["request"]
            config = RunConfig(
                algorithm=method["algorithm"],
                execution=method["execution"],
                parameters=method["parameters"],
                scene=Scene.model_validate(case["scene"]),
                family=case["scene"]["family"],
                seed=case["seed"],
                max_steps=request["max_steps"],
                timeout_s=request["timeout_s"],
                stress=request["stress"],
                realtime=False,
            )
            with self.lock:
                if batch["state"] == "cancelled" or self.closed.is_set():
                    return
                # RunManager owns the shared concurrency and disk quota checks.
                run = self.manager.create(
                    config,
                    headless=True,
                    spec=spec,
                    metadata={
                        "benchmark_id": batch["id"],
                        "benchmark_case_id": case["id"],
                        "benchmark_method_id": method["id"],
                        "test_set_sha256": batch["test_set_sha256"],
                    },
                )
                self.active_run = run
                item.update(state="running", run_id=run.id)
                self._save(batch)
                run.control("resume")
            while run.thread.is_alive():
                run.thread.join(timeout=0.2)
                if self.closed.is_set():
                    run.control("stop")
            with self.lock:
                item.update(
                    state=run.state,
                    metrics=run.store.manifest["metrics"],
                    error=run.failures[0]["message"] if run.failures else None,
                )
                self.active_run = None
                self._save(batch)
        except Exception as error:
            from .engine import RunCapacityError

            if isinstance(error, RunCapacityError):
                self.closed.wait(0.3)
                return
            with self.lock:
                item.update(state="failed", error=str(error)[:2000])
                self.active_run = None
                self._save(batch)

    def close(self):
        self.closed.set()
        self.wake.set()
        with self.lock:
            for batch in self.batches.values():
                if batch["state"] not in TERMINAL:
                    self.cancel(batch["id"])
                    batch["reason"] = "服务关闭，批次已中断；已完成结果保留"
                    self._save(batch)
        if self.thread.is_alive():
            self.thread.join(timeout=6)


def export_benchmark_csv(batch: dict) -> str:
    stream = io.StringIO(newline="")
    writer = csv.writer(stream)
    writer.writerow(
        [
            "batch_id",
            "test_set_sha256",
            "method",
            "case",
            "seed",
            "run_id",
            "state",
            "success",
            "score",
            "completion",
            "lateral_p95_m",
            "inference_p95_ms",
            "collision_count",
            "error",
        ]
    )
    for item in batch["items"]:
        method = next(m for m in batch["methods"] if m["id"] == item["method_id"])
        case = next(c for c in batch["cases"] if c["id"] == item["case_id"])
        metrics = item.get("metrics") or {}
        writer.writerow(
            [
                batch["id"],
                batch["test_set_sha256"],
                method["algorithm"],
                case["name"],
                case["seed"],
                item["run_id"],
                item["state"],
                metrics.get("success"),
                (metrics.get("score") or {}).get("total"),
                metrics.get("completion"),
                (metrics.get("tracking_lateral_error_m") or {}).get("p95"),
                (metrics.get("inference_ms") or {}).get("p95"),
                metrics.get("collision_count"),
                item.get("error"),
            ]
        )
    return "\ufeff" + stream.getvalue()
