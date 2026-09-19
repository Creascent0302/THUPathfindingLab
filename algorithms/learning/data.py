"""Privileged training supervision. This module is NEVER imported by deployment."""

from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from types import SimpleNamespace

import cv2
import numpy as np

from pathlab.evaluation import OrderedPath
from pathlab.scenarios import FAMILIES, generate, validate_scene
from pathlab.sdk import Action, Observation
from pathlab.simulation import Renderer, Vehicle, world_to_vehicle
from pathlab.storage import write_json
from algorithms.modular.control import Pursuit
from .model import context_input, image_input


class TrainingExpert:
    def __init__(self, scene):
        self.route = OrderedPath(scene.target_path)
        self.progress = 0.0
        self.controller = Pursuit(scene.vehicle.model_dump(), 0.8)

    def action(self, state):
        self.progress, error, _ = self.route.project(
            [state.x_m, state.y_m], max(0, self.progress - 0.3), self.progress + 1
        )
        points = self.route.points[
            (self.route.arc >= max(0, self.progress - 0.2))
            & (self.route.arc <= self.progress + 4)
        ]
        if len(points) < 2:
            points = self.route.points[-2:]
        local = world_to_vehicle(points, state)
        motion = SimpleNamespace(
            speed=state.speed_mps, steering=state.steering_angle_rad
        )
        return (
            self.controller.command(local, 1, motion),
            error,
            self.route.total - self.progress,
        )


def collect_episode(job):
    family, seed, split, folder, checkpoint, beta = job
    cv2.setNumThreads(1)
    rng = np.random.default_rng(seed + list(FAMILIES).index(family) * 10000)
    scene = generate(family, seed, split=split)
    scene.camera.width, scene.camera.height = 320, 180
    scene.appearance.line_rgb = tuple([int(rng.integers(20, 75))] * 3)
    scene.appearance.ground_rgb = tuple([int(rng.integers(200, 240))] * 3)
    scene.appearance.line_width_m = float(rng.uniform(0.045, 0.085))
    scene.appearance.illumination = float(rng.uniform(0.7, 1.12))
    scene.appearance.shadow = float(rng.uniform(0, 0.3))
    scene.appearance.noise_std = float(rng.uniform(0, 3))
    scene.appearance.blur_sigma = float(rng.uniform(0, 0.65))
    scene.camera.pitch_down_rad = float(rng.uniform(0.33, 0.47))
    scene.camera.height_m = float(rng.uniform(0.43, 0.53))
    if scene.vehicle.motion_model == "inertial_v2":
        # Teach recovery across moderate actuator variations while retaining
        # the same public camera-only deployment boundary.
        scene.vehicle.speed_response_s = float(rng.uniform(0.14, 0.22))
        scene.vehicle.yaw_response_s = float(rng.uniform(0.09, 0.16))
        scene.vehicle.lateral_response_s = float(rng.uniform(0.07, 0.14))
        scene.vehicle.jerk_limit_mps3 = float(rng.uniform(4.5, 7.5))
    if validate_scene(scene):
        scene.camera.pitch_down_rad, scene.camera.height_m = 0.38, 0.48
    renderer, vehicle, expert = (
        Renderer(scene),
        Vehicle(scene.vehicle, scene.initial_pose),
        TrainingExpert(scene),
    )
    limits = scene.vehicle.model_dump()
    student = None
    if checkpoint:
        from .algorithm import RecurrentPolicy

        student = RecurrentPolicy()
        student.initialize({"checkpoint": checkpoint}, {"vehicle_limits": limits})
    previous = np.zeros(2, np.float32)
    images, contexts, actions, valid = [], [], [], []
    reason = "step_limit"
    for step in range(1200):
        truth_action, error, remaining = expert.action(vehicle.state)
        if (error > 1.2 and step > 35) or (remaining < 0.12 and step > 10):
            reason = (
                "teacher_complete" if remaining < 0.12 else "left_training_corridor"
            )
            break
        rgb = renderer.render(vehicle.state, step * 2)
        obscured = step > 15 and step % 170 in range(90, 94) and rng.random() < 0.65
        if obscured:
            rgb[:] = (
                np.array(scene.appearance.ground_rgb) * scene.appearance.illumination
            )
        images.append(image_input(rgb, scene.task_hint, step == 0))
        contexts.append(context_input(limits, previous, 0.1))
        target = np.array(
            [
                truth_action.steering_angle_rad / limits["max_steering_rad"],
                truth_action.speed_mps / min(1.0, limits["max_speed_mps"]),
            ],
            np.float32,
        )
        if obscured:
            target[1] = 0
        actions.append(target)
        valid.append(0.0 if obscured else 1.0)
        behavior = truth_action.model_copy()
        if student:
            obs = Observation.from_rgb(
                rgb,
                episode_id="collection",
                frame_id=step * 2,
                timestamp_s=step * 0.1,
                dt_s=0.05,
                calibration=renderer.camera.calibration(),
                task_hint=scene.task_hint,
            )
            if step == 0:
                student.reset(obs, obs.task_hint)
            prediction = student.step(obs)
            if rng.random() > beta:
                behavior = prediction.action.model_copy()
                if prediction.status in {
                    "LOST",
                    "AMBIGUOUS",
                    "ERROR",
                    "UNINITIALIZED",
                    "FINISHED",
                }:
                    behavior = Action(steering_angle_rad=0, speed_mps=0)
        else:
            # Correlated steering perturbations produce real recovery trajectories.
            phase = step % 110
            if 35 <= phase < 42:
                behavior.steering_angle_rad += 0.14 * (
                    1 if (step // 110 + seed) % 2 else -1
                )
        if obscured:
            behavior.speed_mps = 0
        previous = np.array(
            [behavior.steering_angle_rad, behavior.speed_mps], np.float32
        )
        if student:
            student.previous = previous.copy()
        for _ in range(2):
            vehicle.advance(behavior, 0.05)
    if student:
        student.close()
    file = Path(folder) / f"{split}-{family}-{seed}.npz"
    np.savez_compressed(
        file,
        images=np.asarray(images, np.uint8),
        context=np.asarray(contexts, np.float32),
        actions=np.asarray(actions, np.float32),
        visible=np.asarray(valid, np.float32),
    )
    item = {
        "file": file.name,
        "family": family,
        "seed": seed,
        "split": split,
        "frames": len(images),
        "reason": reason,
        "scene": scene.model_dump(),
        "teacher": "privileged_ordered_path_pursuit",
        "behavior_checkpoint": checkpoint,
        "motion_model": scene.vehicle.motion_model,
        "render_version": scene.render_version,
    }
    print(file.name, len(images), reason, flush=True)
    return item


def collect(args):
    folder = Path(args.data)
    folder.mkdir(parents=True, exist_ok=True)
    jobs = [
        (f, s, split, str(folder), args.checkpoint, args.beta)
        for f in FAMILIES
        for split, seeds in (
            ("development", range(args.episodes_per_family)),
            ("validation", range(201, 201 + args.validation_seeds)),
        )
        for s in seeds
    ]
    if (folder / "manifest.json").exists():
        raise ValueError("数据目录已有 manifest，请使用新的目录，避免覆盖训练记录")
    write_json(folder / "collection-plan.json", vars(args))
    with ProcessPoolExecutor(max_workers=args.jobs) as pool:
        episodes = list(pool.map(collect_episode, jobs))
    write_json(
        folder / "manifest.json",
        {
            "format_version": 1,
            "episodes": episodes,
            "privileged_teacher": True,
            "control_interval_s": 0.1,
            "test_seeds_excluded": [1001, 1002, 1003, 1004, 1005, 5001, 5002, 5003],
        },
    )
    print("Collected", sum(e["frames"] for e in episodes), "frames")
