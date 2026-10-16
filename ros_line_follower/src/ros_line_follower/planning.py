"""Ordered, metric reference paths. No extrapolation, ROS, or vehicle actuation."""

from __future__ import annotations

from dataclasses import dataclass, fields
import math

import numpy as np


@dataclass(frozen=True)
class PlannerConfig:
    target_length_m: float = 10.0
    min_length_m: float = 5.0
    spacing_m: float = 0.15
    max_speed_mps: float = 0.6
    max_lateral_accel_mps2: float = 0.4
    braking_mps2: float = 0.6
    minimum_radius_m: float = 2.0
    stop_margin_m: float = 0.4
    left_width_m: float = 0.25
    right_width_m: float = 0.25
    turning_threshold_per_m: float = 0.08
    min_confidence: float = 0.35
    max_gap_m: float = 1.0
    max_start_distance_m: float = 1.5
    smoothing_m: float = 0.20
    max_smoothing_deviation_m: float = 0.12

    def __post_init__(self):
        for field in fields(self):
            value = getattr(self, field.name)
            if (
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not math.isfinite(value)
            ):
                raise ValueError("%s must be a finite number" % field.name)
            if value <= 0 and field.name != "stop_margin_m":
                raise ValueError("%s must be positive" % field.name)
        if self.stop_margin_m < 0:
            raise ValueError("stop_margin_m cannot be negative")
        if self.target_length_m < self.min_length_m:
            raise ValueError("target_length_m must be at least min_length_m")
        if self.spacing_m >= self.min_length_m / 3:
            raise ValueError("spacing_m is too large for min_length_m")
        if not 0 < self.min_confidence <= 1:
            raise ValueError("min_confidence must lie in (0, 1]")


@dataclass(frozen=True)
class ReferencePath:
    points: np.ndarray
    heading: np.ndarray
    curvature: np.ndarray
    speed: np.ndarray
    time: np.ndarray
    length_m: float


def _arc(points):
    return np.r_[0.0, np.cumsum(np.linalg.norm(np.diff(points, axis=0), axis=1))]


def _sample(points, arc, distances):
    return np.column_stack(
        [np.interp(distances, arc, points[:, axis]) for axis in (0, 1)]
    )


def _start_from_vehicle(points, config):
    """Select only the ordered initial approach, never a nearby later loop."""
    segments = np.diff(points, axis=0)
    lengths2 = np.sum(segments * segments, axis=1)
    fraction = np.clip(-np.sum(points[:-1] * segments, axis=1) / lengths2, 0, 1)
    closest = points[:-1] + fraction[:, None] * segments
    eligible = (
        (segments[:, 0] > 0)
        & (closest[:, 0] >= -0.05)
        & (np.linalg.norm(closest, axis=1) <= config.max_start_distance_m)
    )
    candidates = np.flatnonzero(eligible)
    if not len(candidates):
        raise ValueError("path has no nearby forward-facing start")
    # Search only one short initial arc, retaining the supplied branch identity.
    first = int(candidates[0])
    arc = _arc(points)
    candidates = candidates[arc[candidates] <= arc[first] + config.max_start_distance_m]
    index = int(candidates[np.argmin(np.linalg.norm(closest[candidates], axis=1))])
    if abs(math.atan2(segments[index, 1], segments[index, 0])) > math.pi / 3:
        raise ValueError("path starts with an unreachable heading")
    start = closest[index]
    remaining = points[index + 1 :]
    if np.linalg.norm(start - remaining[0]) < 1e-6:
        return remaining.copy()
    return np.vstack((start, remaining))


def _smooth(points, config):
    """Bounded Gaussian smoothing with fitted endpoint tangents.

    A skeleton's first pixel step is often diagonal at an image boundary. Its
    direction is not a reliable tangent: extending that one step can manufacture
    a sharp turn after smoothing. Fit a local quadratic over the kernel support
    instead. Padding is only for convolution, never part of the output path.
    """
    arc = _arc(points)
    count = max(3, int(math.ceil(arc[-1] / min(config.spacing_m / 2, 0.075))) + 1)
    distances = np.linspace(0.0, arc[-1], count)
    dense = _sample(points, arc, distances)
    step = distances[1]
    radius = min(count - 1, max(1, int(math.ceil(3 * config.smoothing_m / step))))
    offsets = np.arange(-radius, radius + 1) * step
    kernel = np.exp(-0.5 * (offsets / config.smoothing_m) ** 2)
    kernel /= kernel.sum()
    support = min(count, max(4, radius + 1))
    local_arc = np.arange(support) * step

    def padding(endpoint):
        coefficients = np.polynomial.polynomial.polyfit(local_arc, endpoint, 2)
        extension = -np.arange(radius, 0, -1) * step
        return (
            endpoint[0]
            + extension[:, None] * coefficients[1]
            + extension[:, None] ** 2 * coefficients[2]
        )

    before = padding(dense[:support])
    after = padding(dense[-support:][::-1])[::-1]
    padded = np.vstack((before, dense, after))
    smoothed = np.column_stack(
        [np.convolve(padded[:, axis], kernel, mode="valid") for axis in (0, 1)]
    )
    if (
        np.max(np.linalg.norm(smoothed - dense, axis=1))
        > config.max_smoothing_deviation_m
    ):
        raise ValueError("path needs excessive smoothing; keep collecting observations")
    return smoothed


def build_reference(
    path_body, config: PlannerConfig, confidence: float
) -> ReferencePath:
    """Body axes: x forward, y left; ordered points in metres, headings in radians.

    A finite visible prefix is smoothed and sampled by travelled distance. A tail
    margin is reserved before its final stop. Sharp bends and missing segments
    fail closed; the caller must publish a stop instead of stretching the path.
    """
    if not math.isfinite(confidence) or not config.min_confidence <= confidence <= 1:
        raise ValueError("line confidence is insufficient or invalid")
    points = np.asarray(path_body, dtype=float)
    if points.ndim != 2 or points.shape[1] != 2 or len(points) < 3:
        raise ValueError("path must contain at least three ordered (x, y) points")
    if not np.all(np.isfinite(points)) or np.max(np.abs(points)) > 1000:
        raise ValueError("path coordinates must be finite metres within 1 km")
    points = points[np.r_[True, np.linalg.norm(np.diff(points, axis=0), axis=1) > 1e-6]]
    if len(points) < 3:
        raise ValueError("path contains too few distinct points")
    gaps = np.linalg.norm(np.diff(points, axis=0), axis=1)
    # Keep a valid visible prefix, but never bridge a missing section.
    discontinuities = np.flatnonzero(gaps > config.max_gap_m)
    if len(discontinuities):
        points = points[: int(discontinuities[0]) + 1]
    if len(points) < 3:
        raise ValueError("path begins with a discontinuity")
    points = _start_from_vehicle(points, config)
    if len(points) < 3 or _arc(points)[-1] < config.min_length_m + config.stop_margin_m:
        raise ValueError("continuous observed path is too short")
    # Limit processing to the requested horizon plus smoothing support.
    arc = _arc(points)
    end = min(
        arc[-1], config.target_length_m + config.stop_margin_m + 3 * config.smoothing_m
    )
    prefix = points[arc < end]
    points = np.vstack((prefix, _sample(points, arc, np.array([end]))))
    points = _smooth(points, config)
    arc = _arc(points)
    length = min(config.target_length_m, arc[-1] - config.stop_margin_m)
    if length < config.min_length_m:
        raise ValueError("usable path is too short after smoothing and stop margin")
    distances = np.linspace(0, length, int(math.ceil(length / config.spacing_m)) + 1)
    sampled = _sample(points, arc, distances)
    # Derivatives use actual chord lengths rather than assuming equal spacing.
    actual_arc = _arc(sampled)
    derivative = np.gradient(sampled, actual_arc, axis=0, edge_order=2)
    heading = np.unwrap(np.arctan2(derivative[:, 1], derivative[:, 0]))
    curvature = np.gradient(heading, actual_arc, edge_order=2)
    if (
        not np.all(np.isfinite(curvature))
        or np.max(np.abs(curvature)) > 1 / config.minimum_radius_m + 1e-3
    ):
        raise ValueError("reference curvature exceeds the configured vehicle limit")
    speed = np.minimum(
        config.max_speed_mps * (0.35 + 0.65 * confidence),
        np.sqrt(config.max_lateral_accel_mps2 / np.maximum(np.abs(curvature), 1e-9)),
    )
    speed[-1] = 0.0
    lengths = np.diff(actual_arc)
    for index in range(len(speed) - 2, -1, -1):
        speed[index] = min(
            speed[index],
            math.sqrt(speed[index + 1] ** 2 + 2 * config.braking_mps2 * lengths[index]),
        )
    travel_time = np.r_[0.0, np.cumsum(2 * lengths / (speed[:-1] + speed[1:]))]
    heading = (heading + math.pi) % (2 * math.pi) - math.pi
    return ReferencePath(
        sampled, heading, curvature, speed, travel_time, float(actual_arc[-1])
    )
