"""Image-space baseline: independent row association and filtered PD steering."""

import cv2
import numpy as np

from pathlab.sdk import Action, AlgorithmOutput


class ScanlinePID:
    def initialize(self, config, public_context):
        self.speed = float(config.get("speed_mps", 0.5))
        self.kp = float(config.get("kp", 0.65))
        self.kd = float(config.get("kd", 0.035))
        self.limit = (public_context.get("vehicle_limits") or {}).get(
            "max_steering_rad", 0.52
        )

    def reset(self, initial_observation, task_hint):
        self.column = None
        self.error = self.derivative = self.steering = 0.0
        self.last_time = initial_observation.timestamp_s
        self.missing = 0.0

    def step(self, observation):
        if observation.timestamp_s < self.last_time:
            return AlgorithmOutput(
                status="ERROR", diagnostics=["时间倒退，请重置算法实例"]
            )
        rgb = observation.rgb()
        h, w = rgb.shape[:2]
        gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
        threshold = max(25, np.percentile(gray, 70) * 0.60)
        mask = (gray < threshold) & (
            (rgb.max(axis=2).astype(int) - rgb.min(axis=2)) < 50
        )
        dt = max(observation.dt_s, observation.timestamp_s - self.last_time)
        self.last_time = observation.timestamp_s
        hint = observation.task_hint
        top_of_marker = None
        if hint.kind == "marker":
            hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV)
            reference = cv2.cvtColor(np.uint8([[hint.marker_rgb]]), cv2.COLOR_RGB2HSV)[
                0, 0, 0
            ]
            difference = np.abs(hsv[:, :, 0].astype(int) - int(reference))
            marker_y, marker_x = np.where(
                (np.minimum(difference, 180 - difference) < 12)
                & (hsv[:, :, 1] > 90)
                & (hsv[:, :, 2] > 45)
            )
            if len(marker_x) >= 8:
                top_of_marker = int(np.percentile(marker_y, 10))
        if self.column is None:
            if hint.kind == "point":
                self.column = hint.point_px[0]
            elif hint.kind == "region":
                self.column = (hint.region_px[0] + hint.region_px[2]) / 2
            elif hint.kind == "marker":
                if top_of_marker is not None:
                    self.column = float(np.median(marker_x))
            if self.column is None:
                return AlgorithmOutput(
                    status="AMBIGUOUS",
                    action=Action(steering_angle_rad=0, speed_mps=0),
                    diagnostics=["扫描线基线需要明确初始化提示"],
                )
        centers = []
        column = self.column
        bottom = (
            min(int(h * 0.82), top_of_marker)
            if top_of_marker is not None
            else int(h * 0.82)
        )
        for y in range(bottom, int(h * 0.16), -5):
            xs = np.flatnonzero(mask[y])
            if not len(xs):
                continue
            groups = np.split(xs, np.flatnonzero(np.diff(xs) > 2) + 1)
            candidates = [float(g.mean()) for g in groups if len(g) >= 2]
            if not candidates:
                continue
            candidate = min(candidates, key=lambda u: abs(u - column))
            if abs(candidate - column) > w * 0.22:
                continue
            centers.append((candidate, float(y)))
            column = candidate
        if len(centers) < 3:
            self.missing += dt
            predict = self.missing <= 1.5
            return AlgorithmOutput(
                status="TRACK" if predict else "LOST",
                confidence=max(0.0, 0.4 * (1 - self.missing / 1.5)),
                action=Action(
                    steering_angle_rad=self.steering,
                    speed_mps=min(self.speed, 0.4) if predict else 0,
                ),
                diagnostics=["基线有界保持最后动作" if predict else "扫描线丢失，停车"],
            )
        self.missing = 0.0
        near = np.array(centers[: max(2, len(centers) // 3)])
        self.column = float(near[:, 0].mean())
        error = (w / 2 - self.column) / (w / 2)
        self.derivative = 0.75 * self.derivative + 0.25 * (error - self.error) / dt
        self.error = error
        target = self.kp * error + self.kd * self.derivative
        self.steering = float(
            np.clip(0.4 * target + 0.6 * self.steering, -self.limit, self.limit)
        )
        return AlgorithmOutput(
            status="TRACK",
            confidence=float(min(0.9, len(centers) / 20)),
            centerline_px=centers,
            action=Action(
                steering_angle_rad=self.steering,
                speed_mps=self.speed / (1 + abs(error)),
            ),
            debug={"normalized_image_error": error, "rows": len(centers)},
            diagnostics=["图像扫描线 PD 基线；没有拓扑身份保证"],
        )

    def close(self):
        pass
