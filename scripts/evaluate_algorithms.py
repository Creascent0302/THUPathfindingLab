"""Reproducible policy evaluation with public observations and private scoring.

In-process evaluation measures policy compute without JSONL transport overhead.
Use run.py benchmark for full worker/protocol evaluation of the same plugins.
"""

# ruff: noqa: E402

import argparse
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
import csv
import hashlib
import importlib
import json
import os
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import cv2
import numpy as np

from pathlab.adapters import PurePursuit, execution_action
from pathlab.evaluation import EVALUATOR_VERSION, THRESHOLDS, Evaluator, summarize
from pathlab.config import MapDesign
from pathlab.map_editor import MapRequest, build_scene
from pathlab.registry import registry
from pathlab.scenarios import FAMILIES, generate
from pathlab.sdk import Observation
from pathlab.simulation import Renderer, Vehicle
from pathlab.storage import environment, write_json


def evaluation_scene(family, seed, split, suite):
    scene = generate("straight" if suite == "custom" else family, seed, split=split)
    rng = np.random.default_rng(seed)
    if suite == "appearance":
        scene.appearance.illumination = float(rng.uniform(0.5, 0.8))
        scene.appearance.shadow = 0.4
        scene.appearance.noise_std = 6
        scene.appearance.blur_sigma = 0.7
        scene.appearance.line_width_m = 0.04
    elif suite == "occlusion":
        scene.appearance.occlusion = True
    elif suite == "camera":
        scene.camera.height_m = 0.58
        scene.camera.pitch_down_rad = 0.61
        scene.camera.horizontal_fov_deg = 92
    elif suite == "offset":
        scene.category = "stress"
        scene.initial_pose.y_m = float(rng.choice([-0.48, 0.48]))
        scene.initial_pose.yaw_rad = float(rng.choice([-0.26, 0.26]))
    elif suite == "custom":
        radius, width = float(rng.uniform(0.60, 0.95)), float(rng.uniform(4.5, 6.5))
        spacing = 2 * radius + 0.2
        scene = build_scene(
            MapRequest(
                seed=seed,
                design=MapDesign(
                    radius_m=radius,
                    waypoints=[
                        [0, 0],
                        [width, 0],
                        [width, spacing],
                        [1, spacing],
                        [1, 2 * spacing],
                        [width + 1, 2 * spacing],
                    ],
                ),
            )
        )
        scene.split = split
    return scene


def evaluate(job):
    algorithm, family, seed, steps, resolution, parameters, split, suite, output = job
    cv2.setNumThreads(1)
    scene = evaluation_scene(family, seed, split, suite)
    if resolution:
        scene.camera.width, scene.camera.height = resolution, round(resolution * 9 / 16)
    simulator, vehicle, evaluator = (
        Renderer(scene),
        Vehicle(scene.vehicle, scene.initial_pose),
        Evaluator(scene),
    )
    spec = registry()[algorithm]
    policy = None
    context = {
        "protocol_version": "1.0",
        "observation_track": "pure_visual",
        "execution": "action",
        "vehicle_limits": scene.vehicle.model_dump(),
    }
    records, failures, reason = [], [], "episode_timeout"
    adapter = PurePursuit(scene.vehicle.wheelbase_m, scene.vehicle.max_speed_mps)
    start = time.perf_counter()
    try:
        module, name = spec.entrypoint.split(":")
        policy = getattr(importlib.import_module(module), name)()
        policy.initialize(parameters, context)
        for index in range(steps):
            obs = Observation.from_rgb(
                simulator.render(vehicle.state, index),
                episode_id="evaluation",
                frame_id=index,
                timestamp_s=index * scene.dt_s,
                dt_s=scene.dt_s,
                calibration=simulator.camera.calibration(),
                task_hint=scene.task_hint,
            )
            if index == 0:
                policy.reset(obs, obs.task_hint)
            clock = time.perf_counter()
            result = policy.step(obs)
            elapsed = (time.perf_counter() - clock) * 1000
            action, events = execution_action(result, "action", adapter)
            applied = vehicle.advance(action, scene.dt_s)
            score = evaluator.update(vehicle.state, (index + 1) * scene.dt_s)
            records.append(
                {
                    "frame_id": index,
                    "timestamp_s": (index + 1) * scene.dt_s,
                    "dt_s": scene.dt_s,
                    "output": result.model_dump(),
                    "applied": applied.model_dump(),
                    "evaluation": score,
                    "inference_ms": elapsed,
                    "interventions": events + applied.interventions,
                    "pose": vehicle.state.model_dump(),
                }
            )
            if evaluator.done_reason:
                reason = evaluator.done_reason
                break
            if result.status in {"ERROR", "FINISHED"}:
                reason = "policy_" + result.status.lower()
                break
    except Exception as error:
        failures.append({"kind": "exception", "message": repr(error)})
        reason = "algorithm_exception"
    finally:
        try:
            if policy is not None:
                policy.close()
        except Exception as error:
            failures.append({"kind": "close_exception", "message": repr(error)})
    summary = summarize(records, evaluator, reason, failures)
    report = {
        "algorithm": algorithm,
        "family": scene.family,
        "seed": seed,
        "split": split,
        "suite": suite,
        "scene": scene.model_dump(),
        "parameters": parameters,
        "metrics": summary,
        "failures": failures,
        "wall_s": time.perf_counter() - start,
        "last_frame": records[-1] if records else None,
    }
    if output:
        folder = Path(output) / "episodes"
        folder.mkdir(parents=True, exist_ok=True)
        write_json(folder / f"{algorithm}-{family}-{seed}.json", report)
    print(
        f"{algorithm:20s} {family:12s} {seed:4d} {reason:20s} {summary['completion']:.3f} frames={len(records)}",
        flush=True,
    )
    return report


def write_report(folder, plan, reports):
    """Keep every trial and summarize sample counts, including failures."""
    write_json(folder / "report.json", {"plan": plan, "runs": reports})
    fields = [
        "algorithm",
        "family",
        "seed",
        "success",
        "reason",
        "completion",
        "illegal_switches",
        "inference_mean_ms",
    ]
    with (folder / "report.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fields)
        writer.writeheader()
        for row in reports:
            m = row["metrics"]
            writer.writerow(
                {
                    **{k: row[k] for k in fields[:3]},
                    **{k: m[k] for k in fields[3:6]},
                    "illegal_switches": len(m["illegal_switches"] or []),
                    "inference_mean_ms": m["inference_ms"]["mean"],
                }
            )
    lines = [
        "# 视觉寻迹闭环评测",
        "",
        f"集合：{plan['split']} / {plan['suite']}；种子：{plan['seeds']}；每回合上限：{plan['steps']} 帧。",
        "",
        "算法只接收公开 SDK 观测；评分使用原有私有评分器，阈值未放宽。耗时为进程内 step（含图像解码），不含工作进程传输、渲染与初始化。",
        "",
        "| 算法 | 成功 / 总数 | 成功率 | Wilson 95% 区间 | 非法换线 | 推理均值 ms | 结束原因 |",
        "|---|---:|---:|---|---:|---:|---|",
    ]
    for algorithm in dict.fromkeys(row["algorithm"] for row in reports):
        metrics = [row["metrics"] for row in reports if row["algorithm"] == algorithm]
        count, successes = len(metrics), sum(m["success"] for m in metrics)
        proportion, z = successes / count, 1.96
        denominator = 1 + z * z / count
        center = (proportion + z * z / (2 * count)) / denominator
        half = (
            z
            * (proportion * (1 - proportion) / count + z * z / (4 * count * count))
            ** 0.5
            / denominator
        )
        frames = sum(m["frames"] for m in metrics)
        timing = sum(
            (m["inference_ms"]["mean"] or 0) * m["frames"] for m in metrics
        ) / max(frames, 1)
        switches = sum(len(m["illegal_switches"] or []) for m in metrics)
        lines.append(
            f"| {algorithm} | {successes}/{count} | {proportion:.1%} | {center - half:.1%}–{center + half:.1%} | {switches} | {timing:.2f} | {dict(Counter(m['reason'] for m in metrics))} |"
        )
    lines += [
        "",
        "区间按回合二项采样计算；同一生成器的样本有相关性，不能解释为真实道路泛化保证。",
        "",
        "| 算法 | 场景族 | 成功 / 总数 | 平均进度 | 失败原因 |",
        "|---|---|---:|---:|---|",
    ]
    for algorithm, family in dict.fromkeys(
        (row["algorithm"], row["family"]) for row in reports
    ):
        metrics = [
            row["metrics"]
            for row in reports
            if row["algorithm"] == algorithm and row["family"] == family
        ]
        lines.append(
            f"| {algorithm} | {family} | {sum(m['success'] for m in metrics)}/{len(metrics)} | {np.mean([m['completion'] for m in metrics]):.1%} | {dict(Counter(m['reason'] for m in metrics if not m['success']))} |"
        )
    lines += [
        "",
        "逐回合结果、失败详情及最后一帧见 report.json / episodes；完整计划、代码与权重摘要见 plan.json。所有失败均进入分母。",
    ]
    (folder / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--algorithms", nargs="+", default=["temporal_pursuit"])
    parser.add_argument(
        "--families", nargs="+", default=list(FAMILIES), choices=list(FAMILIES)
    )
    parser.add_argument("--seeds", nargs="+", type=int, default=[7])
    parser.add_argument("--steps", type=int, default=4000)
    parser.add_argument(
        "--resolution", type=int, default=0, help="0 preserves the full 640×360 camera"
    )
    parser.add_argument("--jobs", type=int, default=4)
    parser.add_argument("--parameters", type=json.loads, default={})
    parser.add_argument(
        "--suite",
        choices=["core", "appearance", "camera", "occlusion", "offset", "custom"],
        default="core",
    )
    parser.add_argument(
        "--split", choices=["development", "validation", "test"], default="development"
    )
    parser.add_argument("--output", default="artifacts/algorithms/development")
    args = parser.parse_args()
    if args.suite == "custom":
        args.families = ["custom"]  # One distinct map per seed, never count duplicates.
    folder = Path(args.output)
    folder.mkdir(parents=True, exist_ok=True)
    if args.split == "test" and any(seed < 1001 for seed in args.seeds):
        parser.error(
            "测试集须使用保留种子 >=1001；开发和调参请使用 development / validation"
        )
    for algorithm in args.algorithms:
        if algorithm not in registry():
            parser.error(f"未知算法：{algorithm}")
        if not registry()[algorithm].entrypoint:
            parser.error(
                "进程内快速评测只支持本地 Python entrypoint；外部或 ZIP 算法请使用 python run.py benchmark"
            )
        if reason := registry()[algorithm].unavailable_reason():
            parser.error(reason)
    plan = {
        **vars(args),
        "timing": "in_process_inference",
        "environment": environment(),
        "evaluator_version": EVALUATOR_VERSION,
        "thresholds": THRESHOLDS,
        "code_sha256": {
            str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted((ROOT / "algorithms").rglob("*.py"))
        },
    }
    checkpoint = Path(
        args.parameters.get(
            "checkpoint", ROOT / "algorithms/learning/weights/driver.pt"
        )
    )
    if "cnn_gru" in args.algorithms and checkpoint.exists():
        plan["checkpoint_sha256"] = hashlib.sha256(checkpoint.read_bytes()).hexdigest()
    write_json(folder / "plan.json", plan)
    jobs = [
        (
            a,
            f,
            s,
            args.steps,
            args.resolution,
            args.parameters,
            args.split,
            args.suite,
            args.output,
        )
        for a in args.algorithms
        for f in args.families
        for s in args.seeds
    ]
    os.environ.update(OMP_NUM_THREADS="1", OPENBLAS_NUM_THREADS="1")
    with ProcessPoolExecutor(max_workers=args.jobs) as pool:
        reports = list(pool.map(evaluate, jobs))
    write_report(folder, plan, reports)
    for algorithm in args.algorithms:
        rows = [r for r in reports if r["algorithm"] == algorithm]
        print(
            algorithm,
            sum(r["metrics"]["success"] for r in rows),
            "/",
            len(rows),
            "success",
        )


if __name__ == "__main__":
    main()
