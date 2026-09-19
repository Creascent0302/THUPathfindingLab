"""Local launcher, reproducible benchmark, scene generation, and environment checks."""

from __future__ import annotations

import argparse
from collections import Counter
import csv
import json
from pathlib import Path
import runpy
import sys
import time

import numpy as np

from .config import RunConfig
from .engine import Run
from .registry import ROOT, registry
from .scenarios import FAMILIES, generate
from .storage import environment, write_json


def benchmark(args):
    specs = registry()
    for name in args.algorithms:
        if name not in specs:
            raise SystemExit(f"未注册算法：{name}")
        if reason := specs[name].unavailable_reason():
            raise SystemExit(reason)
    plan = {
        "algorithms": args.algorithms,
        "seeds": args.seeds,
        "families": args.families,
        "max_steps": args.steps,
        "split": args.split,
        "timing": "worker_protocol_round_trip",
        "disclaimer": "实际独立进程闭环评测；保留失败，性能结论仅适用于列出的场景集合。",
    }
    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=True)
    write_json(out / "plan.json", plan)
    records = []
    start = time.perf_counter()
    for algorithm in args.algorithms:
        capability = specs[algorithm].capabilities[0]
        for family in args.families:
            for seed in args.seeds:
                scene = generate(family, seed, split=args.split)
                run = Run(
                    RunConfig(
                        algorithm=algorithm,
                        execution=capability,
                        family=family,
                        seed=seed,
                        scene=scene,
                        max_steps=args.steps,
                        realtime=False,
                    ),
                    ROOT / "artifacts",
                    headless=True,
                )
                run.start()
                run.control("resume")
                try:
                    while run.thread.is_alive():
                        run.thread.join(0.5)
                except KeyboardInterrupt:
                    run.control("stop")
                    run.thread.join(5)
                    raise
                metrics = run.store.manifest["metrics"]
                row = {
                    "algorithm": algorithm,
                    "execution": capability,
                    "family": family,
                    "seed": seed,
                    "run_id": run.id,
                    "state": run.state,
                    "metrics": metrics,
                }
                records.append(row)
                print(
                    f"{algorithm:14s} {family:12s} seed={seed:<6} {run.state:10s} {run.reason:20s} completion={metrics['completion']:.3f}",
                    flush=True,
                )
    report = {
        "plan": plan,
        "environment": environment(),
        "elapsed_wall_s": time.perf_counter() - start,
        "runs": records,
    }
    write_json(out / "report.json", report)
    with (out / "report.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            [
                "algorithm",
                "family",
                "seed",
                "state",
                "success",
                "completion",
                "reason",
                "run_id",
            ],
        )
        writer.writeheader()
        for row in records:
            writer.writerow(
                {
                    **{
                        key: row[key]
                        for key in ["algorithm", "family", "seed", "state", "run_id"]
                    },
                    **{
                        key: row["metrics"][key]
                        for key in ["success", "completion", "reason"]
                    },
                }
            )
    lines = [
        "# 算法独立进程运行报告",
        "",
        "此报告由实际运行生成，包含完整工作进程与 JSONL 通信开销；失败样本全部保留。",
        "",
        f"实际耗时：{report['elapsed_wall_s']:.1f} s；每回合最多 {args.steps} 步；仿真步长 0.05 s。",
        "",
        "| 算法 | 场景族 | 样本量 | 成功 | 平均有效进度 | 失败/结束原因 |",
        "|---|---|---:|---:|---:|---|",
    ]
    for algorithm in args.algorithms:
        for family in args.families:
            rows = [
                r
                for r in records
                if r["algorithm"] == algorithm and r["family"] == family
            ]
            reasons = Counter(r["metrics"]["reason"] for r in rows)
            lines.append(
                f"| {algorithm} | {FAMILIES[family]} | {len(rows)} | {sum(r['metrics']['success'] for r in rows)} | {np.mean([r['metrics']['completion'] for r in rows]):.1%} | {dict(reasons)} |"
            )
    lines.extend(
        [
            "",
            "场景、种子与阈值在运行前固定；详见 plan.json。原始每帧记录见 artifacts/runs/<run_id>/。",
            "",
            "本报告只代表给定集合。比较不同算法时应使用相同场景、步数、提示和评分阈值；停车、固定动作、分割探针不具有完整寻迹能力。",
        ]
    )
    (out / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"\n报告：{out / 'report.md'}")


def main():
    parser = argparse.ArgumentParser(description="智能交通创新实践 · 寻迹实验室")
    sub = parser.add_subparsers(dest="command")
    serve = sub.add_parser("serve", help="启动本地工作台")
    serve.add_argument("--port", type=int, default=8000)
    serve.add_argument("--host", default="127.0.0.1")
    sub.add_parser("doctor", help="检查运行环境")
    sub.add_parser("test", help="运行平台回归测试")
    scenes = sub.add_parser("scenes", help="生成八类场景 JSON")
    scenes.add_argument("--seeds", nargs="+", type=int, default=[7])
    scenes.add_argument("--output", default=str(ROOT / "scenarios"))
    bench = sub.add_parser("benchmark", help="确定性、无界面批量评测")
    bench.add_argument(
        "--algorithms",
        nargs="+",
        default=["temporal_pursuit", "temporal_mpc", "scanline_pid"],
    )
    bench.add_argument("--seeds", nargs="+", type=int, default=[201, 202])
    bench.add_argument(
        "--families", nargs="+", choices=list(FAMILIES), default=list(FAMILIES)
    )
    bench.add_argument("--steps", type=int, default=4000)
    bench.add_argument(
        "--split", choices=["development", "validation", "test"], default="validation"
    )
    bench.add_argument("--output", default=str(ROOT / "artifacts" / "benchmark"))
    learning = sub.add_parser(
        "learning", help="可选 CPU 学习：collect / fit（子命令后加 --help）"
    )
    learning.add_argument("arguments", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    if args.command in {None, "serve"}:
        import uvicorn
        from .api import create_app

        if not (ROOT / "frontend" / "dist" / "index.html").exists():
            raise SystemExit("前端未构建，请先运行 python scripts/setup.py")
        uvicorn.run(
            create_app(),
            host=getattr(args, "host", "127.0.0.1"),
            port=getattr(args, "port", 8000),
            log_level="info",
        )
    elif args.command == "doctor":
        print(
            json.dumps(
                {
                    **environment(),
                    "frontend_built": (
                        ROOT / "frontend" / "dist" / "index.html"
                    ).exists(),
                    "algorithms": list(registry()),
                },
                indent=2,
                ensure_ascii=False,
            )
        )
    elif args.command == "test":
        import pytest

        raise SystemExit(pytest.main([str(ROOT / "tests"), "-q"]))
    elif args.command == "scenes":
        folder = Path(args.output)
        folder.mkdir(parents=True, exist_ok=True)
        for family in FAMILIES:
            for seed in args.seeds:
                write_json(
                    folder / f"{family}-{seed}.json",
                    generate(family, seed).model_dump(),
                )
        print(f"已生成 {len(FAMILIES) * len(args.seeds)} 个合法场景：{folder}")
    elif args.command == "learning":
        if registry()["cnn_gru"].runtime_requirements:
            import importlib.util

            if importlib.util.find_spec("torch") is None:
                raise SystemExit(
                    "请先运行 python scripts/setup_learning.py 安装可选 CPU 学习环境"
                )
        sys.argv = ["pathlab learning", *args.arguments]
        runpy.run_module("algorithms.learning.train", run_name="__main__")
    else:
        benchmark(args)


if __name__ == "__main__":
    main()
