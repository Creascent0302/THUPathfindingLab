import time
import threading

import pytest

from pathlab.config import RunConfig, SceneObject
from pathlab.engine import Run, RunManager
from pathlab.registry import PluginSpec, registry
from pathlab.scenarios import generate
from pathlab.sdk import Action
from pathlab.simulation import AppliedAction
from .conftest import wait_until


FAULT = PluginSpec(
    id="fault",
    name="故障注入",
    version="1",
    capabilities=["action"],
    entrypoint="tests.faults:Fault",
)


def test_terminal_status_is_published_only_after_result_is_saved(tmp_path, monkeypatch):
    run = Run(
        RunConfig(algorithm="manual", max_steps=1, realtime=False),
        tmp_path,
        headless=True,
    )
    saving, release = threading.Event(), threading.Event()
    finish = run.store.finish

    def delayed_finish(*args):
        saving.set()
        if not release.wait(5):
            raise AssertionError("test did not release result writer")
        finish(*args)

    monkeypatch.setattr(run.store, "finish", delayed_finish)
    run.start()
    try:
        run.control("resume")
        assert saving.wait(5)
        assert run.state == "running"
        assert run.store.manifest["metrics"] is None
        release.set()
        run.thread.join(5)
        assert run.state == "completed"
        assert run.store.manifest["metrics"]["reason"] == "episode_timeout"
        assert run.store.rows.closed
    finally:
        release.set()
        run.control("stop")
        run.thread.join(5)


def test_finishing_then_coasting_into_obstacle_is_not_success(execute):
    scene = generate("straight", 7)
    scene.target_path = [(i * 0.04, 0) for i in range(51)]
    scene.initial_pose.x_m = -1.5
    scene.initial_pose.y_m = scene.initial_pose.yaw_rad = 0
    scene.camera.width, scene.camera.height = 160, 90
    scene.vehicle.braking_mps2 = 0.3
    scene.objects = [SceneObject(kind="box", x_m=2.8, y_m=0, length_m=0.1)]
    run = execute(
        RunConfig(
            algorithm="constant",
            scene=scene,
            parameters={"speed_mps": 0.8},
            max_steps=300,
            realtime=False,
        )
    )
    assert run.evaluator.success_at_s is not None
    assert run.reason == "collision"
    assert run.store.manifest["metrics"]["success"] is False
    assert run.store.manifest["metrics"]["score"]["total"] < 50
    assert run.vehicle.state.speed_mps == 0
    braking = [r for r in run.records if "safety_braking" in r["interventions"]]
    assert braking and any(r["evaluation"]["collision_ids"] for r in braking)


def test_nonconverging_dynamics_cannot_write_unbounded_braking_frames(
    tmp_path, monkeypatch
):
    run = Run(RunConfig(algorithm="manual", realtime=False), tmp_path, headless=True)
    run.vehicle.state.speed_mps = 0.1
    monkeypatch.setattr(
        run.vehicle,
        "advance",
        lambda action, dt: AppliedAction(
            requested=action,
            bounded=action,
            actual=Action(speed_mps=0.1, steering_angle_rad=0),
            interventions=[],
        ),
    )
    try:
        run._brake("test_invalid_integrator")
        assert 0 < len(run.records) < 200
        assert run.reason == "braking_failure"
        assert run.failures[-1]["kind"] == "physics"
        assert run.vehicle.state.speed_mps == 0.1  # Do not fabricate a stopped pose.
    finally:
        run.store.rows.close()


@pytest.mark.parametrize(
    "fault,kind",
    [
        ("exception", "exception"),
        ("initialize", "exception"),
        ("crash", "crash"),
        ("hang", "timeout"),
        ("nan", "exception"),
        ("shape", "invalid_output"),
        ("empty", "invalid_output"),
        ("missing_action", "exception"),
    ],
)
def test_faults_are_isolated_and_next_run_succeeds(execute, fault, kind):
    run = execute(
        RunConfig(
            algorithm="fault",
            parameters={"fault": fault},
            max_steps=3,
            timeout_s=0.4,
            realtime=False,
        ),
        spec=FAULT,
    )
    assert run.state == "failed", run.failures
    assert run.failures[0]["kind"] == kind
    assert run.worker.process.poll() is not None
    following = execute()
    assert following.state == "completed", following.failures
    assert (
        len(
            [r for r in following.records if "safety_braking" not in r["interventions"]]
        )
        == 6
    )
    assert following.vehicle.state.speed_mps == 0
    assert following.records[-1]["pose"]["x_m"] > following.records[5]["pose"]["x_m"]


@pytest.mark.parametrize("fault", ["garbage", "version", "oversize"])
def test_external_protocol_failures(execute, fault):
    spec = PluginSpec(
        id="external_fault",
        name="协议故障",
        version="1",
        capabilities=["action"],
        command=["{python}", "-m", "tests.faults", fault],
    )
    run = execute(
        RunConfig(algorithm="external_fault", max_steps=2, realtime=False), spec=spec
    )
    assert run.state == "failed"
    assert run.failures[0]["kind"] == "protocol"
    assert run.worker.process.poll() is not None


def test_saturation_is_not_hidden(execute):
    run = execute(
        RunConfig(
            algorithm="fault",
            parameters={"fault": "bounds"},
            max_steps=4,
            realtime=False,
        ),
        spec=FAULT,
    )
    row = run.records[0]
    assert row["output"]["action"]["speed_mps"] == 50
    assert row["applied"]["bounded"]["speed_mps"] == 1.5
    assert "speed_saturated" in row["interventions"]


def test_public_boundary_and_instance_reset(execute):
    config = RunConfig(
        algorithm="fault", parameters={"fault": "inspect"}, max_steps=3, realtime=False
    )
    a, b = execute(config, spec=FAULT), execute(config, spec=FAULT)
    debug = a.records[0]["output"]["debug"]
    prohibited = {
        "scene",
        "seed",
        "pose",
        "target_path",
        "target_id",
        "family",
        "map",
        "future_image",
    }
    assert not prohibited.intersection(debug["observation_keys"])
    assert not prohibited.intersection(debug["context"])
    assert a.id != b.id
    assert [r["output"]["debug"]["frames_seen"] for r in a.records] == [1, 2, 3]
    assert b.records[0]["output"]["debug"]["frames_seen"] == 1


def test_deterministic_motion_and_stress(execute):
    config = RunConfig(
        algorithm="constant",
        seed=31,
        max_steps=15,
        realtime=False,
        stress={
            "mode": "stress",
            "delay_frames": 3,
            "drop_probability": 0.4,
            "action_ttl_s": 0.1,
        },
    )
    a, b = execute(config), execute(config)
    assert [r["pose"] for r in a.records] == [r["pose"] for r in b.records]
    assert [r["interventions"] for r in a.records] == [
        r["interventions"] for r in b.records
    ]
    assert any("observation_dropped" in r["interventions"] for r in a.records)
    assert any("action_expired" in r["interventions"] for r in a.records)


def test_manual_pause_step_cancel_and_brake(tmp_path):
    run = Run(RunConfig(algorithm="manual", max_steps=400), tmp_path, headless=True)
    run.start()
    try:
        wait_until(lambda: run.state == "running")
        run.set_action(Action(steering_angle_rad=0.2, speed_mps=0.8))
        run.control("step")
        wait_until(lambda: len(run.records) == 1)
        time.sleep(0.12)
        assert len(run.records) == 1
        run.control("resume")
        wait_until(lambda: len(run.records) >= 4)
        run.control("stop")
        run.thread.join(5)
        assert run.state == "cancelled"
        assert run.vehicle.state.speed_mps == 0
        assert any("safety_braking" in row["interventions"] for row in run.records)
    finally:
        run.control("stop")
        run.thread.join(5)


def test_browser_lease_and_bounded_concurrency(tmp_path):
    manager = RunManager(tmp_path)
    try:
        runs = [manager.create(RunConfig()) for _ in range(3)]
        with pytest.raises(ValueError, match="同时"):
            manager.create(RunConfig())
        runs[0].client_seen = time.monotonic() - 31
        wait_until(lambda: runs[0].state == "cancelled")
        assert runs[0].reason == "client_disconnected"
    finally:
        manager.close()


def test_external_plugin_and_algorithm_removal(execute, tmp_path):
    run = execute(RunConfig(algorithm="external_stop", max_steps=2, realtime=False))
    assert run.state == "completed"
    assert run.records[0]["output"]["debug"]["frames_seen"] == 1
    path = tmp_path / "algorithms.json"
    path.write_text("[]")
    assert registry(path) == {}
