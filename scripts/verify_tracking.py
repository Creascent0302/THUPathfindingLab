"""Reproducible, obstacle-free closed-loop acceptance for both temporal drivers.

python scripts/verify_tracking.py --jobs 4 --output .cache/tracking-acceptance
Every case is frozen before execution; failures remain in the report and exit code.
"""

# ruff: noqa: E402
from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
import hashlib
import math
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pathlab.config import Scene
from pathlab.scenarios import FAMILIES, PathBuilder, generate, validate_scene
from pathlab.storage import write_json
from scripts.evaluate_algorithms import evaluate


def cases():
    result = {}
    for family in FAMILIES:
        for seed in (7, 1009):
            result[f"{family}-{seed}"] = generate(family, seed)
    for name in (
        "user-original",
        "user-actual",
        "user-0920",
        "close-lines",
        "steep-camera",
        "coil-6001-inertial_v2",
        "coil-6002-inertial_v2",
        "coil-6001-kinematic_v1",
        "parallel_curve-6001-inertial_v2",
        "parallel_curve-6002-inertial_v2",
    ):
        result[name] = Scene.model_validate_json(
            (ROOT / "scenarios" / "challenges" / f"{name}.json").read_text()
        )
    # Include the latest actual user maps, without modifying files or obstacles in them.
    for file in sorted((ROOT / "artifacts" / "maps").glob("*.json")):
        scene = Scene.model_validate_json(file.read_text())
        result[f"saved-{file.stem[:8]}"] = scene
    base = result["close-lines"]
    for name, camera, appearance in (
        ("camera-steep-wide", {"pitch_down_rad": 0.95, "horizontal_fov_deg": 110}, {}),
        ("camera-shallow", {"pitch_down_rad": 0.20, "horizontal_fov_deg": 80}, {}),
        ("camera-low-resolution", {"width": 320, "height": 180}, {}),
        (
            "dim-noisy-thin",
            {},
            {
                "illumination": 0.50,
                "shadow": 0.4,
                "noise_std": 6,
                "blur_sigma": 0.6,
                "line_width_m": 0.03,
            },
        ),
        ("bright-thick", {}, {"illumination": 1.25, "line_width_m": 0.15}),
        ("marker-hidden", {}, {"marker_enabled": False}),
    ):
        scene = (
            generate("hairpin", 1009)
            if name == "bright-thick"
            else base.model_copy(deep=True)
        )
        scene.camera = scene.camera.model_copy(update=camera)
        scene.appearance = scene.appearance.model_copy(update=appearance)
        result[name] = scene
    # Legal curvature at 2% above the vehicle minimum, immediate and chained turns.
    minimum = base.vehicle.wheelbase_m / math.tan(base.vehicle.max_steering_rad)
    for lead in (0.0, 0.35, 1.0):
        for sign in (-1, 1):
            builder = PathBuilder()
            if lead:
                builder.segment(lead)
            builder.turn(sign * math.pi / 2, minimum * 1.025).segment(1.4)
            builder.turn(-sign * math.pi, minimum * 1.025).segment(2.0)
            scene = generate("straight", 1009)
            scene.target_path = builder.points
            scene.distractors = []
            scene.appearance.marker_enabled = False
            result[f"minimum-radius-{lead}-{sign}"] = scene
    # Rotate/translate the actual geometry; algorithms only see the camera image.
    for angle in (math.pi / 2, math.pi, -0.8):
        scene = base.model_copy(deep=True)
        rotation = np.array(
            [[math.cos(angle), -math.sin(angle)], [math.sin(angle), math.cos(angle)]]
        )

        def transform(points):
            return (np.asarray(points) @ rotation.T + [2, -3]).tolist()

        scene.target_path = transform(scene.target_path)
        scene.distractors = [transform(points) for points in scene.distractors]
        result[f"rotated-{angle:.2f}"] = scene
    # A legal nearby line alongside the initial arc tests identity, not mere distance.
    scene = result["minimum-radius-0.35-1"].model_copy(deep=True)
    scene.distractors = [[[x, -0.18] for x in np.linspace(0, 6, 151)]]
    result["bend-adjacent-start"] = scene
    for name, scene in result.items():
        scene = scene.model_copy(deep=True).at_start()
        scene.objects = []
        scene.appearance.occlusion = False
        scene.name = name
        errors = validate_scene(scene)
        if errors:
            raise ValueError(f"Invalid acceptance case {name}: {errors}")
        yield name, scene


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--jobs", type=int, default=4)
    parser.add_argument(
        "--output", type=Path, default=ROOT / ".cache/tracking-acceptance"
    )
    parser.add_argument(
        "--cases", nargs="+", help="Optional case names for reproducing a failure"
    )
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    folder = args.output / "scenes"
    folder.mkdir(exist_ok=True)
    jobs = []
    scene_hashes = {}
    for name, scene in cases():
        if args.cases and name not in args.cases:
            continue
        file = folder / f"{name}.json"
        write_json(file, scene.model_dump())
        scene_hashes[name] = hashlib.sha256(file.read_bytes()).hexdigest()
        for algorithm in ("temporal_pursuit", "temporal_mpc"):
            jobs.append(
                (
                    algorithm,
                    name,
                    scene.seed,
                    4000,
                    0,
                    {},
                    "validation",
                    "core",
                    str(args.output),
                    str(file),
                    None,
                )
            )
    if not jobs:
        parser.error("No matching cases")
    code_hashes = {
        str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
        for folder in (ROOT / "algorithms/modular", ROOT / "pathlab")
        for p in sorted(folder.glob("*.py"))
    }
    write_json(
        args.output / "plan.json",
        {
            "scene_sha256": scene_hashes,
            "code_sha256": code_hashes,
            "runs": len(jobs),
            "objects": False,
        },
    )
    rows = []
    with ProcessPoolExecutor(max_workers=args.jobs) as pool:
        for completed in as_completed([pool.submit(evaluate, job) for job in jobs]):
            report = completed.result()
            rows.append(
                {
                    key: report[key]
                    for key in (
                        "algorithm",
                        "case",
                        "seed",
                        "metrics",
                        "failures",
                        "wall_s",
                    )
                }
            )
            write_json(args.output / "summary.json", rows)
    failures = [
        r
        for r in rows
        if not r["metrics"]["success"]
        or r["failures"]
        or r["metrics"]["illegal_switches"]
    ]
    print(
        f"Acceptance: {len(rows) - len(failures)}/{len(rows)} passed; {args.output / 'summary.json'}",
        flush=True,
    )
    raise SystemExit(bool(failures))


if __name__ == "__main__":
    main()
