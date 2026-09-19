import copy
import json

import pytest
from fastapi.testclient import TestClient

from pathlab.api import create_app
from pathlab.benchmark import (
    BenchmarkManager,
    BenchmarkRequest,
    aggregate,
    test_set_key as benchmark_key,
)
from pathlab.config import Pose, RunConfig, SceneObject, VehicleConfig
from pathlab.engine import RunManager
from pathlab.engine import RunCapacityError
from pathlab.evaluation import Evaluator, comparison_key, score_metrics, summarize
from pathlab.scenarios import generate
from pathlab.simulation import VehicleState
from pathlab.storage import write_json
from pathlab.registry import PluginSpec, registry
from .conftest import wait_until


def sample_metrics(success=True, completion=1):
    return {
        "truth_metrics_available": True,
        "success": success,
        "completion": completion,
        "tracking_lateral_error_m": {"p95": 0.02},
        "simulation_time_s": 15,
        "steering_rate_rad_s": {"p95": 0.1},
        "frames": 300,
        "safety_intervention_frames": 0,
        "illegal_switches": [],
        "collision_count": 0,
        "inference_ms": {"p95": 10},
    }


def request(**changes):
    return BenchmarkRequest.model_validate(
        {
            "algorithms": [{"algorithm": "constant"}, {"algorithm": "stop"}],
            "families": ["straight"],
            "seeds": [11],
            "max_steps": 2,
            **changes,
        }
    )


def test_score_separates_success_failure_and_cannot_reward_stopping():
    scene = generate("straight", 7)
    high_failure = score_metrics(sample_metrics(False, 1), scene)
    low_success = sample_metrics(True)
    low_success.update(
        tracking_lateral_error_m={"p95": 100},
        simulation_time_s=10000,
        steering_rate_rad_s={"p95": 100},
        safety_intervention_frames=300,
        inference_ms={"p95": 1e9},
    )
    assert (
        high_failure["total"] <= 49 < 60 <= score_metrics(low_success, scene)["total"]
    )
    assert score_metrics(sample_metrics(False, 0), scene)["total"] == 0
    assert score_metrics(sample_metrics(), None) is None
    assert summarize([], None, "source_complete", [])["score"] is None


def test_score_quality_degrades_for_error_collision_and_slow_inference():
    scene = generate("straight", 7)
    metrics = sample_metrics()
    reference = score_metrics(metrics, scene)
    for change in [
        {"tracking_lateral_error_m": {"p95": 0.22}},
        {"collision_count": 1},
        {"inference_ms": {"p95": 500}},
        {"simulation_time_s": 100},
    ]:
        altered = score_metrics({**metrics, **change}, scene)
        assert altered["quality"] < reference["quality"]


def test_comparison_key_includes_full_vehicle_scene_and_execution():
    scene = generate("straight", 7).model_dump()
    config = RunConfig().model_dump()
    key = comparison_key(config, scene, "inertial_v2")
    assert key == comparison_key(
        {**config, "algorithm": "another", "parameters": {"kp": 3}},
        scene,
        "inertial_v2",
    )
    altered = copy.deepcopy(scene)
    altered["vehicle"]["braking_mps2"] += 0.1
    assert comparison_key(config, altered, "inertial_v2") != key
    assert comparison_key(config, scene, "kinematic_v1") != key
    assert comparison_key({**config, "max_steps": 10}, scene, "inertial_v2") != key
    assert comparison_key(config, None, "inertial_v2") is None


def test_batch_test_set_key_distinguishes_execution_but_not_method_identity():
    cases = [{"scene": generate("straight", 7).model_dump()}]
    versions = {"simulation.py": "frozen"}
    action = request(algorithms=[{"algorithm": "constant"}])
    other_action = request(algorithms=[{"algorithm": "stop"}])
    path = request(algorithms=[{"algorithm": "custom_tracker", "execution": "path"}])
    assert benchmark_key(cases, versions, action) == benchmark_key(
        cases, versions, other_action
    )
    assert benchmark_key(cases, versions, action) != benchmark_key(
        cases, versions, path
    )


def test_collision_checks_swept_motion_and_ignores_disabled_objects():
    scene = generate("straight", 7)
    scene.initial_pose = Pose(x_m=-0.3, y_m=0)
    scene.vehicle = VehicleConfig(
        wheelbase_m=0.06, length_m=0.08, width_m=0.08, max_speed_mps=5
    )
    scene.objects = [SceneObject(kind="box", x_m=0, y_m=0, length_m=0.08, width_m=0.08)]
    evaluator = Evaluator(scene)
    evaluator.update(VehicleState(x_m=0.2, speed_mps=5), 0.1)
    assert len(evaluator.collisions) == 1
    assert evaluator.collisions[0]["object_index"] == 0
    scene.objects[0].enabled = False
    disabled = Evaluator(scene)
    disabled.update(VehicleState(x_m=0.2, speed_mps=5), 0.1)
    assert disabled.collisions == []
    scene.objects[0].enabled = True
    scene.objects[0].collidable = False
    nonphysical = Evaluator(scene)
    nonphysical.update(VehicleState(x_m=0.2, speed_mps=5), 0.1)
    assert nonphysical.collisions == []


def test_collision_during_terminal_coasting_overrides_success_without_route_progress():
    scene = generate("straight", 7)
    scene.objects = [
        SceneObject(kind="barrier", x_m=0.7, y_m=0, length_m=0.1, width_m=0.4)
    ]
    scene.initial_pose = Pose()
    evaluator = Evaluator(scene)
    evaluator.update(VehicleState(), 0.05)
    evaluator.done_reason = "success"
    evaluator.success_at_s = 0.05
    evaluator.last_evaluation["reason"] = "success"
    progress = evaluator.progress
    for index in range(10):
        evaluator.update(
            VehicleState(x_m=(index + 1) * 0.05, speed_mps=1), (index + 2) * 0.05
        )
    assert evaluator.done_reason == "collision"
    assert evaluator.progress == progress
    assert len(evaluator.collisions) == 1


def test_external_timeout_coasting_cannot_acquire_or_add_progress():
    scene = generate("straight", 7)
    scene.objects = []
    scene.initial_pose = Pose(x_m=-0.25)
    evaluator = Evaluator(scene)
    evaluator.update(VehicleState(x_m=-0.24), 0.05)
    evaluator.begin_coasting()
    for index in range(20):
        evaluator.update(
            VehicleState(x_m=-0.24 + 0.04 * (index + 1)), 0.1 + index * 0.05
        )
    assert evaluator.acquired_at is None and evaluator.progress == 0
    scene.initial_pose = Pose()
    acquired = Evaluator(scene)
    acquired.update(VehicleState(x_m=0.03), 0.05)
    progress = acquired.progress
    acquired.begin_coasting()
    for index in range(20):
        acquired.update(VehicleState(x_m=0.03 + 0.04 * (index + 1)), 0.1 + index * 0.05)
    assert acquired.progress == progress


def test_paired_aggregation_never_drops_crashes_or_ranks_incomplete_cases():
    methods = [
        {"id": "0", "algorithm": "a", "name": "A", "execution": "action"},
        {"id": "1", "algorithm": "b", "name": "B", "execution": "action"},
    ]
    batch = {
        "methods": methods,
        "items": [
            {
                "method_id": "0",
                "case_id": "0",
                "state": "completed",
                "metrics": {**sample_metrics(), "score": {"total": 90}},
            },
            {"method_id": "1", "case_id": "0", "state": "queued", "metrics": None},
        ],
    }
    summary = aggregate(batch)
    assert not summary["comparable"]
    assert all(
        row["score"] is None and row["success_rate"] is None
        for row in summary["methods"]
    )
    batch["items"][1]["state"] = "failed"
    summary = aggregate(batch)
    assert summary["comparable"]
    assert summary["methods"][1]["score"] == 0
    assert summary["methods"][1]["execution_failures"] == 1
    batch["items"][1]["state"] = "cancelled"
    assert not aggregate(batch)["comparable"]


def test_batch_plan_bounds_and_execution_contract():
    for changes in [
        {"seeds": [1, 1]},
        {"seeds": [-1]},
        {"families": []},
        {"algorithms": [{"algorithm": "manual"}]},
        {
            "algorithms": [
                {"algorithm": "constant"},
                {"algorithm": "stop", "execution": "path"},
            ]
        },
        {
            "families": list(
                __import__("pathlab.scenarios", fromlist=["FAMILIES"]).FAMILIES
            ),
            "seeds": list(range(16)),
        },
    ]:
        with pytest.raises(ValueError):
            request(**changes)


def test_saved_map_is_snapshotted_and_restart_retains_interruption(tmp_path):
    manager = RunManager(tmp_path)
    batches = BenchmarkManager(manager)
    identifier = "a" * 32
    (tmp_path / "maps").mkdir()
    scene = generate("hairpin", 7)
    write_json(tmp_path / "maps" / f"{identifier}.json", scene.model_dump())
    batch = batches.create(request(families=[], map_ids=[identifier], seeds=[21, 22]))
    (tmp_path / "maps" / f"{identifier}.json").unlink()
    assert [case["seed"] for case in batch["cases"]] == [21, 22]
    assert batch["cases"][0]["scene"]["target_path"] == scene.target_path
    restored = BenchmarkManager(manager)
    restored.start()
    try:
        persisted = restored.get(batch["id"])
        assert persisted["state"] == "failed"
        assert all(item["state"] == "cancelled" for item in persisted["items"])
        assert not persisted["summary"]["comparable"]
    finally:
        restored.close()


def test_queue_cancel_and_code_change_are_persisted(tmp_path, monkeypatch):
    batches = BenchmarkManager(RunManager(tmp_path))
    cancelled = batches.create(request())
    batches.cancel(cancelled["id"])
    persisted = json.loads(
        (tmp_path / "benchmarks" / f"{cancelled['id']}.json").read_text()
    )
    assert all(item["state"] == "cancelled" for item in persisted["items"])
    changed = batches.create(request())
    monkeypatch.setattr("pathlab.benchmark.implementation_hash", lambda spec: "changed")
    stored = batches.batches[changed["id"]]
    batches._execute(stored, stored["items"][0])
    assert stored["items"][0]["state"] == "failed"
    assert stored["invalidated"]
    assert not aggregate(stored)["comparable"]


def test_batch_api_runs_real_workers_and_exports_replayable_records(tmp_path):
    with TestClient(create_app(tmp_path)) as client:
        response = client.post("/api/benchmarks", json=request().model_dump())
        assert response.status_code == 201, response.text
        identifier = response.json()["id"]
        wait_until(
            lambda: client.get(f"/api/benchmarks/{identifier}").json()["state"]
            == "completed",
            timeout=30,
        )
        batch = client.get(f"/api/benchmarks/{identifier}").json()
        assert batch["summary"]["comparable"]
        assert len(batch["items"]) == 2
        for item in batch["items"]:
            assert item["run_id"] and item["metrics"]["score"]["total"] == 0
            manifest = client.get(f"/api/results/{item['run_id']}").json()["manifest"]
            assert manifest["benchmark_id"] == identifier
            assert manifest["config"]["realtime"] is False
            assert client.app.state.manager.runs[item["run_id"]].headless
        assert (
            client.get(f"/api/benchmarks/{identifier}/export?format=json").json()[
                "test_set_sha256"
            ]
            == batch["test_set_sha256"]
        )
        assert (
            "lateral_p95_m"
            in client.get(f"/api/benchmarks/{identifier}/export?format=csv").text
        )
        assert client.get("/api/benchmarks").json()[0]["summary"]["finished"] == 2
        assert client.delete(f"/api/benchmarks/{identifier}").status_code == 200
        assert len(client.get("/api/results").json()) == 2


def test_capacity_waits_and_batch_reservations_bound_the_queue(tmp_path, monkeypatch):
    manager = RunManager(tmp_path)
    batches = BenchmarkManager(manager)
    batch = batches.create(request())

    def occupied(*args, **kwargs):
        raise RunCapacityError("busy")

    monkeypatch.setattr(manager, "create", occupied)
    stored = batches.batches[batch["id"]]
    batches._execute(stored, stored["items"][0])
    assert stored["items"][0]["state"] == "queued"
    for _ in range(2):
        batches.create(request())
    with pytest.raises(ValueError, match="3 个批次"):
        batches.create(request())
    for identifier in list(batches.batches):
        batches.cancel(identifier)
    batches.create(
        request(
            families=["straight", "bend", "s_curve", "hairpin"], seeds=list(range(16))
        )
    )
    with pytest.raises(ValueError, match="200 条"):
        batches.create(
            request(families=["straight", "bend", "s_curve"], seeds=list(range(16)))
        )


def test_worker_failure_is_preserved_and_cancel_stops_pending_jobs(
    tmp_path, monkeypatch
):
    specs = registry()
    specs["fault"] = PluginSpec(
        id="fault",
        name="故障测试",
        version="1",
        capabilities=["action"],
        entrypoint="tests.faults:Fault",
    )
    monkeypatch.setattr("pathlab.benchmark.registry", lambda **kwargs: specs)
    with TestClient(create_app(tmp_path)) as client:
        response = client.post(
            "/api/benchmarks",
            json=request(
                algorithms=[
                    {"algorithm": "fault", "parameters": {"fault": "initialize"}},
                    {"algorithm": "stop"},
                ]
            ).model_dump(),
        )
        identifier = response.json()["id"]
        wait_until(
            lambda: client.get(f"/api/benchmarks/{identifier}").json()["state"]
            == "completed",
            timeout=30,
        )
        batch = client.get(f"/api/benchmarks/{identifier}").json()
        assert batch["summary"]["comparable"]
        failure = next(item for item in batch["items"] if item["state"] == "failed")
        assert "intentional initialization failure" in failure["error"]
        assert failure["run_id"] and failure["metrics"]["frames"] == 0
        response = client.post(
            "/api/benchmarks", json=request(max_steps=6000, seeds=[31, 32]).model_dump()
        )
        identifier = response.json()["id"]
        wait_until(
            lambda: any(
                item["state"] == "running"
                for item in client.get(f"/api/benchmarks/{identifier}").json()["items"]
            ),
            timeout=15,
        )
        assert client.post(f"/api/benchmarks/{identifier}/cancel").status_code == 200
        wait_until(
            lambda: all(
                item["state"] in {"completed", "failed", "cancelled"}
                for item in client.get(f"/api/benchmarks/{identifier}").json()["items"]
            ),
            timeout=15,
        )
        batch = client.get(f"/api/benchmarks/{identifier}").json()
        assert batch["state"] == "cancelled" and not batch["summary"]["comparable"]
        assert sum(item["run_id"] is not None for item in batch["items"]) == 1
        assert not any(
            run.thread.is_alive() for run in client.app.state.manager.runs.values()
        )
