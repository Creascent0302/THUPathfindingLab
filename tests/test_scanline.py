"""Regressions for hairpin ordering and local scanline association."""

import numpy as np
import pytest

from algorithms.scanline import (
    ScanlinePD,
    ScanlineTracker,
    ordered_nearest,
    scan_component,
)


def test_rotating_scanlines_follow_both_sides_of_a_hairpin_in_order():
    inbound = np.column_stack((np.arange(0.5, 3.0, 0.025), np.zeros(100)))
    angle = np.linspace(-np.pi / 2, np.pi / 2, 100)
    bend = np.column_stack((3 + 0.65 * np.cos(angle), 0.65 + 0.65 * np.sin(angle)))
    outbound = np.column_stack((np.arange(3.0, 0.5, -0.025), np.full(100, 1.3)))
    route = np.concatenate((inbound, bend, outbound))
    # A nearby return path cannot be represented as one y for each x.
    path = scan_component(route, 8, np.array([1.0, 0.0]))
    assert np.linalg.norm(path[0] - route[0]) < 0.1
    assert np.linalg.norm(path[-1] - route[-1]) < 0.1
    assert path[:, 0].max() > 3.6
    indices = np.linalg.norm(path[:, None] - route[None], axis=2).argmin(axis=1)
    assert np.all(np.diff(indices) > 0)
    assert np.linalg.norm(np.diff(path, axis=0), axis=1).max() < 0.13


@pytest.mark.parametrize("gap", [0.06, 0.22])
def test_local_cross_sections_do_not_average_a_parallel_branch(gap):
    x = np.arange(0.5, 5, 0.025)
    route = np.column_stack((x, 0.08 * np.sin(x)))
    parallel = route + [0, gap]
    # Even a connected-component junction farther away must not merge rows.
    cloud = np.concatenate((route, parallel))
    path = scan_component(cloud, 12, np.array([1.0, 0.0]))
    target_distance = np.linalg.norm(path[:, None] - route[None], axis=2).min(axis=1)
    wrong_distance = np.linalg.norm(path[:, None] - parallel[None], axis=2).min(axis=1)
    assert target_distance.max() < 0.03
    assert wrong_distance.min() > gap - 0.03
    assert path[-1, 0] > 4.8


def test_first_ordered_reference_wins_over_nearer_future_return():
    path = np.array(
        [[0.5, 0.1], [0.8, 0.1], [1.5, 0.1], [2, 1], [0.7, 0.3], [0.1, 0.2]]
    )
    assert ordered_nearest(path) == 0
    assert np.argmin(np.linalg.norm(path, axis=1)) == 5
    tracker = ScanlineTracker()
    tracker.path = path.copy()
    tracker.advance(np.zeros(2), 0.0)
    np.testing.assert_array_equal(tracker.path, path)


def test_feedback_scales_with_public_wheelbase_on_the_same_visible_curve():
    from algorithms.modular.control import MotionEstimate
    from pathlab.config import VehicleConfig

    angle = np.linspace(0.22, 1.2, 90)
    radius = 2.0
    path = radius * np.column_stack((np.sin(angle), 1 - np.cos(angle)))
    steering = []
    for wheelbase in (0.32, 0.9):
        limits = VehicleConfig(wheelbase_m=wheelbase).model_dump()
        motion = MotionEstimate(limits)
        motion.state[3] = 0.5
        steering.append(
            ScanlinePD(limits).command(path, 0.98, motion).steering_angle_rad
        )
    assert 0.1 < steering[0] < 0.23
    assert 0.32 < steering[1] < 0.52
