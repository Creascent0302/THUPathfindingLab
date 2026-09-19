import time

import pytest

from pathlab.config import RunConfig
from pathlab.engine import Run, RunManager
from pathlab.registry import PluginSpec, registry
from pathlab.sdk import Action
from .conftest import wait_until


FAULT = PluginSpec(
    id="fault",
    name="故障注入",
    version="1",
    capabilities=["action"],
    entrypoint="tests.faults:Fault",
)


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
    assert len(following.records) == 6


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
