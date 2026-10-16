"""Exact Goal/RefPoint wire adapter; message classes come from the real ROS build."""

from __future__ import annotations

import math

import numpy as np

from .planning import PlannerConfig, ReferencePath


_POINT_FIELDS = (
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
_POINT_TYPES = ("float64",) * 8 + ("int16",)
_GOAL_FIELDS = ("timestamp", "Estop", "Go", "Signal", "refPath", "mode", "objects")


def validate_message_types(GoalType, RefPointType):
    """Validate generated ROS schemas, including the Goal's actual package names.

    Object's contents are intentionally unspecified: no objects are synthesized.
    ROS still requires its genuine generated definition to import Goal correctly.
    """
    point_type = getattr(RefPointType, "_type", "")
    goal_type = getattr(GoalType, "_type", "")
    goal_slots = tuple(getattr(GoalType, "__slots__", ()))
    goal_types = tuple(getattr(GoalType, "_slot_types", ()))
    if "/" not in point_type or point_type.rsplit("/", 1)[1] != "RefPoint":
        raise ValueError(
            "RefPointType must be a generated package/RefPoint ROS message"
        )
    if "/" not in goal_type or goal_type.rsplit("/", 1)[1] != "Goal":
        raise ValueError("GoalType must be a generated package/Goal ROS message")
    if (
        tuple(getattr(RefPointType, "__slots__", ())) != _POINT_FIELDS
        or tuple(getattr(RefPointType, "_slot_types", ())) != _POINT_TYPES
    ):
        raise ValueError("RefPoint schema differs from the supplied RefPoint.msg")
    if goal_slots != _GOAL_FIELDS or len(goal_types) != len(_GOAL_FIELDS):
        raise ValueError("Goal fields differ from the supplied Goal.msg")
    expected = ("float64", "int16", "bool", "int16", point_type + "[]", "int16")
    if goal_types[:-1] != expected:
        raise ValueError(
            "Goal field types or its RefPoint package reference do not match"
        )
    object_type = goal_types[-1]
    if "/" not in object_type or object_type.rsplit("/", 1)[1] != "Object[]":
        raise ValueError(
            "Goal.objects must use its actual generated package/Object[] type"
        )
    # Bare RefPoint/Object names in the supplied Goal.msg resolve in its package.
    package = goal_type.rsplit("/", 1)[0]
    if point_type != package + "/RefPoint" or object_type != package + "/Object[]":
        raise ValueError(
            "Goal's RefPoint and Object must belong to its actual message package"
        )


def _int16(value, name):
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or not -32768 <= value <= 32767
    ):
        raise ValueError("%s must be a signed int16" % name)
    return value


def make_goal(
    GoalType,
    RefPointType,
    reference: ReferencePath,
    stamp,
    config: PlannerConfig,
    *,
    pose_xy_yaw,
    output_frame: str,
    point_time_mode: str,
    mode: int,
    enabled: bool = True,
    estop_level: int = 1,
):
    """Use the observation timestamp, never a fresh stamp for stale geometry.

    Vehicle coordinates are forward/left; world coordinates are ENU, with CCW
    headings from +x. Widths are configured corridors, not measured free space.
    Stop messages contain no points and explicitly set Go=False and Estop>0.
    """
    validate_message_types(GoalType, RefPointType)
    if output_frame not in ("world", "vehicle"):
        raise ValueError("output_frame must explicitly be 'world' or 'vehicle'")
    if point_time_mode not in ("relative", "absolute"):
        raise ValueError("point_time_mode must explicitly be 'relative' or 'absolute'")
    timestamp = float(stamp.to_sec() if hasattr(stamp, "to_sec") else stamp)
    if not math.isfinite(timestamp) or timestamp < 0:
        raise ValueError("observation timestamp must be finite and nonnegative")
    mode = _int16(mode, "mode")
    if mode not in (1, 2, 3):
        raise ValueError("mode must be 1, 2, or 3 as specified by Goal.msg")
    estop_level = _int16(estop_level, "estop_level")
    if estop_level not in (1, 2, 3):
        raise ValueError("stop Estop level must be 1, 2, or 3")
    if not isinstance(enabled, bool):
        raise ValueError("enabled must be bool")
    goal = GoalType()
    goal.timestamp = timestamp
    goal.Estop = 0 if enabled else estop_level
    goal.Go = enabled
    goal.Signal = 0
    goal.refPath = []
    goal.mode = mode
    goal.objects = []
    if not enabled:
        return goal
    if reference is None:
        raise ValueError("an enabled Goal requires a valid reference path")
    points = np.asarray(reference.points, dtype=float)
    count = len(points)
    arrays = [
        np.asarray(getattr(reference, key), dtype=float)
        for key in ("heading", "curvature", "speed", "time")
    ]
    if (
        points.shape != (count, 2)
        or count < 3
        or any(a.shape != (count,) for a in arrays)
    ):
        raise ValueError("reference arrays have inconsistent dimensions")
    if not all(np.all(np.isfinite(a)) for a in [points] + arrays):
        raise ValueError("reference contains non-finite values")
    heading, curvature, speed, times = arrays
    if (
        np.any(speed < 0)
        or speed[-1] != 0
        or times[0] != 0
        or np.any(np.diff(times) <= 0)
    ):
        raise ValueError(
            "reference must have forward speeds, a final stop, and increasing relative times"
        )
    if output_frame == "world":
        pose = np.asarray(pose_xy_yaw, dtype=float)
        if pose.shape != (3,) or not np.all(np.isfinite(pose)):
            raise ValueError(
                "world output requires a finite observation-time (x, y, yaw) pose"
            )
        c, s = math.cos(pose[2]), math.sin(pose[2])
        points = points @ np.array([[c, s], [-s, c]]) + pose[:2]
        heading = heading + pose[2]
    heading = (heading + math.pi) % (2 * math.pi) - math.pi
    if point_time_mode == "absolute":
        times = times + timestamp
    if (
        not np.all(np.isfinite(points))
        or not np.all(np.isfinite(times))
        or np.any(np.diff(times) <= 0)
    ):
        raise ValueError("output coordinates or timestamps exceed numeric precision")
    for index in range(count):
        point = RefPointType()
        point.t = float(times[index])
        point.x = float(points[index, 0])
        point.y = float(points[index, 1])
        point.v = float(speed[index])
        point.heading = float(heading[index])
        point.cr = float(curvature[index])
        point.left_width = float(config.left_width_m)
        point.right_width = float(config.right_width_m)
        point.turning_flag = int(abs(point.cr) >= config.turning_threshold_per_m)
        goal.refPath.append(point)
    return goal
