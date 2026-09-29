"""Run the real worker/path-executor pipeline on the classroom curriculum."""
# ruff: noqa: E402

import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from pathlab.config import RunConfig
from pathlab.engine import Run
from pathlab.scenarios import FAMILIES, generate
from pathlab.storage import write_json


def evaluate(job):
    family, seed, destination, algorithm = job
    scene = generate(family, seed)
    # Persist all real output paths, controls and private evaluation in an
    # isolated directory. No teacher/student saved maps or records are touched.
    root = destination / f"{algorithm}-{family}-{seed}"
    run = Run(
        RunConfig(
            algorithm=algorithm,
            execution="path",
            scene=scene,
            realtime=False,
            max_steps=6000,
            timeout_s=2,
        ),
        root,
        headless=True,
    )
    run.start()
    run.control("resume")
    run.thread.join(360)
    if run.thread.is_alive():
        run.control("stop")
        run.thread.join(10)
        raise RuntimeError(f"测试超时：{family}/{seed}")
    metrics = run.store.manifest["metrics"]
    result = {
        "family": family,
        "seed": seed,
        "algorithm": algorithm,
        "episode_id": run.id,
        "reason": run.reason,
        "metrics": metrics,
        "failures": run.failures,
    }
    assert all(
        r["output"] is None or r["output"]["action"] is None for r in run.records
    )
    print(
        f"{algorithm} {family}/{seed}: {run.reason}, completion={metrics['completion']:.3f}",
        flush=True,
    )
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--families", nargs="+", default=list(FAMILIES))
    parser.add_argument("--seeds", nargs="+", type=int, default=[7, 1009, 42])
    parser.add_argument("--jobs", type=int, default=4)
    parser.add_argument(
        "--output", type=Path, default=ROOT / ".cache/classroom-acceptance"
    )
    args = parser.parse_args()
    # Each invocation keeps its own records, including failed earlier trials.
    args.output.mkdir(parents=True, exist_ok=True)
    destination = Path(tempfile.mkdtemp(prefix="trial-", dir=args.output))
    paths = [
        *sorted((ROOT / "pathlab").glob("*.py")),
        *sorted((ROOT / "algorithms").glob("*.py")),
    ]
    plan = {
        "families": args.families,
        "seeds": args.seeds,
        "source_sha256": {
            str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in paths
        },
    }
    write_json(destination / "plan.json", plan)
    jobs = [
        (f, s, destination, "temporal_path") for f in args.families for s in args.seeds
    ]
    jobs += [("straight", args.seeds[0], destination, "straight_path")]
    with ThreadPoolExecutor(max_workers=args.jobs) as pool:
        reports = list(pool.map(evaluate, jobs))
    write_json(destination / "summary.json", reports)
    passed = sum(row["metrics"]["success"] is True for row in reports)
    print(
        json.dumps(
            {"passed": passed, "total": len(reports), "report": str(destination)},
            ensure_ascii=False,
        )
    )
    return int(passed != len(reports))


if __name__ == "__main__":
    raise SystemExit(main())
