"""Offline ROS message/state tests; never initialize a node or contact a master.

Run with the ROS 1 interpreter after sourcing its environment. Non-ROS Python
environments skip this module instead of pretending to validate ROS transport.
"""

from collections import deque
from contextlib import ExitStack
import json
import math
from pathlib import Path
import sys
import threading
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

try:
    import rospy
    import roslib.message  # noqa: F401
    import tf2_ros  # noqa: F401
    import cv_bridge  # noqa: F401
    from sensor_msgs.msg import CameraInfo, Image
except ImportError as error:
    raise unittest.SkipTest("ROS 1 Python dependencies are unavailable: " + str(error))

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from ros_line_follower.geometry import Pose2, PoseBuffer, PublicationGate  # noqa: E402
from ros_line_follower.planning import PlannerConfig, build_reference  # noqa: E402
from ros_line_follower.ros_node import LineFollowerNode, RuntimeConfig  # noqa: E402


class RefPoint:
    """Exact field schema; deliberately not claimed as a generated wire type."""

    __slots__ = (
        "t",
        "x",
        "y",
        "v",
        "heading",
        "cr",
        "left_width",
        "right_width",
        "turning_flag",
    )
    _slot_types = ("float64",) * 8 + ("int16",)
    _type = "offline_test_msgs/RefPoint"


class Goal:
    __slots__ = ("timestamp", "Estop", "Go", "Signal", "refPath", "mode", "objects")
    _slot_types = (
        "float64",
        "int16",
        "bool",
        "int16",
        "offline_test_msgs/RefPoint[]",
        "int16",
        "offline_test_msgs/Object[]",
    )
    _type = "offline_test_msgs/Goal"


class Recorder:
    def __init__(self):
        self.messages = []

    def publish(self, message):
        self.messages.append(message)


def offline_node():
    # Bypass __init__: no rospy.init_node, Publisher, Subscriber, TF listener,
    # master lookup, sockets, or background worker threads are constructed.
    node = LineFollowerNode.__new__(LineFollowerNode)
    node.runtime = RuntimeConfig()
    node.planner = PlannerConfig(target_length_m=6.0)
    node.lock = threading.RLock()
    node.poses = PoseBuffer(node.runtime.max_pose_gap_s)
    node.images = deque(maxlen=6)
    node.info = None
    node.info_valid_from = 0.0
    node.latest = None
    node.restart_required = False
    node.epoch = 0
    node.reason = "offline test"
    node.last_image_stamp = 0.0
    node.last_pose_wall = 100.0
    node.gate = PublicationGate(node.runtime.publish_hz)
    node.enable_motion = True
    node.output_frame = "world"
    node.world_frame = "utm"
    node.frame = "base_link"
    node.point_time_mode = "relative"
    node.mode = 3
    node.Goal, node.RefPoint = Goal, RefPoint
    node.goal_pub, node.path_pub, node.status_pub = Recorder(), Recorder(), Recorder()
    return node


def info_message(stamp, focal_length=500.0):
    message = CameraInfo()
    message.header.stamp = rospy.Time.from_sec(stamp)
    message.header.frame_id = "camera_optical"
    message.width, message.height = 640, 480
    message.P = [focal_length, 0, 320, 0, 0, focal_length, 240, 0, 0, 0, 1, 0]
    message.R = [1, 0, 0, 0, 1, 0, 0, 0, 1]
    return message


def image_message(stamp):
    message = Image()
    message.header.stamp = rospy.Time.from_sec(stamp)
    message.header.frame_id = "camera_optical"
    message.width, message.height = 640, 480
    return message


def set_plan(node, capture_stamp=10.0, current_stamp=10.0, current_speed=0.2):
    points = np.c_[np.linspace(0, 7, 180), np.zeros(180)]
    reference = build_reference(points, node.planner, 0.95)
    observed_pose = Pose2(capture_stamp, 100, 200, math.pi / 2, 0.2)
    node.latest = (reference, observed_pose, 100.0, False)
    node.poses.push(Pose2(current_stamp, 100, 200, math.pi / 2, current_speed))
    return reference


class CameraInfoStateTests(unittest.TestCase):
    def test_changed_calibration_cannot_be_paired_with_buffered_or_delayed_old_image(
        self,
    ):
        node = offline_node()
        node.poses.push(Pose2(10.0, 0, 0, 0))
        node.poses.push(Pose2(10.2, 0, 0, 0))
        with patch.object(rospy.Time, "now", return_value=rospy.Time.from_sec(10.2)):
            node._info(info_message(10.0))
            node._image(image_message(10.1))
            node.latest = object()
            changed = info_message(10.2, focal_length=600)
            node._info(changed)
            self.assertEqual(node.epoch, 1)
            self.assertIsNone(node.latest)
            self.assertEqual(len(node.images), 0)
            # A delayed old image is still bracketed by poses, but its
            # acquisition predates the new intrinsics and must not be used.
            node._image(image_message(10.15))
            self.assertIsNone(node._take_frame())
            new_image = image_message(10.2)
            node._image(new_image)
            selected = node._take_frame()
        self.assertIsNotNone(selected)
        self.assertIs(selected[0], new_image)
        self.assertIs(selected[1], changed)
        self.assertEqual(selected[2].stamp, 10.2)

    def test_latched_zero_stamp_change_uses_arrival_time_as_lower_bound(self):
        node = offline_node()
        node.poses.push(Pose2(10.0, 0, 0, 0))
        node.poses.push(Pose2(10.2, 0, 0, 0))
        with patch.object(rospy.Time, "now", return_value=rospy.Time.from_sec(10.2)):
            node._info(info_message(0))
            node._image(image_message(10.1))
            self.assertIsNotNone(node._take_frame())
            node._info(info_message(0, focal_length=600))
            self.assertAlmostEqual(node.info_valid_from, 10.2)
            node._image(image_message(10.15))
            self.assertIsNone(node._take_frame())

    def test_unchanged_camera_info_does_not_flush_waiting_frames(self):
        node = offline_node()
        with patch.object(rospy.Time, "now", return_value=rospy.Time.from_sec(10.2)):
            node._info(info_message(0))
            image = image_message(10.1)
            node._image(image)
            node._info(info_message(10.2))
        self.assertEqual(node.epoch, 0)
        self.assertEqual(node.info_valid_from, 0)
        self.assertEqual(list(node.images), [image])

    def test_delayed_old_intrinsics_do_not_replace_newer_calibration(self):
        node = offline_node()
        with patch.object(rospy.Time, "now", return_value=rospy.Time.from_sec(10.2)):
            node._info(info_message(10.0))
            latest = info_message(10.2, focal_length=600)
            node._info(latest)
            epoch = node.epoch
            node._info(info_message(10.1))
        self.assertIs(node.info, latest)
        self.assertAlmostEqual(node.info_valid_from, 10.2)
        self.assertEqual(node.epoch, epoch)


class PublicationStateTests(unittest.TestCase):
    def assert_stopped(self, node):
        self.assertEqual(len(node.goal_pub.messages), 1)
        goal = node.goal_pub.messages[0]
        self.assertFalse(goal.Go)
        self.assertGreater(goal.Estop, 0)
        self.assertEqual(goal.refPath, [])

    def test_age_and_current_speed_jointly_reject_insufficient_braking_space(self):
        node = offline_node()
        reference = set_plan(node, current_stamp=10.7, current_speed=2.0)
        needed = 2.0**2 / (2 * node.planner.braking_mps2)
        needed += 2.0 * (node.gate.period + node.runtime.max_pose_age_s)
        needed += node.planner.stop_margin_m
        # The complete path would suffice. Movement since its image removes
        # that margin; using image-time speed (0.2 m/s) would miss this fault.
        self.assertGreater(reference.length_m, needed)
        self.assertLess(reference.length_m - 2.0 * 0.7, needed)
        node._publish_cycle(now=10.7, wall=100.0)
        self.assert_stopped(node)
        self.assertIsNone(node.latest)

    def test_fresh_path_at_same_current_speed_remains_usable(self):
        node = offline_node()
        set_plan(node, current_speed=2.0)
        node._publish_cycle(now=10.0, wall=100.0)
        self.assertTrue(node.goal_pub.messages[0].Go)

    def test_restart_lock_blocks_even_a_fresh_otherwise_valid_plan(self):
        node = offline_node()
        set_plan(node)
        node.restart_required = True
        node._publish_cycle(now=10.0, wall=100.0)
        self.assert_stopped(node)
        self.assertTrue(node.restart_required)
        self.assertEqual(node.path_pub.messages[0].poses, [])

    def test_pose_jump_latches_restart_even_after_normal_localization_resumes(self):
        node = offline_node()
        set_plan(node)
        jumped = SimpleNamespace(
            timestamp=10.1,
            x=110.0,
            y=200.0,
            heading=math.pi / 2,
            speed_x=0.2,
            speed_y=0.0,
            roll=0.0,
            pitch=0.0,
        )
        with patch.object(rospy.Time, "now", return_value=rospy.Time.from_sec(10.1)):
            node._pose(jumped)
        self.assertTrue(node.restart_required)
        self.assertIsNone(node.latest)
        self.assertEqual(node.poses.poses, [])
        self.assertIn("重启节点", node.reason)
        # A subsequent normal measurement can refill localization; it must not
        # silently authorize choosing a new route after the coordinate jump.
        recovered = SimpleNamespace(**vars(jumped))
        recovered.timestamp = 10.2
        recovered.y = 200.02
        with patch.object(rospy.Time, "now", return_value=rospy.Time.from_sec(10.2)):
            node._pose(recovered)
        self.assertEqual(len(node.poses.poses), 1)
        self.assertTrue(node.restart_required)

    def test_localization_outage_stops_even_when_image_and_plan_are_fresh(self):
        node = offline_node()
        set_plan(node)
        node.last_pose_wall = 99.0
        node._publish_cycle(now=10.0, wall=100.0)
        self.assert_stopped(node)
        self.assertEqual(node.path_pub.messages[0].poses, [])

    def test_disabled_motion_still_previews_world_path_without_drive_command(self):
        node = offline_node()
        reference = set_plan(node)
        node.enable_motion = False
        node._publish_cycle(now=10.0, wall=100.0)
        self.assert_stopped(node)
        path = node.path_pub.messages[0]
        self.assertEqual(path.header.frame_id, "utm")
        self.assertEqual(path.header.stamp.to_sec(), 10.0)
        self.assertEqual(len(path.poses), len(reference.points))
        # The observed vehicle points north, so its forward line advances UTM y.
        self.assertAlmostEqual(path.poses[0].pose.position.x, 100)
        self.assertAlmostEqual(path.poses[-1].pose.position.x, 100)
        self.assertGreater(path.poses[-1].pose.position.y, 205)
        status = json.loads(node.status_pub.messages[0].data)
        self.assertFalse(status["motion_enabled"])
        self.assertGreater(status["length_m"], 5)

    def test_ros_clock_rollback_clears_state_and_publishes_immediate_stop(self):
        node = offline_node()
        set_plan(node)
        node.images.append(image_message(10))
        node.last_image_stamp = 10
        node.closed = Mock()
        node.closed.wait.side_effect = [False, False, True]
        node.info = info_message(10)
        node.info_valid_from = 10
        with ExitStack() as stack:
            stack.enter_context(
                patch.object(
                    rospy.Time, "now", side_effect=[rospy.Time(10), rospy.Time(9)]
                )
            )
            stack.enter_context(
                patch(
                    "ros_line_follower.ros_node.time.monotonic",
                    side_effect=[100, 100.05],
                )
            )
            stack.enter_context(patch.object(rospy, "is_shutdown", return_value=False))
            errors = stack.enter_context(patch.object(rospy, "logerr_throttle"))
            node._publish()
        errors.assert_not_called()
        self.assertEqual(len(node.goal_pub.messages), 2)
        self.assertTrue(node.goal_pub.messages[0].Go)
        self.assertFalse(node.goal_pub.messages[1].Go)
        self.assertEqual(node.poses.poses, [])
        self.assertEqual(len(node.images), 0)
        self.assertEqual(node.last_image_stamp, 0)
        self.assertEqual(node.epoch, 1)
        self.assertIsNone(node.info)
        self.assertEqual(node.info_valid_from, 0)
        self.assertTrue(node.restart_required)


class RuntimeConfigTests(unittest.TestCase):
    def test_pose_gap_limits_match_pose_buffer(self):
        accepted = RuntimeConfig(max_pose_gap_s=1.0)
        PoseBuffer(accepted.max_pose_gap_s)
        for gap in (0, -0.1, 1.001, 1.5, 2):
            with self.subTest(gap=gap), self.assertRaises(ValueError):
                RuntimeConfig(max_pose_gap_s=gap)


if __name__ == "__main__":
    unittest.main()
