"""Reproducible complex-map supervision; never imported by a deployed policy.

Saved failure cases are development data. Validation and final tests use newly
generated geometries, not different camera views of the saved failure cases.
"""

import argparse
from concurrent.futures import ProcessPoolExecutor
import hashlib
import json
from pathlib import Path

import numpy as np

from pathlab.config import MapDesign, ObjectScatter, Scene, VehicleConfig
from pathlab.map_editor import MapRequest, build_scene
from pathlab.scenarios import PathBuilder, generate, validate_scene
from pathlab.scene_objects import scatter_objects
from pathlab.storage import write_json
from .data import collect_episode


KINDS = ("coil", "parallel_curve")


def custom_scene(kind, seed, motion="inertial_v2", split="development"):
    """Independent variable-length, variable-curvature geometric families."""
    rng = np.random.default_rng(seed)
    radius = float(rng.uniform(0.83, 1.30))
    if kind == "coil":
        width, height = rng.uniform(4.5, 7.5), rng.uniform(3.5, 5.5)
        gap = float(rng.uniform(0.40, 0.85))
        points = [
            [0, 0],
            [width, 0],
            [width, height],
            [-2.5, height],
            [-2.5, -gap],
            [width + gap, -gap],
            [width + gap, height + gap],
            [-2.5 - gap, height + gap],
        ]
        scene = build_scene(
            MapRequest(
                name="独立套圈几何",
                seed=seed,
                vehicle=VehicleConfig(motion_model=motion),
                design=MapDesign(waypoints=points, radius_m=radius),
            )
        )
    elif kind == "acquisition":
        scene = generate("straight", seed, split=split)
        scene.target_path = PathBuilder().segment(4).points
        separation = float(rng.uniform(0.25, 0.55))
        scene.distractors = []
        if seed % 4:
            side = float(rng.choice([-1, 1]))
            scene.distractors = [
                [[float(x), side * separation] for x in np.linspace(-0.4, 4.5, 124)]
            ]
    elif kind == "parallel_curve":
        builder = PathBuilder().segment(float(rng.uniform(2.8, 4.5)))
        builder.turn(float(rng.uniform(0.6, 1.25)), radius)
        builder.segment(float(rng.uniform(1, 2)))
        builder.turn(-float(rng.uniform(1, 1.8)), radius).segment(3)
        scene = generate("straight", seed, split=split)
        scene.target_path = builder.points
        points = np.asarray(builder.points)
        tangents = np.gradient(points, axis=0)
        normals = np.column_stack((-tangents[:, 1], tangents[:, 0]))
        normals /= np.linalg.norm(normals, axis=1, keepdims=True)
        separation = float(rng.uniform(0.28, 0.65))
        side = float(rng.choice([-1, 1]))
        scene.distractors = [(points + side * separation * normals).tolist()]
        scene.objects = []
    else:
        raise ValueError(f"未知复杂几何：{kind}")
    scene.family = f"complex_{kind}_{motion}"
    scene.split = split
    scene.vehicle.motion_model = motion
    scene.render_version = "2" if motion == "kinematic_v1" else "3"
    if seed % 2:
        scene.target_path = [[x, -y] for x, y in scene.target_path]
        scene.distractors = [[[x, -y] for x, y in line] for line in scene.distractors]
    scene.initial_pose.y_m = float(rng.uniform(-0.2, 0.2))
    scene.initial_pose.yaw_rad = float(rng.uniform(-0.09, 0.09))
    if kind == "acquisition":
        scene.initial_pose.y_m = float(rng.uniform(-0.33, 0.30))
        scene.initial_pose.yaw_rad = float(rng.uniform(-0.13, 0.13))
    scene.camera.pitch_down_rad = 0.38 if seed % 3 else 0.52
    scene.objects = []
    errors = validate_scene(scene)
    if errors:
        raise ValueError("复杂几何无效：" + "; ".join(errors))
    return scene


def augment(scene, seed, motion, family):
    """Change geometry scale, handedness, camera, actuation and appearance."""
    scene = scene.model_copy(deep=True)
    rng = np.random.default_rng(seed + (1000 if motion == "inertial_v2" else 0))
    scene.seed, scene.family = seed, family
    scene.vehicle.motion_model = motion
    scene.render_version = "2" if motion == "kinematic_v1" else "3"
    if seed % 3:
        scale = float(rng.uniform(0.94, 1.15))
        mirror = -1 if seed % 2 else 1
        scene.target_path = [
            [x * scale, y * scale * mirror] for x, y in scene.target_path
        ]
        scene.distractors = [
            [[x * scale, y * scale * mirror] for x, y in line]
            for line in scene.distractors
        ]
        scene.initial_pose.y_m = float(rng.uniform(-0.18, 0.18))
        scene.initial_pose.yaw_rad = float(rng.uniform(-0.08, 0.08))
    # Train both camera sampling chains. A resized 320px rendering is not
    # identical to rendering at the student's actual 640px camera resolution.
    scene.camera.width = 640 if seed % 2 == 0 else 320
    scene.camera.height = scene.camera.width * 9 // 16
    scene.camera.pitch_down_rad = (
        (0.38 if seed % 4 == 0 else 0.52)
        if seed % 2 == 0
        else float(rng.uniform(0.34, 0.59))
    )
    scene.camera.height_m = float(rng.uniform(0.44, 0.54))
    scene.camera.horizontal_fov_deg = float(rng.uniform(76, 87))
    scene.appearance.line_width_m = float(rng.uniform(0.046, 0.077))
    scene.appearance.illumination = float(rng.uniform(0.72, 1.12))
    scene.appearance.noise_std = float(rng.uniform(0, 2))
    scene.appearance.blur_sigma = float(rng.uniform(0, 0.45))
    scene.vehicle.speed_response_s = float(rng.uniform(0.14, 0.23))
    scene.vehicle.yaw_response_s = float(rng.uniform(0.08, 0.17))
    scene.vehicle.lateral_response_s = float(rng.uniform(0.07, 0.14))
    scene.vehicle.jerk_limit_mps3 = float(rng.uniform(4.5, 7.5))
    if "acquisition" in family:
        scene.initial_pose.y_m = float(rng.uniform(-0.33, 0.30))
        scene.initial_pose.yaw_rad = float(rng.uniform(-0.13, 0.13))
    scene.objects = scatter_objects(
        scene, ObjectScatter(count=0 if seed % 3 == 0 else 4, spread_m=5)
    )
    errors = validate_scene(scene)
    if errors:
        raise ValueError("增强场景无效：" + "; ".join(errors))
    return scene


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", required=True)
    parser.add_argument("--scene-files", nargs="*", default=[])
    parser.add_argument("--source-episodes", type=int, default=6)
    parser.add_argument("--generated-episodes", type=int, default=4)
    parser.add_argument(
        "--kinds", nargs="+", choices=[*KINDS, "acquisition"], default=list(KINDS)
    )
    parser.add_argument("--checkpoint", default=None)
    parser.add_argument("--beta", type=float, default=0.5)
    parser.add_argument("--jobs", type=int, default=6)
    args = parser.parse_args()
    if not 1 <= args.source_episodes <= 100 or not 1 <= args.generated_episodes <= 100:
        parser.error("开发种子仅允许 0–99")
    if not 0 <= args.beta <= 1 or args.jobs < 1:
        parser.error("beta 须在 0..1；jobs 须为正数")
    folder = Path(args.data)
    if (folder / "manifest.json").exists():
        raise ValueError("请使用新目录；不覆盖既有采集记录")
    folder.mkdir(parents=True, exist_ok=True)
    jobs = []
    for source in args.scene_files:
        path = Path(source)
        content = json.loads(path.read_text())
        scene = Scene.model_validate(content.get("scene", content))
        if scene.split == "test":
            raise ValueError("保留测试场景不可作为开发训练数据")
        if scene.task_hint.kind != "marker" or scene.task_hint.marker_rgb != (
            34,
            160,
            94,
        ):
            raise ValueError("当前学习模型仅支持默认绿色起点标记")
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        for motion in ("kinematic_v1", "inertial_v2"):
            for seed in range(args.source_episodes):
                family = f"development_case_{digest[:8]}_{motion}"
                case = augment(scene, seed, motion, family)
                case.split = "development"
                jobs.append(
                    (
                        case,
                        {
                            "source": str(path),
                            "sha256": digest,
                            "role": "development_case",
                        },
                    )
                )
    for kind in args.kinds:
        for motion in ("kinematic_v1", "inertial_v2"):
            for split, seeds in (
                ("development", range(args.generated_episodes)),
                ("validation", (201, 202)),
            ):
                for seed in seeds:
                    scene = custom_scene(kind, seed, motion, split)
                    scene = augment(scene, seed, motion, scene.family)
                    jobs.append(
                        (scene, {"generator": kind, "role": "independent_geometry"})
                    )
    plan = {
        **vars(args),
        "held_out_seeds": [6001, 6002, 6003],
        "held_out_rule": "no collection or model selection on held-out geometries",
        "scene_count": len(jobs),
    }
    write_json(folder / "collection-plan.json", plan)
    tasks = [
        {
            "scene": scene.model_dump(),
            "folder": str(folder),
            "checkpoint": args.checkpoint,
            "beta": args.beta,
            "provenance": provenance,
        }
        for scene, provenance in jobs
    ]
    with ProcessPoolExecutor(max_workers=args.jobs) as pool:
        episodes = list(pool.map(collect_episode, tasks))
    write_json(
        folder / "manifest.json",
        {
            "format_version": 1,
            "episodes": episodes,
            "privileged_teacher": True,
            "control_interval_s": 0.1,
            "test_seeds_excluded": [6001, 6002, 6003],
        },
    )
    print("Collected", sum(item["frames"] for item in episodes), "frames", flush=True)


if __name__ == "__main__":
    main()
