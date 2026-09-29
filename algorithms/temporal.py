"""Vision-only local paths; the platform owns all executed controls."""

import math

from pathlab.adapters import PurePursuit, execution_action
from pathlab.sdk import Action, AlgorithmOutput
from .motion import MotionEstimate
from .vision import TargetTracker


class StudentAlgorithm:
    def initialize(self, config, public_context):
        self.limits = public_context.get("vehicle_limits")
        self.execution = public_context.get("execution", "path")
        self.start_on_path = public_context.get("start_on_path", False)
        self.config = config

    def reset(self, initial_observation, task_hint):
        self.last_time = initial_observation.timestamp_s
        self.last_action = Action(steering_angle_rad=0, speed_mps=0)
        if self.limits is None:
            return
        self.tracker = TargetTracker(
            start_on_path=self.start_on_path,
            minimum_radius=self.limits["wheelbase_m"]
            / math.tan(self.limits["max_steering_rad"]),
        )
        self.motion = MotionEstimate(self.limits)
        self.adapter = PurePursuit(
            self.limits["wheelbase_m"],
            self.limits["max_speed_mps"],
            max_steering_rad=self.limits["max_steering_rad"],
        )

    def step(self, observation):
        if self.limits is None or observation.calibration is None:
            return AlgorithmOutput(
                status="LOST", diagnostics=["课堂示例需要仿真相机标定和车辆参数"]
            )
        elapsed = observation.timestamp_s - self.last_time
        if elapsed < 0:
            return AlgorithmOutput(status="ERROR", diagnostics=["时间倒退，请重置"])
        if elapsed:
            translation, yaw = self.motion.advance(
                self.last_action, elapsed, observation.dt_s
            )
            self.tracker.advance(translation, yaw)
        self.last_time = observation.timestamp_s
        track = self.tracker.observe(observation, max(elapsed, observation.dt_s))
        confidence = min(track.confidence, 0.4) if track.predicted else track.confidence
        path = track.path
        output = AlgorithmOutput(
            status=track.status,
            confidence=confidence,
            local_path_m=path.tolist() if path is not None else None,
            centerline_px=self.tracker.camera.pixels(path).tolist()
            if path is not None
            else None,
            candidates_px=track.candidates,
            debug={
                "prediction_only": track.predicted,
                "missing_s": self.tracker.missing_s,
                "motion_source": "predicted_path_execution",
            },
            diagnostics=[track.reason],
        )
        # Prediction only: estimate how the shared executor moves this frame's
        # path before associating the next image. Nothing is returned in action.
        self.last_action, _ = execution_action(output, self.execution, self.adapter)
        return output

    def close(self):
        pass
