"""Append-only frame records, bounded images, and portable exports."""

from __future__ import annotations

import csv
import importlib.metadata
import io
import json
import os
import platform
from pathlib import Path
import sys

from .evaluation import EVALUATOR_VERSION, SCORE_VERSION, THRESHOLDS, comparison_key
from .sdk import VERSION

RUN_STORAGE_LIMIT_BYTES = 2 * 1024**3
SUBMISSION_STORAGE_LIMIT_BYTES = 2 * 1024**3


def directory_bytes(directory: Path) -> int:
    """Count regular files without following links; tolerate concurrent deletion."""
    total = 0
    for parent, _, names in os.walk(directory):
        for name in names:
            path = Path(parent) / name
            try:
                if not path.is_symlink() and path.is_file():
                    total += path.stat().st_size
            except FileNotFoundError:
                continue
    return total


def check_run_storage(root: Path):
    used = directory_bytes(root / "runs")
    if used >= RUN_STORAGE_LIMIT_BYTES:
        raise ValueError(
            f"运行记录已占用 {used / 1024**3:.2f} GiB，达到 2 GiB 配额。"
            "请在「运行记录与对比」删除不需要的记录及图像；"
            "地图、训练数据和算法报告不计入此配额。"
        )


def storage_usage(root: Path) -> dict:
    return {
        "runs": {
            "used_bytes": directory_bytes(root / "runs"),
            "limit_bytes": RUN_STORAGE_LIMIT_BYTES,
        },
        "submissions": {
            "used_bytes": directory_bytes(root / "submissions"),
            "limit_bytes": SUBMISSION_STORAGE_LIMIT_BYTES,
        },
    }


def write_json(path: Path, data):
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False),
        encoding="utf-8",
    )
    temporary.replace(path)


def environment() -> dict:
    return {
        "python": sys.version,
        "platform": platform.platform(),
        "packages": {
            name: importlib.metadata.version(name)
            for name in (
                "numpy",
                "opencv-python-headless",
                "fastapi",
                "pydantic",
                "uvicorn",
            )
        },
    }


class RunStore:
    def __init__(
        self,
        root: Path,
        episode_id: str,
        config: dict,
        algorithm: dict,
        scene: dict | None,
    ):
        self.directory = root / "runs" / episode_id
        self.directory.mkdir(parents=True)
        physics_version = (
            (scene or {}).get("vehicle", {}).get("motion_model", "kinematic_v1")
        )
        self.manifest = {
            "episode_id": episode_id,
            "protocol_version": VERSION,
            "evaluator_version": EVALUATOR_VERSION,
            "score_version": SCORE_VERSION,
            "physics_version": physics_version,
            "render_version": (scene or {}).get("render_version"),
            "comparison_key": comparison_key(config, scene, physics_version),
            "owner_pid": os.getpid(),
            "thresholds": THRESHOLDS,
            "config": config,
            "algorithm": algorithm,
            "scene": scene,
            "environment": environment(),
            "state": "queued",
            "metrics": None,
            "failures": [],
        }
        self.rows = (self.directory / "frames.jsonl").open("a", encoding="utf-8")
        self.image_bytes = 0
        self.record_bytes = 0
        self.save()

    def append(self, row: dict):
        encoded = (
            json.dumps(row, ensure_ascii=False, allow_nan=False, separators=(",", ":"))
            + "\n"
        )
        self.rows.write(encoded)
        self.record_bytes += len(encoded.encode())
        self.rows.flush()

    def save_image(self, frame_id: int, raw: bytes):
        if self.image_bytes + len(raw) > 128 * 1024 * 1024:
            return False
        directory = self.directory / "images"
        directory.mkdir(exist_ok=True)
        (directory / f"{frame_id:06d}.png").write_bytes(raw)
        self.image_bytes += len(raw)
        return True

    def save(self):
        write_json(self.directory / "manifest.json", self.manifest)

    def finish(self, state: str, metrics: dict, failures: list[dict]):
        self.manifest.update(
            state=state,
            metrics=metrics,
            failures=failures,
            recorded_image_bytes=self.image_bytes,
        )
        self.save()
        self.rows.close()


def read_records(directory: Path) -> list[dict]:
    with (directory / "frames.jsonl").open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.endswith("\n")]


def export_csv(records: list[dict]) -> str:
    stream = io.StringIO(newline="")
    fields = [
        "frame_id",
        "timestamp_s",
        "status",
        "confidence",
        "inference_ms",
        "speed_mps",
        "steering_angle_rad",
        "lateral_error_m",
        "heading_error_rad",
        "completion",
        "velocity_x_mps",
        "velocity_y_mps",
        "yaw_rate_rad_s",
        "acceleration_mps2",
        "collision_ids",
        "interventions",
    ]
    writer = csv.DictWriter(stream, fields)
    writer.writeheader()
    for r in records:
        output = r.get("output") or {}
        actual = (r.get("applied") or {}).get("actual", {})
        score = r.get("evaluation") or {}
        writer.writerow(
            {
                "frame_id": r["frame_id"],
                "timestamp_s": r["timestamp_s"],
                "status": output.get("status"),
                "confidence": output.get("confidence"),
                "inference_ms": r.get("inference_ms"),
                **actual,
                **{
                    k: score.get(k)
                    for k in ["lateral_error_m", "heading_error_rad", "completion"]
                },
                **{
                    key: (r.get("pose") or {}).get(key)
                    for key in (
                        "velocity_x_mps",
                        "velocity_y_mps",
                        "yaw_rate_rad_s",
                        "acceleration_mps2",
                    )
                },
                "collision_ids": json.dumps(
                    score.get("collision_ids"), ensure_ascii=False
                )
                if score.get("collision_ids") is not None
                else None,
                "interventions": "|".join(r.get("interventions", [])),
            }
        )
    return stream.getvalue()
