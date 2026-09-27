"""Short, uncertainty-bounded continuation of an actually observed ordered road.

Forecasts are never fitted back into this model. Only fresh camera associations
may refresh its age, travelled distance and geometric support.
"""

import math

import numpy as np


class RouteForecast:
    def __init__(self):
        self.observed = None
        self.origin = np.zeros(2)
        self.heading = self.curvature = self.residual = self.span = 0.0
        self.age = self.travel = 0.0

    def advance(self, translation, rotation, yaw):
        if self.observed is not None:
            self.observed = (self.observed - translation) @ rotation
            self.origin = (self.origin - translation) @ rotation
            self.heading -= yaw
            self.travel += float(np.linalg.norm(translation))

    def observe(self, path, obstacles):
        if path is None or len(path) < 12:
            return
        points = np.asarray(path)
        # Use only the last contiguous clean run, not prop contact edges or a
        # straight chord joining disconnected pieces across an occlusion.
        clean = np.ones(len(points), dtype=bool)
        for item in obstacles:
            clean &= np.linalg.norm(points - item.center, axis=1) > item.radius + 0.18
        indices = np.flatnonzero(clean)
        if not len(indices):
            return
        observed = points[: indices[-1] + 1].copy()
        parts = np.split(indices, np.flatnonzero(np.diff(indices) > 1) + 1)
        selected = parts[-1]
        points = points[selected]
        if len(points) < 12:
            return
        arc = np.r_[0, np.cumsum(np.linalg.norm(np.diff(points, axis=0), axis=1))]
        keep = arc >= arc[-1] - 1.4
        points, arc = points[keep], arc[keep]
        span = float(arc[-1] - arc[0])
        if span < 0.7:
            return
        s = np.linspace(-span, 0, max(15, round(span / 0.05)))
        samples = np.column_stack(
            [np.interp(s, arc - arc[-1], points[:, axis]) for axis in range(2)]
        )
        coefficients = np.polyfit(s, samples, 2)
        fitted = (
            s[:, None] ** 2 * coefficients[0]
            + s[:, None] * coefficients[1]
            + coefficients[2]
        )
        residual = float(np.sqrt(np.mean(np.sum((samples - fitted) ** 2, axis=1))))
        linear = np.polyfit(s, samples, 1)
        linear_error = float(
            np.sqrt(
                np.mean(
                    np.sum(
                        (samples - (s[:, None] * linear[0] + linear[1])) ** 2, axis=1
                    )
                )
            )
        )
        # Do not magnify pixel staircases into a long curved extrapolation.
        # Prefer the simpler straight model when the whole visible run supports it.
        if linear_error < 0.012:
            coefficients = np.vstack([np.zeros(2), linear])
            residual = linear_error
        velocity, acceleration = coefficients[1], 2 * coefficients[0]
        norm = float(np.linalg.norm(velocity))
        curvature = float(
            (velocity[0] * acceleration[1] - velocity[1] * acceleration[0])
            / max(norm**3, 1e-6)
        )
        if residual > 0.025 or not 0.85 < norm < 1.15 or abs(curvature) > 1.5:
            # A poor fit is not a new road observation. Keep the last valid
            # model under its original age/distance budget, without refreshing it.
            return
        # The tail window estimates future geometry; it must not discard an
        # already observed bend between the vehicle and that window.
        self.observed = observed
        self.origin = coefficients[2].copy()
        self.heading = math.atan2(velocity[1], velocity[0])
        self.curvature, self.residual, self.span = curvature, residual, span
        self.age = self.travel = 0.0

    def uncertainty(self, distance):
        return (
            0.02
            + 3 * self.residual
            + (0.012 + 2 * self.residual / max(self.span, 0.7)) * distance
            + (0.004 + 2 * self.residual / max(self.span, 0.7) ** 2) * distance**2
        )

    @property
    def trustworthy(self):
        tangent = np.array([math.cos(self.heading), math.sin(self.heading)])
        forward_needed = max(0.0, -float(self.origin @ tangent)) + 1.0
        return bool(
            self.observed is not None
            and self.age < 20
            and self.travel < 4.5
            and self.uncertainty(forward_needed) < 0.28
            and abs(self.curvature) * forward_needed < 0.7
        )

    def continuation(self):
        if not self.trustworthy:
            return None
        distances = np.arange(0.05, 4.51, 0.05)
        distances = distances[
            (self.uncertainty(distances) < 0.28)
            & (abs(self.curvature) * distances < 0.7)
        ]
        if not len(distances):
            return None
        angle = self.curvature * distances
        length = distances * np.sinc(angle / (2 * np.pi))
        heading = self.heading + angle / 2
        extension = (
            self.origin + length[:, None] * np.c_[np.cos(heading), np.sin(heading)]
        )
        return np.vstack([self.observed[:-1], self.origin, extension])
