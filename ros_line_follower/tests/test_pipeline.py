"""Physical perspective camera -> temporal identity -> metric reference path."""

import math
from pathlib import Path
import sys

import cv2
import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from ros_line_follower.geometry import ground_homography, rotation  # noqa: E402
from ros_line_follower.planning import PlannerConfig, build_reference  # noqa: E402
from ros_line_follower.vision import (  # noqa: E402
    TargetTracker,
    VisionConfig,
    transform_points,
)


def perspective_camera():
    pitch = math.radians(20)
    transform = np.eye(4)
    transform[:3, :3] = [
        [0, -1, 0],
        [-math.sin(pitch), 0, -math.cos(pitch)],
        [math.cos(pitch), 0, -math.sin(pitch)],
    ]
    transform[:3, 3] = -transform[:3, :3] @ [0, 0, 0.8]
    projection = [[600, 0, 640, 0], [0, 600, 360, 0], [0, 0, 1, 0]]
    return ground_homography(projection, np.eye(3), transform, 0)


def road(shape):
    x = np.linspace(0.1, 14, 1000)
    y = {
        "straight": np.zeros_like(x),
        "curve": 0.018 * x**2,
        "sine": 0.4 * np.sin(x / 3) ** 2,
    }[shape]
    return np.c_[x, y]


def render(lines, homography, polarity):
    image = np.full((720, 1280, 3), 215 if polarity == "dark" else 40, np.uint8)
    color = (25,) * 3 if polarity == "dark" else (245,) * 3
    for path in lines:
        path = path[path[:, 0] >= 0.1]
        tangent = np.gradient(path, axis=0)
        normal = np.c_[-tangent[:, 1], tangent[:, 0]]
        normal /= np.linalg.norm(normal, axis=1)[:, None]
        # A real 12 cm ribbon, not a constant-width pixel polyline.
        boundary = np.r_[path + 0.06 * normal, (path - 0.06 * normal)[::-1]]
        pixels = np.rint(transform_points(boundary, homography)).astype(np.int32)
        cv2.fillPoly(image, [pixels], color)
    return image


@pytest.mark.parametrize("shape", ["straight", "curve", "sine"])
@pytest.mark.parametrize("polarity", ["dark", "light"])
def test_perspective_metric_pipeline_keeps_target_with_parallel_distractor(
    shape, polarity
):
    target = road(shape)
    distractor = target + [0, 0.4]
    homography = perspective_camera()
    tracker = TargetTracker(VisionConfig(line_polarity=polarity))
    image = render([target, distractor], homography, polarity)
    track = tracker.observe(image, homography, 0.1)
    assert track.path is not None and not track.predicted, track.reason
    reference = build_reference(track.path, PlannerConfig(), track.confidence)
    assert reference.length_m > 9.9
    assert len(reference.points) >= 67
    distance = np.linalg.norm(reference.points[:, None] - target[None, :], axis=2).min(
        axis=1
    )
    assert distance.max() < 0.05
    assert np.max(np.abs(reference.curvature)) < 0.5
    assert reference.speed[-1] == 0

    translation, yaw = np.array([0.4, 0]), 0.02
    tracker.advance(translation, yaw)
    new_target = (target - translation) @ rotation(yaw)
    new_distractor = (distractor - translation) @ rotation(yaw)
    image = render([new_target, new_distractor], homography, polarity)
    track = tracker.observe(image, homography, 0.1)
    assert track.path is not None and not track.predicted, track.reason
    reference = build_reference(track.path, PlannerConfig(), track.confidence)
    distance = np.linalg.norm(
        reference.points[:, None] - new_target[None, :], axis=2
    ).min(axis=1)
    assert reference.length_m > 9.9 and distance.max() < 0.05
