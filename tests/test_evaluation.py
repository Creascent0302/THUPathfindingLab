import numpy as np

from pathlab.config import Pose
from pathlab.evaluation import Evaluator, summarize
from pathlab.scenarios import generate
from pathlab.simulation import VehicleState


def evaluator(family="straight"):
    scene = generate(family)
    scene.initial_pose = Pose()
    return Evaluator(scene)


def test_stop_cannot_succeed():
    score = evaluator()
    for i in range(100):
        row = score.update(VehicleState(), (i + 1) * 0.05)
    assert score.acquired_at is not None
    assert row["completion"] == 0
    assert score.done_reason is None


def test_continuous_ordered_path_can_succeed():
    score = evaluator()
    for i, x in enumerate(np.arange(0.04, score.path.total, 0.04)):
        row = score.update(VehicleState(x_m=float(x), speed_mps=0.8), (i + 1) * 0.05)
        if score.done_reason:
            break
    assert score.done_reason == "success"
    assert row["completion"] > 0.98


def test_endpoint_teleport_and_hairpin_jump_fail():
    for family in ["straight", "hairpin", "repeated"]:
        score = evaluator(family)
        score.update(VehicleState(x_m=0.01), 0.05)
        x, y = score.path.points[-1]
        row = score.update(VehicleState(x_m=float(x), y_m=float(y)), 0.1)
        assert score.done_reason == "invalid_motion"
        assert row["completion"] < 0.02


def test_distractor_switch_is_sustained_and_recorded():
    score = evaluator("parallel")
    score.update(VehicleState(x_m=0.01), 0.05)
    for i in range(1, 40):
        score.update(VehicleState(x_m=0.01, y_m=-min(0.43, i * 0.03)), (i + 1) * 0.05)
        if score.done_reason:
            break
    assert score.done_reason == "illegal_switch"
    assert len(score.switches) == 1
    assert score.progress < 0.1


def test_near_endpoint_without_acquisition_never_succeeds():
    score = evaluator("hairpin")
    endpoint = score.path.points[-1]
    score.previous = endpoint.copy()
    for i in range(20):
        row = score.update(
            VehicleState(x_m=float(endpoint[0]), y_m=float(endpoint[1])), (i + 1) * 0.05
        )
    assert not row["completion"]
    assert score.acquired_at is None


def test_unannotated_data_does_not_get_truth_metrics():
    metrics = summarize([], None, "source_complete", [])
    for key in [
        "success",
        "completion",
        "illegal_switches",
        "acquisition_success",
        "simulation_time_s",
        "completion_time_s",
    ]:
        assert metrics[key] is None
    assert metrics["tracking_lateral_error_m"]["mean"] is None
