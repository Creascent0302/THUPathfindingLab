"""ROS 1 transport. Perception never estimates motion from its own commands."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
import json
import math
import threading
import time

import numpy as np
import rospy
import roslib.message
import tf2_ros
from cv_bridge import CvBridge
from geometry_msgs.msg import PoseStamped
from nav_msgs.msg import Path
from sensor_msgs.msg import CameraInfo, Image
from std_msgs.msg import String

from .geometry import (
    Pose2,
    PoseBuffer,
    PublicationGate,
    ground_homography,
    relative_motion,
    rigid_transform,
    rotation,
)
from .messages import make_goal, validate_message_types
from .planning import PlannerConfig, build_reference
from .vision import TargetTracker, VisionConfig


@dataclass(frozen=True)
class RuntimeConfig:
    process_hz: float = 10.0
    publish_hz: float = 2.0
    max_image_age_s: float = 0.75
    max_pose_age_s: float = 0.35
    max_pose_gap_s: float = 0.2
    max_frame_gap_s: float = 0.6
    max_speed_mps: float = 2.0
    max_yaw_rate_rad_s: float = 1.2
    max_tilt_rad: float = 0.2
    future_tolerance_s: float = 0.05
    stop_estop_level: int = 1

    def __post_init__(self):
        if not all(math.isfinite(value) for value in self.__dict__.values()):
            raise ValueError("运行参数必须有限")
        if not 1 <= self.process_hz <= 20 or not 0.2 <= self.publish_hz <= min(
            5, self.process_hz
        ):
            raise ValueError(
                "处理频率应为1～20 Hz，发布频率应为0.2～5 Hz且不高于处理频率"
            )
        for key in (
            "max_image_age_s",
            "max_pose_age_s",
            "max_pose_gap_s",
            "max_frame_gap_s",
        ):
            if not 0 < getattr(self, key) <= 2:
                raise ValueError(key + " 应在 (0,2] 秒内")
        if self.max_pose_gap_s > 1:
            raise ValueError("max_pose_gap_s 不得超过1秒")
        if not 0 < self.max_speed_mps <= 10 or not 0 < self.max_yaw_rate_rad_s <= 3:
            raise ValueError("定位运动门限无效")
        if not 0 < self.max_tilt_rad <= 0.35 or not 0 <= self.future_tolerance_s <= 0.1:
            raise ValueError("地面倾角或未来时间容差无效")
        if type(self.stop_estop_level) is not int or self.stop_estop_level not in (
            1,
            2,
            3,
        ):
            raise ValueError("停止等级必须是1、2或3")


def required(name):
    value = rospy.get_param("~" + name, None)
    if value is None or value == "":
        raise ValueError("请在配置中填写 ~" + name + "；当前实车文件未定义它，不能猜测")
    return value


def message_class(name):
    cls = roslib.message.get_message_class(name)
    if cls is None:
        raise ValueError("无法加载 " + name + "，请先编译并 source 实车消息包")
    return cls


class LineFollowerNode:
    def __init__(self):
        self.runtime = RuntimeConfig(**rospy.get_param("~runtime", {}))
        self.planner = PlannerConfig(**rospy.get_param("~planner", {}))
        vision = dict(rospy.get_param("~vision", {}))
        vision["minimum_radius_m"] = self.planner.minimum_radius_m
        self.vision = VisionConfig(**vision)
        self.frame = str(required("vehicle_frame"))
        self.output_frame = str(required("output_frame"))
        self.point_time_mode = str(required("point_time_mode"))
        self.ground_z = float(required("ground_z_m"))
        self.world_frame = str(rospy.get_param("~world_frame", "utm"))
        if self.frame == "camera_init" or self.world_frame == "camera_init":
            raise ValueError(
                "camera_init 是滚动栅格原点，不能用作定位车体系或固定世界系"
            )
        if self.output_frame not in ("world", "vehicle"):
            raise ValueError("output_frame 必须按控制端约定填写 world 或 vehicle")
        if self.point_time_mode not in ("absolute", "relative"):
            raise ValueError(
                "point_time_mode 必须按控制端约定填写 absolute 或 relative"
            )
        if not math.isfinite(self.ground_z):
            raise ValueError("ground_z_m 必须是实测地面在车体系中的高度")
        if self.vision.memory_s > self.runtime.max_image_age_s:
            raise ValueError("视觉预测记忆不能超过图像有效期")
        self.enable_motion = rospy.get_param("~enable_motion", False)
        if type(self.enable_motion) is not bool:
            raise ValueError("enable_motion 必须是布尔值")
        self.mode = rospy.get_param("~mode", 3)
        self.Goal = message_class(str(required("goal_type")))
        if "refPath" not in self.Goal.__slots__:
            raise ValueError("Goal 消息没有 refPath")
        ref_type = self.Goal._slot_types[self.Goal.__slots__.index("refPath")]
        if not ref_type.endswith("[]"):
            raise ValueError("Goal.refPath 必须是 RefPoint[]")
        self.RefPoint = message_class(ref_type[:-2])
        validate_message_types(self.Goal, self.RefPoint)
        # Validate mode and all output semantics before connecting subscribers.
        make_goal(
            self.Goal,
            self.RefPoint,
            None,
            1.0,
            self.planner,
            pose_xy_yaw=(0, 0, 0),
            output_frame=self.output_frame,
            point_time_mode=self.point_time_mode,
            mode=self.mode,
            enabled=False,
            estop_level=self.runtime.stop_estop_level,
        )
        self.VehicleState = message_class("cav_msgs/VehicleState")
        for name in (
            "timestamp",
            "x",
            "y",
            "heading",
            "roll",
            "pitch",
            "speed_x",
            "speed_y",
        ):
            if name not in self.VehicleState.__slots__:
                raise ValueError("VehicleState 缺少 " + name)
        self.goal_pub = rospy.Publisher(
            str(required("goal_topic")), self.Goal, queue_size=1, latch=False
        )
        self.path_pub = rospy.Publisher(
            "~reference_path", Path, queue_size=1, latch=False
        )
        self.status_pub = rospy.Publisher("~status", String, queue_size=1, latch=False)
        self.bridge = CvBridge()
        self.tf = tf2_ros.Buffer(cache_time=rospy.Duration(5))
        self.tf_listener = tf2_ros.TransformListener(self.tf)
        self.lock = threading.RLock()
        self.closed = threading.Event()
        self.poses = PoseBuffer(self.runtime.max_pose_gap_s)
        self.images = deque(maxlen=6)
        self.info = None
        self.info_valid_from = 0.0
        self.latest = None
        self.restart_required = False
        self.epoch = 0
        self.reason = "等待图像、定位和相机标定"
        self.last_image_stamp = 0.0
        self.last_pose_wall = -math.inf
        self.gate = PublicationGate(self.runtime.publish_hz)
        self.subscribers = [
            rospy.Subscriber(
                rospy.get_param("~vehicle_state_topic", "/vehicle/vehicle_state"),
                self.VehicleState,
                self._pose,
                queue_size=50,
                tcp_nodelay=True,
            ),
            rospy.Subscriber(
                str(required("camera_info_topic")), CameraInfo, self._info, queue_size=1
            ),
            rospy.Subscriber(
                str(required("image_topic")),
                Image,
                self._image,
                queue_size=1,
                buff_size=32 * 1024**2,
                tcp_nodelay=True,
            ),
        ]
        self.threads = [
            threading.Thread(target=self._process, daemon=True),
            threading.Thread(target=self._publish, daemon=True),
        ]
        rospy.on_shutdown(self.close)
        for thread in self.threads:
            thread.start()

    def _fault(self, reason, reset=False):
        with self.lock:
            self.latest, self.reason = None, str(reason)
            if reset:
                self.epoch += 1
                self.images.clear()

    def _pose(self, message):
        try:
            now = rospy.Time.now().to_sec()
            pose = Pose2(
                float(message.timestamp),
                float(message.x),
                float(message.y),
                float(message.heading),
                math.hypot(message.speed_x, message.speed_y),
                float(message.roll),
                float(message.pitch),
            )
            if (
                not -self.runtime.future_tolerance_s
                <= now - pose.stamp
                <= self.runtime.max_pose_age_s
            ):
                raise ValueError("定位时间已过期或晚于 ROS 时钟")
            if max(abs(pose.roll), abs(pose.pitch)) > self.runtime.max_tilt_rad:
                raise ValueError("车身倾角超过平地投影适用范围")
            if pose.speed > self.runtime.max_speed_mps or message.speed_x < -0.03:
                raise ValueError("当前速度超出巡线配置或车辆正在倒车")
            with self.lock:
                if self.poses.poses:
                    previous = self.poses.poses[-1]
                    dt = pose.stamp - previous.stamp
                    translation, yaw = relative_motion(previous, pose)
                    if dt <= 0:
                        if dt < 0:
                            self.restart_required = True
                        raise ValueError("定位时间戳重复或倒退")
                    if (
                        np.linalg.norm(translation)
                        > 0.1 + self.runtime.max_speed_mps * dt
                        or abs(yaw) > 0.1 + self.runtime.max_yaw_rate_rad_s * dt
                    ):
                        self.restart_required = True
                        raise ValueError("定位突跳，丢弃旧路径并重新建立时序")
                self.poses.push(pose)
                self.last_pose_wall = time.monotonic()
        except (ValueError, TypeError) as error:
            with self.lock:
                self.poses.clear()
                reason = str(error)
                if self.restart_required:
                    reason += "；路线身份无法确认，请将车放回原线后重启节点"
                self._fault(reason, reset=True)

    def _info(self, message):
        def signature(info):
            return (
                info.header.frame_id,
                info.width,
                info.height,
                tuple(info.P),
                tuple(info.R),
                info.binning_x,
                info.binning_y,
                info.roi.x_offset,
                info.roi.y_offset,
                info.roi.width,
                info.roi.height,
            )

        with self.lock:
            stamp = message.header.stamp.to_sec()
            now = rospy.Time.now().to_sec()
            if (
                not math.isfinite(stamp)
                or stamp < 0
                or stamp > now + self.runtime.future_tolerance_s
            ):
                self._fault("相机标定时间戳无效", reset=True)
                return
            if stamp and stamp < self.info_valid_from:
                return  # A delayed calibration cannot replace the newer one.
            changed = self.info is not None and signature(message) != signature(
                self.info
            )
            if changed:
                self._fault("相机标定变化，等待使用新标定的图像", reset=True)
                self.info_valid_from = now if stamp == 0 else stamp
            elif self.info is None:
                self.info_valid_from = stamp
            self.info = message

    def _image(self, message):
        stamp = message.header.stamp.to_sec()
        now = rospy.Time.now().to_sec()
        with self.lock:
            if (
                not math.isfinite(stamp)
                or stamp <= 0
                or not -self.runtime.future_tolerance_s
                <= now - stamp
                <= self.runtime.max_image_age_s
            ):
                self._fault("图像时间戳无效、过期或与 ROS 时钟不同源", reset=True)
                return
            if stamp <= self.last_image_stamp:
                self.last_image_stamp = stamp
                self._fault("图像时间戳重复或倒退", reset=True)
                return
            self.last_image_stamp = stamp
            self.images.append(message)

    def _take_frame(self):
        with self.lock:
            if self.info is None:
                return None
            # Use the newest frame already bracketed by localization. Waiting
            # for the later pose is better than pairing with the last callback.
            for message in reversed(self.images):
                if message.header.stamp.to_sec() < self.info_valid_from:
                    continue
                try:
                    pose = self.poses.at(message.header.stamp.to_sec())
                except ValueError:
                    continue
                self.images = deque(
                    (m for m in self.images if m.header.stamp > message.header.stamp),
                    maxlen=6,
                )
                return message, self.info, pose, self.epoch
        return None

    def _calibration(self, image, info):
        if not image.header.frame_id or image.header.frame_id != info.header.frame_id:
            raise ValueError("图像与 CameraInfo 必须使用同一个 optical frame")
        if (image.width, image.height) != (info.width, info.height):
            raise ValueError("图像与标定尺寸不符；不能仅缩放图像而不更新内参")
        if not 16 <= image.width <= 3840 or not 16 <= image.height <= 2160:
            raise ValueError("图像尺寸超限")
        if (
            info.binning_x not in (0, 1)
            or info.binning_y not in (0, 1)
            or any(
                (info.roi.x_offset, info.roi.y_offset, info.roi.width, info.roi.height)
            )
        ):
            raise ValueError("请提供已归一化为当前分辨率且无 ROI/binning 的 CameraInfo")
        transform = self.tf.lookup_transform(
            info.header.frame_id, self.frame, image.header.stamp, rospy.Duration(0.05)
        ).transform
        t, q = transform.translation, transform.rotation
        matrix = rigid_transform([t.x, t.y, t.z], [q.x, q.y, q.z, q.w])
        return ground_homography(info.P, info.R, matrix, self.ground_z)

    def _process(self):
        tracker, previous, calibration, epoch = (
            TargetTracker(self.vision),
            None,
            None,
            -1,
        )
        while not self.closed.is_set() and not rospy.is_shutdown():
            started = time.monotonic()
            selected = self._take_frame()
            if selected is None or self.restart_required:
                self.closed.wait(0.01)
                continue
            image, info, pose, current_epoch = selected
            try:
                h = self._calibration(image, info)
                changed = calibration is not None and not np.allclose(
                    h, calibration, atol=1e-6, rtol=1e-6
                )
                gap = (
                    previous is not None
                    and pose.stamp - previous.stamp > self.runtime.max_frame_gap_s
                )
                if current_epoch != epoch or changed or gap:
                    # Camera changes/outages do not authorize selecting another
                    # branch. The metric target remains in body coordinates.
                    tracker.invalidate_prediction()
                epoch, calibration = current_epoch, h
                dt = (
                    1 / self.runtime.process_hz
                    if previous is None
                    else pose.stamp - previous.stamp
                )
                if dt <= 0:
                    raise ValueError("感知帧时间倒退")
                if previous is not None:
                    tracker.advance(*relative_motion(previous, pose))
                previous = pose
                rgb = self.bridge.imgmsg_to_cv2(image, desired_encoding="rgb8")
                track = tracker.observe(rgb, h, dt)
                if track.path is None:
                    raise ValueError(track.reason)
                confidence = (
                    min(track.confidence, 0.5) if track.predicted else track.confidence
                )
                reference = build_reference(track.path, self.planner, confidence)
                # Output has enough observed length to stop from current measured speed.
                stopping = (
                    pose.speed**2 / (2 * self.planner.braking_mps2)
                    + self.planner.stop_margin_m
                )
                if reference.length_m < stopping:
                    raise ValueError("当前实际车速的制动距离超出有效路径")
                with self.lock:
                    if current_epoch == self.epoch:
                        self.latest = (
                            reference,
                            pose,
                            time.monotonic(),
                            track.predicted,
                        )
                        self.reason = track.reason
            except Exception as error:
                # A bad camera/TF/track frame cannot leave the last drive goal live.
                tracker.invalidate_prediction()
                self._fault(str(error))
                rospy.logwarn_throttle(2.0, "巡线暂停: %s", str(error))
            self.closed.wait(
                max(0, 1 / self.runtime.process_hz - (time.monotonic() - started))
            )

    def _publish(self):
        last_ros = None
        while not self.closed.wait(0.025) and not rospy.is_shutdown():
            now, wall = rospy.Time.now().to_sec(), time.monotonic()
            try:
                if last_ros is not None and now < last_ros:
                    with self.lock:
                        self.poses.clear()
                        self.last_image_stamp = 0
                        self.info = None
                        self.info_valid_from = 0
                        self.restart_required = True
                        self._fault(
                            "ROS 时钟倒退，请将车放回原线后重启节点", reset=True
                        )
                last_ros = now
                self._publish_cycle(now, wall)
            except Exception as error:
                self._fault("路径发布失败: " + str(error))
                rospy.logerr_throttle(2.0, "路径发布失败: %s", str(error))

    def _publish_cycle(self, now, wall):
        with self.lock:
            plan = self.latest
            valid = plan is not None and not self.restart_required
            if valid:
                age = now - plan[1].stamp
                valid = (
                    -self.runtime.future_tolerance_s
                    <= age
                    <= self.runtime.max_image_age_s
                )
                valid = valid and wall - plan[2] <= self.runtime.max_image_age_s
                valid = (
                    valid and wall - self.last_pose_wall <= self.runtime.max_pose_age_s
                )
                if valid and self.poses.poses:
                    current = self.poses.poses[-1]
                    # Account for motion since the image and one publication
                    # interval of reaction, using the latest measured speed.
                    remaining = plan[0].length_m - self.runtime.max_speed_mps * max(
                        age, 0
                    )
                    stopping = (
                        current.speed**2 / (2 * self.planner.braking_mps2)
                        + current.speed
                        * (self.gate.period + self.runtime.max_pose_age_s)
                        + self.planner.stop_margin_m
                    )
                    valid = remaining >= stopping
                else:
                    valid = False
                if not valid:
                    self._fault("图像/定位超时或当前车速所需制动空间不足，旧路径失效")
            stamp = plan[1].stamp if valid else max(now, 1e-9)
            if not self.gate.ready(wall, stamp, valid and self.enable_motion):
                return
            reference, pose = (
                (plan[0], plan[1]) if valid else (None, Pose2(stamp, 0, 0, 0))
            )
            goal = make_goal(
                self.Goal,
                self.RefPoint,
                reference,
                stamp,
                self.planner,
                pose_xy_yaw=(pose.x, pose.y, pose.yaw),
                output_frame=self.output_frame,
                point_time_mode=self.point_time_mode,
                mode=self.mode,
                enabled=valid and self.enable_motion,
                estop_level=self.runtime.stop_estop_level,
            )
            self.goal_pub.publish(goal)
            self._debug_path(reference, pose, stamp)
            self.status_pub.publish(
                String(
                    data=json.dumps(
                        {
                            "state": "TRACK" if goal.Go else "STOP",
                            "reason": self.reason,
                            "motion_enabled": self.enable_motion,
                            "image_stamp": stamp,
                            "points": len(goal.refPath),
                            "length_m": reference.length_m if reference else 0,
                            "prediction_only": bool(plan[3]) if valid else False,
                        },
                        ensure_ascii=False,
                    )
                )
            )

    def _debug_path(self, reference, pose, stamp):
        message = Path()
        message.header.stamp = rospy.Time.from_sec(stamp)
        message.header.frame_id = (
            self.world_frame if self.output_frame == "world" else self.frame
        )
        if reference is not None:
            points = reference.points
            headings = reference.heading
            if self.output_frame == "world":
                points = points @ rotation(pose.yaw).T + [pose.x, pose.y]
                headings = headings + pose.yaw
            for point, heading in zip(points, headings):
                output = PoseStamped()
                output.header = message.header
                output.pose.position.x, output.pose.position.y = map(float, point)
                output.pose.orientation.z = math.sin(heading / 2)
                output.pose.orientation.w = math.cos(heading / 2)
                message.poses.append(output)
        self.path_pub.publish(message)

    def close(self):
        if self.closed.is_set():
            return
        self.closed.set()
        with self.lock:
            stamp = max(rospy.Time.now().to_sec(), 1e-9)
            self.goal_pub.publish(
                make_goal(
                    self.Goal,
                    self.RefPoint,
                    None,
                    stamp,
                    self.planner,
                    pose_xy_yaw=(0, 0, 0),
                    output_frame=self.output_frame,
                    point_time_mode=self.point_time_mode,
                    mode=self.mode,
                    enabled=False,
                    estop_level=self.runtime.stop_estop_level,
                )
            )
        for thread in self.threads:
            if thread is not threading.current_thread():
                thread.join(timeout=1)


def main():
    rospy.init_node("ros_line_follower")
    try:
        LineFollowerNode()
        rospy.spin()
    except (ValueError, TypeError, KeyError) as error:
        rospy.logfatal("巡线配置无效: %s", error)
        raise SystemExit(2)
