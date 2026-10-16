#!/usr/bin/env python3
"""Isolated ROS 1 transport acceptance, with synthetic perspective camera data.

Run: python3 ros_line_follower/tests/ros_smoke.py

This creates its own /tmp catkin workspace and random localhost ROS master.
It NEVER uses the configured ROS_MASTER_URI or the real vehicle's master.
Goal.msg and RefPoint.msg are copied byte-for-byte; Object.msg is explicitly a
TEST STUB because no real Object definition was supplied. Its generated Goal
MD5 therefore is NOT a production-interface compatibility certificate.
"""

from __future__ import annotations

import argparse
from contextlib import ExitStack
import io
import json
import math
import os
from pathlib import Path
import shutil
import signal
import socket
import subprocess
import tempfile
import time
from urllib.parse import urlparse
from xmlrpc.client import ServerProxy


ROOT = Path(__file__).resolve().parents[2]


def sourced_environment(setup, environment):
    result = subprocess.check_output(
        ["/bin/bash", "-c", 'source "$1" && env -0', "bash", str(setup)],
        env=environment,
    )
    return dict(entry.decode().split("=", 1) for entry in result.split(b"\0") if entry)


def stop_process(process):
    if process.poll() is not None:
        return
    for sig, timeout in ((signal.SIGINT, 5), (signal.SIGTERM, 3), (signal.SIGKILL, 2)):
        try:
            os.killpg(process.pid, sig)
            process.wait(timeout=timeout)
            return
        except ProcessLookupError:
            return
        except subprocess.TimeoutExpired:
            continue


def prepare_workspace(workspace):
    src = workspace / "src"
    src.mkdir()
    (src / "ros_line_follower").symlink_to(
        ROOT / "ros_line_follower", target_is_directory=True
    )
    shutil.copytree(ROOT / "YHS_cuda_drivable/src/cav_msgs", src / "cav_msgs")
    fixture = src / "pathlab_smoke_msgs"
    (fixture / "msg").mkdir(parents=True)
    for filename in ("Goal.msg", "RefPoint.msg"):
        shutil.copyfile(ROOT / filename, fixture / "msg" / filename)
        assert (fixture / "msg" / filename).read_bytes() == (
            ROOT / filename
        ).read_bytes()
    (fixture / "msg/Object.msg").write_text(
        "# TEST-ONLY stub; NOT the original vehicle's Object interface.\nuint8 unused_test_stub\n"
    )
    (fixture / "package.xml").write_text(
        '<package format="2"><name>pathlab_smoke_msgs</name><version>0.0.0</version>'
        "<description>Isolated test fixtures, not vehicle interfaces</description>"
        '<maintainer email="tests@example.invalid">Tests</maintainer><license>Proprietary</license>'
        "<buildtool_depend>catkin</buildtool_depend><build_depend>message_generation</build_depend>"
        "<exec_depend>message_runtime</exec_depend></package>\n"
    )
    (fixture / "CMakeLists.txt").write_text(
        "cmake_minimum_required(VERSION 3.0.2)\nproject(pathlab_smoke_msgs)\n"
        "find_package(catkin REQUIRED COMPONENTS message_generation)\n"
        "add_message_files(FILES Goal.msg RefPoint.msg Object.msg)\n"
        "generate_messages()\ncatkin_package(CATKIN_DEPENDS message_runtime)\n"
    )


def run_isolated(output):
    setup = Path("/opt/ros/noetic/setup.bash")
    if not setup.exists():
        raise RuntimeError(
            "This optional integration test requires ROS Noetic in /opt/ros/noetic"
        )
    output.mkdir(parents=True, exist_ok=True)
    (output / "result.json").unlink(missing_ok=True)
    with tempfile.TemporaryDirectory(prefix="pathlab-ros-smoke-") as temporary:
        workspace = Path(temporary)
        prepare_workspace(workspace)
        environment = {
            key: value
            for key, value in os.environ.items()
            if not key.startswith("ROS_")
            and key not in ("PYTHONPATH", "CMAKE_PREFIX_PATH", "LD_LIBRARY_PATH")
        }
        environment["PATH"] = "/usr/bin:/bin"
        environment = sourced_environment(setup, environment)
        environment["ROS_HOME"] = str(workspace / "ros_home")
        environment["ROS_LOG_DIR"] = str(output / "ros_logs")
        environment["ROS_IP"] = "127.0.0.1"
        environment.pop("ROS_HOSTNAME", None)
        with socket.socket() as listener:
            listener.bind(("127.0.0.1", 0))
            port = listener.getsockname()[1]
        environment["ROS_MASTER_URI"] = "http://127.0.0.1:%d" % port
        environment["PATHLAB_SMOKE_WORKSPACE"] = temporary
        with (output / "build.log").open("w") as log:
            subprocess.run(
                [
                    "catkin_make",
                    "-C",
                    str(workspace),
                    "-j2",
                    "-DPYTHON_EXECUTABLE=/usr/bin/python3",
                ],
                cwd=workspace,
                env=environment,
                stdout=log,
                stderr=subprocess.STDOUT,
                check=True,
                timeout=180,
            )
        environment = sourced_environment(workspace / "devel/setup.bash", environment)
        with ExitStack() as stack:
            log = stack.enter_context((output / "master.log").open("w"))
            master = subprocess.Popen(
                ["roscore", "-p", str(port)],
                env=environment,
                stdout=log,
                stderr=subprocess.STDOUT,
                start_new_session=True,
            )
            stack.callback(stop_process, master)
            deadline = time.monotonic() + 15
            while time.monotonic() < deadline:
                if master.poll() is not None:
                    raise RuntimeError("Isolated roscore exited; inspect master.log")
                try:
                    if (
                        ServerProxy(environment["ROS_MASTER_URI"]).getPid(
                            "/smoke_driver"
                        )[0]
                        == 1
                    ):
                        break
                except (OSError, ConnectionError):
                    time.sleep(0.1)
            else:
                raise RuntimeError("Isolated localhost ROS master did not become ready")
            log = stack.enter_context((output / "test.log").open("w"))
            worker = subprocess.Popen(
                [
                    "/usr/bin/python3",
                    str(Path(__file__).resolve()),
                    "--worker",
                    "--output",
                    str(output),
                ],
                env=environment,
                stdout=log,
                stderr=subprocess.STDOUT,
                start_new_session=True,
            )
            stack.callback(stop_process, worker)
            if worker.wait(timeout=90):
                raise RuntimeError(
                    "ROS smoke failed:\n" + (output / "test.log").read_text()[-6000:]
                )
        result = json.loads((output / "result.json").read_text())
        print(json.dumps(result, ensure_ascii=False, indent=2))


def exercise_node(output):
    """Only the system ROS Python interpreter imports these dependencies."""
    address = urlparse(os.environ.get("ROS_MASTER_URI", ""))
    workspace = Path(os.environ.get("PATHLAB_SMOKE_WORKSPACE", "/invalid"))
    if (
        address.hostname != "127.0.0.1"
        or address.port == 11311
        or not str(workspace).startswith("/tmp/pathlab-ros-smoke-")
    ):
        raise RuntimeError("Refusing to run against any non-isolated ROS master")
    import cv2
    import numpy as np
    import rospy
    import tf2_ros
    import yaml
    from cav_msgs.msg import VehicleState
    from cv_bridge import CvBridge
    from geometry_msgs.msg import TransformStamped
    from pathlab_smoke_msgs.msg import Goal
    from sensor_msgs.msg import CameraInfo, Image
    from std_msgs.msg import String
    from tf.transformations import quaternion_from_matrix

    rospy.init_node("smoke_driver", disable_signals=True)
    config = yaml.safe_load(
        (ROOT / "ros_line_follower/config/line_follower.yaml").read_text()
    )
    config.update(
        image_topic="/smoke/image_rect",
        camera_info_topic="/smoke/camera_info",
        vehicle_state_topic="/smoke/vehicle_state",
        goal_type="pathlab_smoke_msgs/Goal",
        goal_topic="/smoke/goal",
        vehicle_frame="smoke/base",
        world_frame="smoke/world",
        output_frame="world",
        point_time_mode="absolute",
        ground_z_m=0.0,
        enable_motion=True,
    )
    rospy.set_param("/smoke/line_follower", config)
    received, statuses, image_stamps, callback_errors = [], [], set(), []

    def goal_callback(message):
        try:
            buffer = io.BytesIO()
            message.serialize(buffer)
            copy = Goal().deserialize(buffer.getvalue())
            assert copy == message, (
                "Generated ROS message serialization did not round-trip"
            )
            received.append((time.monotonic(), message))
        except Exception as error:
            callback_errors.append(str(error))

    subscribers = [
        rospy.Subscriber("/smoke/goal", Goal, goal_callback, queue_size=100),
        rospy.Subscriber(
            "/smoke/line_follower/status",
            String,
            lambda m: statuses.append(json.loads(m.data)),
            queue_size=100,
        ),
    ]
    image_pub = rospy.Publisher("/smoke/image_rect", Image, queue_size=1)
    info_pub = rospy.Publisher(
        "/smoke/camera_info", CameraInfo, queue_size=1, latch=True
    )
    pose_pub = rospy.Publisher("/smoke/vehicle_state", VehicleState, queue_size=10)
    info = CameraInfo()
    info.header.frame_id = "smoke/camera_optical"
    info.width, info.height = 640, 480
    info.distortion_model = "plumb_bob"
    info.D = [0.0] * 5
    info.K = [450, 0, 320, 0, 450, 240, 0, 0, 1]
    info.P = [450, 0, 320, 0, 0, 450, 240, 0, 0, 0, 1, 0]
    info.R = [1, 0, 0, 0, 1, 0, 0, 0, 1]
    pitch = math.radians(20)
    camera_from_body = np.eye(4)
    camera_from_body[:3, :3] = [
        [0, -1, 0],
        [-math.sin(pitch), 0, -math.cos(pitch)],
        [math.cos(pitch), 0, -math.sin(pitch)],
    ]
    camera_from_body[:3, 3] = -camera_from_body[:3, :3] @ [0, 0, 0.8]
    body_from_camera = np.linalg.inv(camera_from_body)
    transform = TransformStamped()
    transform.header.stamp = rospy.Time.now()
    transform.header.frame_id = "smoke/base"
    transform.child_frame_id = info.header.frame_id
    t, q = transform.transform.translation, transform.transform.rotation
    t.x, t.y, t.z = body_from_camera[:3, 3]
    q.x, q.y, q.z, q.w = quaternion_from_matrix(body_from_camera)
    broadcaster = tf2_ros.StaticTransformBroadcaster()
    broadcaster.sendTransform(transform)
    # A physical 8 cm dark line becomes narrower towards the horizon.
    ground = np.array(
        [[0.2, -0.04, 0, 1], [14, -0.04, 0, 1], [14, 0.04, 0, 1], [0.2, 0.04, 0, 1]]
    )
    projected = ground @ camera_from_body[:3].T @ np.array(info.K).reshape(3, 3).T
    pixels = np.rint(projected[:, :2] / projected[:, 2:]).astype(np.int32)
    rgb = np.full((info.height, info.width, 3), 230, np.uint8)
    cv2.fillConvexPoly(rgb, pixels, (20, 20, 20))
    cv2.imwrite(str(output / "synthetic-perspective.png"), rgb)
    bridge = CvBridge()
    info.header.stamp = rospy.Time.now()
    info_pub.publish(info)

    def pump(seconds, images=True, poses=True):
        start = time.monotonic()
        next_image = start
        while time.monotonic() - start < seconds:
            now = rospy.Time.now().to_sec()
            if poses:
                pose = VehicleState()
                pose.timestamp = now
                pose.x, pose.y, pose.heading = 100.0, 200.0, math.pi / 2
                pose_pub.publish(pose)
            if images and time.monotonic() >= next_image:
                image = bridge.cv2_to_imgmsg(rgb, encoding="rgb8")
                image.header.frame_id = info.header.frame_id
                image.header.stamp = rospy.Time.from_sec(now - 0.01)
                image_stamps.add(image.header.stamp.to_sec())
                image_pub.publish(image)
                next_image = time.monotonic() + 0.1
            time.sleep(0.025)
        return start, time.monotonic()

    def during(interval):
        return [
            (wall, message)
            for wall, message in received
            if interval[0] <= wall <= interval[1]
        ]

    with (output / "node.log").open("w") as log:
        node = subprocess.Popen(
            [
                "rosrun",
                "ros_line_follower",
                "line_follower_node",
                "__ns:=/smoke",
                "__name:=line_follower",
            ],
            stdout=log,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
        try:
            deadline = time.monotonic() + 10
            while image_pub.get_num_connections() == 0 and time.monotonic() < deadline:
                if node.poll() is not None:
                    raise RuntimeError(
                        "Node exited:\n" + (output / "node.log").read_text()[-5000:]
                    )
                time.sleep(0.05)
            assert image_pub.get_num_connections() > 0, "Node did not subscribe"
            normal = during(pump(4.5))
            driving = [(wall, msg) for wall, msg in normal if msg.Go]
            assert len(driving) >= 5, "No stable tracking: %r" % statuses[-6:]
            intervals = np.diff([wall for wall, _ in driving])
            assert np.all(np.diff([message.timestamp for _, message in driving]) > 0)
            assert intervals.min() >= 0.45, "Normal path output exceeds configured 2 Hz"
            assert intervals.max() < 1.1, "Unexpected gaps in normal path output"
            lengths = []
            for _, goal in driving:
                points = np.array([[point.x, point.y] for point in goal.refPath])
                length = np.linalg.norm(np.diff(points, axis=0), axis=1).sum()
                lengths.append(float(length))
                assert 5 <= length <= 10.01
                assert np.max(np.abs(points[:, 0] - 100)) < 0.15
                assert points[-1, 1] - points[0, 1] > 5
                assert max(abs(p.heading - math.pi / 2) for p in goal.refPath) < 0.15
                assert goal.Estop == 0 and goal.Signal == 0 and goal.objects == []
                assert goal.timestamp in image_stamps, (
                    "Path was restamped instead of retaining image time"
                )
                assert abs(goal.refPath[0].t - goal.timestamp) < 1e-6
                assert np.all(np.diff([point.t for point in goal.refPath]) > 0)
                assert goal.refPath[-1].v == 0

            stop_latencies = {}
            for failure, images, poses, bound in [
                ("image_dropout", False, True, 1.0),
                ("localization_dropout", True, False, 0.65),
            ]:
                interval = pump(1.8, images=images, poses=poses)
                stopped = [
                    (wall, message)
                    for wall, message in during(interval)
                    if not message.Go
                ]
                assert stopped, failure + " did not stop"
                stop_latencies[failure] = stopped[0][0] - interval[0]
                assert stop_latencies[failure] <= bound, failure + " stop was too late"
                for wall, message in during(interval):
                    if wall > interval[0] + bound:
                        assert not message.Go and message.Estop > 0
                        assert message.refPath == [] and message.objects == []
                recovered = during(pump(2.5))
                assert sum(message.Go for _, message in recovered) >= 2, (
                    failure + " did not recover: %r" % statuses[-5:]
                )
            published = rospy.get_published_topics()
            assert not callback_errors, callback_errors
            assert all(
                name.startswith("/smoke/")
                or name in ("/tf_static", "/rosout", "/rosout_agg")
                for name, _ in published
            ), published
            result = {
                "status": "passed",
                "isolated_master": os.environ["ROS_MASTER_URI"],
                "normal_drive_messages": len(driving),
                "minimum_path_length_m": min(lengths),
                "minimum_publish_interval_s": float(intervals.min()),
                "stop_latency_s": stop_latencies,
                "coordinate_mode": "world ENU",
                "message_serialization": "generated ROS classes round-trip",
                "limitation": "Object.msg is a test-only stub; production Goal MD5 and real controller are not validated",
            }
            (output / "result.json").write_text(json.dumps(result, indent=2))
            print(json.dumps(result))
        finally:
            stop_process(node)
            for subscriber in subscribers:
                subscriber.unregister()
            rospy.signal_shutdown("isolated test complete")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / ".cache/ros-smoke")
    parser.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.worker:
        exercise_node(args.output.resolve())
    else:
        run_isolated(args.output.resolve())


if __name__ == "__main__":
    main()
