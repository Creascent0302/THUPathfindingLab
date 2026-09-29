"""New experiments start on the route; legacy records remain immutable."""

import math

import numpy as np
import pytest
from fastapi.testclient import TestClient

from algorithms.modular.algorithm import TemporalMPC, TemporalPursuit
from pathlab.api import create_app
from pathlab.config import RunConfig
from pathlab.evaluation import Evaluator
from pathlab.scenarios import generate, validate_scene
from pathlab.sdk import Observation, TaskHint
from pathlab.simulation import Renderer, Vehicle


@pytest.mark.parametrize("angle", [0, math.pi / 2, math.pi, -0.8])
def test_start_matches_arrow_and_does_not_mutate_source(angle):
    source = generate("bend", 7)
    c, s = math.cos(angle), math.sin(angle)
    source.target_path = (
        np.array(source.target_path) @ np.array([[c, s], [-s, c]]) + [2, -3]
    ).tolist()
    original = source.model_dump_json()
    scene = source.at_start()
    assert scene.initial_pose.x_m == 2
    assert scene.initial_pose.y_m == -3
    assert (
        abs(
            math.atan2(
                math.sin(scene.initial_pose.yaw_rad - angle),
                math.cos(scene.initial_pose.yaw_rad - angle),
            )
        )
        < 1e-10
    )
    assert scene.start_mode == "on_path"
    assert scene.task_hint.kind == "none"
    assert validate_scene(scene) == []
    assert scene.at_start() == scene
    assert source.model_dump_json() == original
    vehicle = Vehicle(scene.vehicle, scene.initial_pose)
    assert vehicle.state.speed_mps == 0
    evaluation = Evaluator(scene).update(vehicle.state, 0)
    assert evaluation["phase"] == "tracking"
    assert evaluation["progress_m"] == 0


@pytest.mark.parametrize("policy_type", [TemporalPursuit, TemporalMPC])
def test_unmarked_parallel_lines_start_tracking_without_acquisition(policy_type):
    scene = generate("close_lines", 1009).at_start()
    scene.appearance.marker_enabled = False
    scene.objects = []
    renderer = Renderer(scene)
    observation = Observation.from_rgb(
        renderer.render(scene.initial_pose, 0),
        episode_id="on-path",
        frame_id=0,
        timestamp_s=0,
        dt_s=scene.dt_s,
        calibration=renderer.camera.calibration(),
        task_hint=scene.task_hint,
    )
    algorithm = policy_type()
    algorithm.initialize(
        {}, {"start_on_path": True, "vehicle_limits": scene.vehicle.model_dump()}
    )
    algorithm.reset(observation, observation.task_hint)
    output = algorithm.step(observation)
    assert output.status == "TRACK"
    assert output.action.speed_mps > 0
    assert np.max(np.abs(np.array(output.local_path_m)[:, 1])) < 0.06


def test_stale_workbench_hint_cannot_block_real_worker(execute):
    scene = generate("parallel", 7)
    original = scene.model_dump_json()
    run = execute(
        RunConfig(
            algorithm="temporal_pursuit",
            scene=scene,
            task_hint=TaskHint(kind="point", point_px=(-100, -100)),
            max_steps=4,
            realtime=False,
        )
    )
    assert not run.failures
    assert run.scene == scene.at_start()
    assert run.config.task_hint.kind == "none"
    first = run.records[0]
    assert first["pose_before"]["x_m"] == 0
    assert first["pose_before"]["y_m"] == 0
    assert first["output"]["status"] == "TRACK"
    assert first["evaluation"]["phase"] == "tracking"
    assert scene.model_dump_json() == original


def test_saved_map_preview_and_new_run_agree_without_overwriting_file(tmp_path):
    import json

    scene = generate("parallel", 7)
    maps = tmp_path / "maps"
    maps.mkdir()
    file = maps / ("a" * 32 + ".json")
    original = scene.model_dump_json()
    file.write_text(original)
    with TestClient(create_app(tmp_path)) as client:
        loaded = client.get("/api/maps").json()[0]["scene"]
        preview = client.post("/api/preview", json=loaded)
        assert preview.status_code == 200, preview.text
        assert preview.json()["scene"] == scene.at_start().model_dump(mode="json")
        run = client.post(
            "/api/runs", json={"algorithm": "manual", "scene": loaded}
        ).json()
        assert run["scene"] == preview.json()["scene"]
        client.post(f"/api/runs/{run['id']}/control", json={"command": "stop"})
        assert client.get("/api/hosting").status_code == 404
    assert json.loads(file.read_text()) == json.loads(original)


def test_immediate_tight_bend_requires_observable_camera_and_keeps_identity():
    from pathlab.scenarios import PathBuilder

    scene = generate("straight", 1009)
    radius = (
        scene.vehicle.wheelbase_m / math.tan(scene.vehicle.max_steering_rad) * 1.025
    )
    scene.target_path = (
        PathBuilder()
        .turn(math.pi / 2, radius)
        .segment(1.4)
        .turn(-math.pi, radius)
        .segment(2)
        .points
    )
    scene.objects = []
    scene.appearance.marker_enabled = False
    scene = scene.at_start()
    hidden = scene.model_copy(deep=True)
    hidden.camera.pitch_down_rad = 0.38
    hidden.camera.horizontal_fov_deg = 80
    assert any("相机看不到" in error for error in validate_scene(hidden))
    assert validate_scene(scene) == []
    renderer, vehicle = Renderer(scene), Vehicle(scene.vehicle, scene.initial_pose)
    policy = TemporalPursuit()
    policy.initialize(
        {}, {"start_on_path": True, "vehicle_limits": scene.vehicle.model_dump()}
    )
    for frame in range(30):
        obs = Observation.from_rgb(
            renderer.render(vehicle.state, frame),
            episode_id="tight",
            frame_id=frame,
            timestamp_s=frame * scene.dt_s,
            dt_s=scene.dt_s,
            calibration=renderer.camera.calibration(),
            task_hint=scene.task_hint,
        )
        if frame == 0:
            policy.reset(obs, obs.task_hint)
        output = policy.step(obs)
        assert output.status == "TRACK"
        assert not output.debug["prediction_only"]
        vehicle.advance(output.action, scene.dt_s)
    assert vehicle.state.yaw_rad > 0.5


@pytest.mark.parametrize("algorithm", ["temporal_pursuit", "temporal_mpc"])
def test_real_worker_completes_tight_bend_from_start(execute, algorithm):
    from pathlab.scenarios import PathBuilder

    scene = generate("straight", 1009).at_start()
    radius = (
        scene.vehicle.wheelbase_m / math.tan(scene.vehicle.max_steering_rad) * 1.025
    )
    scene.target_path = PathBuilder().turn(math.pi / 2, radius).segment(1.5).points
    scene.objects = []
    scene.appearance.marker_enabled = False
    run = execute(
        RunConfig(algorithm=algorithm, scene=scene, max_steps=600, realtime=False)
    )
    assert not run.failures
    assert run.reason == "success"
    assert not run.evaluator.switches
    assert run.evaluator.acquired_at == 0
    assert run.records[0]["output"]["status"] == "TRACK"
    assert run.records[-1]["pose"]["speed_mps"] == 0
