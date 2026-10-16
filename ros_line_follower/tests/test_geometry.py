"""Offline transport geometry contracts; no ROS installation or vehicle needed."""

from pathlib import Path
import math
import sys

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from ros_line_follower.geometry import (  # noqa: E402
    Pose2,
    PoseBuffer,
    PublicationGate,
    ground_homography,
    relative_motion,
    rigid_transform,
)


def camera_geometry(lateral_m=0.0):
    """Physical camera is 1.5 m above ground, looking along vehicle +x."""
    projection = np.array([[500.0, 0, 320, 0], [0, 500.0, 240, 0], [0, 0, 1.0, 0]])
    transform = np.eye(4)
    # Body: forward/left/up. Optical: right/down/forward.
    transform[:3, :3] = [[0, -1, 0], [0, 0, -1], [1, 0, 0]]
    transform[:3, 3] = -transform[:3, :3] @ [0, lateral_m, 1.5]
    return projection, transform


def project_ground(matrix, points):
    homogeneous = np.c_[points, np.ones(len(points))] @ matrix.T
    return homogeneous[:, :2] / homogeneous[:, 2:3]


def test_pose_interpolation_wraps_heading_and_interpolates_measurements():
    buffer = PoseBuffer(max_gap_s=0.3)
    first = Pose2(10, 100, 200, math.radians(179), 0.2, 0.02, 0.04)
    second = Pose2(10.2, 102, 204, math.radians(-179), 0.6, 0.06, 0.08)
    buffer.push(first)
    buffer.push(second)
    assert buffer.at(10) is first
    assert buffer.at(10.2) is second
    middle = buffer.at(10.1)
    np.testing.assert_allclose(
        [middle.x, middle.y, middle.speed, middle.roll, middle.pitch],
        [101, 202, 0.4, 0.04, 0.06],
    )
    assert abs(abs(middle.yaw) - math.pi) < 1e-12
    assert middle.stamp == 10.1


def test_pose_buffer_never_extrapolates_or_interpolates_across_outage():
    buffer = PoseBuffer(max_gap_s=0.2)
    with pytest.raises(ValueError):
        buffer.at(10)
    buffer.push(Pose2(10, 0, 0, 0))
    buffer.push(Pose2(10.5, 0.1, 0, 0))
    for stamp in (9.99, 10.25, 10.51):
        with pytest.raises(ValueError):
            buffer.at(stamp)
    # Exact measured poses remain usable on either side of a gap.
    assert buffer.at(10.5).x == 0.1


def test_pose_buffer_rejects_replay_and_can_start_a_new_clock_epoch():
    buffer = PoseBuffer(capacity=2)
    for stamp in (10.0, 10.1, 10.2):
        buffer.push(Pose2(stamp, 0, 0, 0))
    assert len(buffer.poses) == 2
    for stamp in (10.2, 10.15):
        with pytest.raises(ValueError):
            buffer.push(Pose2(stamp, 0, 0, 0))
    buffer.clear()
    buffer.push(Pose2(1, 5, 7, 0))
    assert buffer.at(1).x == 5


@pytest.mark.parametrize(
    "kwargs", [{"stamp": 0}, {"x": np.nan}, {"yaw": np.inf}, {"speed": np.nan}]
)
def test_pose_requires_finite_measurements(kwargs):
    values = dict(stamp=1.0, x=0.0, y=0.0, yaw=0.0, speed=0.0)
    values.update(kwargs)
    with pytest.raises(ValueError):
        Pose2(**values)


def test_relative_motion_is_in_previous_body_axes_with_wrapped_yaw():
    old = Pose2(10, 100, 200, math.pi / 2)
    current = Pose2(10.1, 99, 202, math.pi / 2 + 0.1)
    translation, yaw = relative_motion(old, current)
    np.testing.assert_allclose(translation, [2, 1], atol=1e-12)
    assert yaw == pytest.approx(0.1)
    _, wrapped = relative_motion(
        Pose2(10, 0, 0, math.radians(179)),
        Pose2(10.1, 0, 0, math.radians(-179)),
    )
    assert wrapped == pytest.approx(math.radians(2))


def test_ground_projection_has_correct_forward_left_axes_and_metric_height():
    projection, transform = camera_geometry()
    homography = ground_homography(projection, np.eye(3), transform, 0.0)
    points = np.array([[10, 0], [10, 2], [5, -1]])
    np.testing.assert_allclose(
        project_ground(homography, points), [[320, 315], [220, 315], [420, 390]]
    )
    lower_ground = ground_homography(projection, np.eye(3), transform, -0.3)
    np.testing.assert_allclose(project_ground(lower_ground, [[10, 0]]), [[320, 330]])


def test_rectification_rotation_is_applied_before_projection():
    projection, transform = camera_geometry()
    angle = 0.1
    rectification = np.array(
        [
            [math.cos(angle), -math.sin(angle), 0],
            [math.sin(angle), math.cos(angle), 0],
            [0, 0, 1],
        ]
    )
    homography = ground_homography(projection, rectification, transform, 0.0)
    # (10, 2, 0) in the body is (-2, 1.5, 10) in the physical optical frame.
    u = 320 + 50 * (-2 * math.cos(angle) - 1.5 * math.sin(angle))
    v = 240 + 50 * (-2 * math.sin(angle) + 1.5 * math.cos(angle))
    np.testing.assert_allclose(project_ground(homography, [[10, 2]]), [[u, v]])


def test_right_camera_baseline_is_in_tf_and_not_applied_twice():
    projection, right_from_body = camera_geometry(lateral_m=-0.2)
    projection[0, 3] = -projection[0, 0] * 0.2
    homography = ground_homography(projection, np.eye(3), right_from_body, 0.0)
    # Right camera's own center is already 0.2 m to the right of the vehicle.
    np.testing.assert_allclose(project_ground(homography, [[10, 0]]), [[310, 315]])
    projection[0, 3] = 0.0
    without_other_camera_baseline = ground_homography(
        projection, np.eye(3), right_from_body, 0.0
    )
    np.testing.assert_allclose(homography, without_other_camera_baseline)


def test_rigid_transform_uses_xyzw_and_validates_rotation():
    transform = rigid_transform([1, 2, 3], [0, 0, math.sqrt(0.5), math.sqrt(0.5)])
    np.testing.assert_allclose(transform @ [1, 0, 0, 1], [1, 3, 3, 1], atol=1e-12)
    for quaternion in ([0, 0, 0, 0], [0, 0, 0, 2], [0, 0, np.nan, 1]):
        with pytest.raises(ValueError):
            rigid_transform([0, 0, 0], quaternion)


def test_ground_projection_rejects_degenerate_and_nonrigid_calibration():
    projection, transform = camera_geometry()
    with pytest.raises(ValueError):
        ground_homography(projection, np.zeros((3, 3)), transform, 0)
    # Camera center on the assumed ground plane makes the planar map singular.
    with pytest.raises(ValueError):
        ground_homography(projection, np.eye(3), transform, 1.5)
    malformed = transform.copy()
    malformed[3, 0] = 1
    with pytest.raises(ValueError):
        ground_homography(projection, np.eye(3), malformed, 0)
    projection[0, 0] = 0
    with pytest.raises(ValueError):
        ground_homography(projection, np.eye(3), transform, 0)


def test_publication_gate_limits_paths_and_never_restamps_old_geometry():
    gate = PublicationGate(rate_hz=2)
    assert gate.ready(1.0, 10.0, True)
    assert not gate.ready(1.1, 10.1, True)
    assert not gate.ready(1.5, 10.0, True)
    assert gate.ready(1.5, 10.4, True)
    assert not gate.ready(1.99, 10.8, True)
    assert gate.ready(2.0, 10.9, True)


def test_first_stop_bypasses_rate_limit_but_stop_heartbeat_is_bounded():
    gate = PublicationGate(rate_hz=2)
    assert gate.ready(1.0, 10.0, True)
    assert gate.ready(1.01, None, False)
    assert not gate.ready(1.02, None, False)
    assert not gate.ready(1.2, 10.2, True)
    assert gate.ready(1.52, None, False)
    assert gate.ready(2.03, 10.8, True)
    assert gate.ready(2.04, None, False)
