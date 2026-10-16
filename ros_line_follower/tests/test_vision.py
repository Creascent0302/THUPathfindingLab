"""Offline geometry/identity checks; these are not real-vehicle acceptance."""

from pathlib import Path
import sys

import cv2
import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from ros_line_follower.vision import (  # noqa: E402
    BirdEye,
    TargetTracker,
    VisionConfig,
    thinning,
    transform_points,
)


# An orthographic rectified test view covers x=[0,16], y=[-4,4] metres.
H = np.array([[0, -50, 220], [-30, 0, 500], [0, 0, 1]], dtype=float)


def scene(lines=(0.0,), polarity="dark", length=14):
    rgb = np.full((520, 440, 3), 225 if polarity == "dark" else 45, np.uint8)
    value = 20 if polarity == "dark" else 245
    for y in lines:
        path = np.c_[np.linspace(0.2, length, 400), np.full(400, y)]
        points = np.rint(transform_points(path, H)).astype(np.int32)
        cv2.polylines(rgb, [points], False, (value,) * 3, 5)
    return rgb


@pytest.mark.parametrize("forward,width,resolution", [(15, 4, 0.04), (21, 6, 0.06)])
def test_bev_extents_are_resized_not_shifted(forward, width, resolution):
    config = VisionConfig(
        bev_forward_m=forward, bev_half_width_m=width, resolution_m=resolution
    )
    camera = BirdEye(440, 520, H, config)
    np.testing.assert_allclose(camera.ground[0, 0], [forward, width])
    np.testing.assert_allclose(camera.ground[-1, -1], [0, -width])
    assert camera.ground.shape[0] == int(np.ceil(forward / resolution)) + 1
    assert camera.ground.shape[1] == int(np.ceil(width * 2 / resolution)) + 1
    points = np.array([[2, 0.2], [10, -1.5], [14, 2]])
    np.testing.assert_allclose(
        transform_points(camera.pixels(points), camera.inv), points
    )


@pytest.mark.parametrize("polarity", ["dark", "light"])
def test_track_long_metric_path_in_both_polarities(polarity):
    tracker = TargetTracker(VisionConfig(line_polarity=polarity))
    track = tracker.observe(scene(polarity=polarity), H, 0.1)
    assert track.status == "TRACK" and not track.predicted
    assert np.ptp(track.path[:, 0]) > 12
    assert np.max(np.abs(track.path[:, 1])) < 0.06
    assert np.all(np.diff(track.path[:, 0]) > 0)


def test_parallel_skeletons_and_tracking_never_bridge_separate_lines():
    mask = np.zeros((70, 60), np.uint8)
    mask[3:67, 10:15] = 1
    mask[3:67, 20:25] = 1
    skeleton = thinning(mask)
    assert skeleton[:, 15:20].sum() == 0
    tracker = TargetTracker()
    track = tracker.observe(scene((0, 0.32)), H, 0.1)
    assert track.status == "TRACK"
    assert len(tracker.components) == 2
    assert np.max(np.abs(track.path[:, 1])) < 0.06
    # The previous target, not whichever line is nearest after motion, owns identity.
    tracker.advance(np.array([0.1, 0.20]), 0)
    track = tracker.observe(scene((-0.20, 0.12)), H, 0.1)
    assert track.status == "TRACK" and not track.predicted
    assert np.max(np.abs(track.path[:, 1] + 0.20)) < 0.06


def test_ambiguous_initialization_stops_instead_of_picking_nearest():
    track = TargetTracker().observe(scene((-0.16, 0.16)), H, 0.1)
    assert track.status == "AMBIGUOUS" and track.path is None


def test_actual_motion_transform_uses_old_body_translation():
    tracker = TargetTracker()
    tracker.path = np.array([[2.0, 0], [3.0, 0], [4.0, 0]])
    tracker.advance([1, 0], np.pi / 2)
    np.testing.assert_allclose(tracker.path, [[0, -1], [0, -2], [0, -3]], atol=1e-12)
    with pytest.raises(ValueError):
        tracker.advance([np.nan, 0], 0)


def test_motion_does_not_skip_to_a_spatially_close_later_leg():
    tracker = TargetTracker()
    outward = np.c_[np.linspace(0.25, 10, 100), np.zeros(100)]
    back = np.c_[np.linspace(10, 0.05, 100), np.full(100, 0.15)]
    tracker.path = np.vstack([outward, back])
    tracker.advance([0, 0], 0)
    np.testing.assert_allclose(tracker.path[0], outward[0])
    assert len(tracker.path) == 200


def test_u_bend_is_ordered_by_connected_route_not_forward_coordinate():
    angle = np.linspace(0, np.pi, 250)
    expected = np.vstack(
        [
            np.c_[np.linspace(0.2, 3, 100), np.zeros(100)],
            np.c_[3 + 1.5 * np.sin(angle), 1.5 * (1 - np.cos(angle))],
            np.c_[np.linspace(3, 0.5, 100), np.full(100, 3.0)],
        ]
    )
    rgb = np.full((520, 440, 3), 225, np.uint8)
    cv2.polylines(
        rgb,
        [np.rint(transform_points(expected, H)).astype(np.int32)],
        False,
        (20, 20, 20),
        5,
    )
    result = TargetTracker(VisionConfig(minimum_radius_m=1.4)).observe(rgb, H, 0.1)
    assert result.status == "TRACK"
    assert np.min(np.diff(result.path[:, 0])) < -0.05
    assert np.linalg.norm(np.diff(result.path, axis=0), axis=1).sum() > 9.5
    assert np.linalg.norm(result.path[-1] - expected[-1]) < 0.1
    error = np.linalg.norm(result.path[:, None] - expected[None], axis=2).min(axis=1)
    assert np.max(error) < 0.10


def test_initial_feasible_arc_scores_better_than_too_tight_arc():
    tracker = TargetTracker(VisionConfig(minimum_radius_m=2))
    direction = np.array([0.0, 1.0])
    assert (
        tracker.initial_connection_cost([2, 2], direction)
        < tracker.config.initial_gate_m
    )
    assert (
        tracker.initial_connection_cost([0.5, 0.5], direction)
        > tracker.config.initial_gate_m
    )


@pytest.mark.parametrize(
    "matrix", [np.zeros((3, 3)), np.ones((2, 2)), np.full((3, 3), np.nan)]
)
def test_bad_calibration_has_explicit_error(matrix):
    result = TargetTracker().observe(scene(), matrix, 0.1)
    assert result.status == "ERROR" and result.path is None


def test_invisible_calibration_is_rejected():
    hidden = H.copy()
    hidden[0, 2] += 5000
    assert TargetTracker().observe(scene(), hidden, 0.1).status == "ERROR"


def test_calibration_change_rebuilds_camera_without_scale_drift():
    tracker = TargetTracker()
    tracker.observe(scene(), H, 0.1)
    old = tracker.camera
    image = cv2.resize(scene(), (880, 1040))
    scaled = np.diag([2, 2, 1]) @ H
    track = tracker.observe(image, scaled, 0.1)
    assert tracker.camera is not old and tracker.camera.size == (880, 1040)
    assert track.status == "TRACK"
    assert np.max(np.abs(track.path[:, 1])) < 0.06


def test_occlusion_expires_and_does_not_reinitialize_on_wrong_line():
    tracker = TargetTracker(VisionConfig(memory_s=0.25))
    assert tracker.observe(scene(), H, 0.1).status == "TRACK"
    blank = np.full((520, 440, 3), 225, np.uint8)
    predicted = tracker.observe(blank, H, 0.1)
    assert predicted.predicted and predicted.path is not None
    tracker.observe(blank, H, 0.1)
    stopped = tracker.observe(scene((0.6,)), H, 0.1)
    assert stopped.status == "LOST" and stopped.path is None
    recovered = tracker.observe(scene((0, 0.6)), H, 0.1)
    assert recovered.status == "TRACK" and not recovered.predicted
    assert np.max(np.abs(recovered.path[:, 1])) < 0.06


def test_no_coloured_marker_can_extend_occlusion_memory():
    tracker = TargetTracker(VisionConfig(memory_s=0.15))
    tracker.observe(scene(), H, 0.1)
    rgb = np.full((520, 440, 3), 225, np.uint8)
    cv2.rectangle(rgb, (190, 440), (250, 480), (245, 150, 20), -1)
    tracker.observe(rgb, H, 0.1)
    assert tracker.observe(rgb, H, 0.1).status == "LOST"


@pytest.mark.parametrize("fault", ["image", "dt", "calibration", "invisible"])
def test_invalid_frame_revokes_prediction_without_forgetting_target(fault):
    tracker = TargetTracker()
    assert tracker.observe(scene(), H, 0.1).status == "TRACK"
    image, matrix, dt = scene(), H.copy(), 0.1
    if fault == "image":
        image = image.astype(float)
    elif fault == "dt":
        dt = float("nan")
    elif fault == "calibration":
        matrix[:] = 0
    else:
        matrix[0, 2] += 5000
    for _ in range(10):
        assert tracker.observe(image, matrix, dt).status == "ERROR"
    assert tracker.initialized and tracker.path is not None
    blank = np.full((520, 440, 3), 225, np.uint8)
    result = tracker.observe(blank, H, 0.1)
    assert result.status == "LOST" and result.path is None and not result.predicted
    assert tracker.observe(scene((0.6,)), H, 0.1).status == "LOST"
    recovered = tracker.observe(scene((0.0, 0.6)), H, 0.1)
    assert recovered.status == "TRACK" and not recovered.predicted
    assert tracker.observe(blank, H, 0.1).predicted


def test_external_transport_fault_can_revoke_prediction():
    tracker = TargetTracker()
    tracker.observe(scene(), H, 0.1)
    tracker.invalidate_prediction()
    blank = np.full((520, 440, 3), 225, np.uint8)
    assert tracker.observe(blank, H, 0.01).status == "LOST"


@pytest.mark.parametrize(
    "changes",
    [
        {"resolution_m": 0},
        {"bev_forward_m": float("nan")},
        {"resolution_m": 0.0001},
        {"line_polarity": "both"},
        {"max_trace_vertices": 10},
        {"initial_anchor_m": 100},
    ],
)
def test_configuration_rejects_invalid_or_unbounded_work(changes):
    with pytest.raises(ValueError):
        VisionConfig(**changes)
