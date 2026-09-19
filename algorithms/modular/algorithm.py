"""SDK entrypoints: one perception stack, independently selectable controllers."""

import math

from pathlab.sdk import Action, AlgorithmOutput
from .control import MotionEstimate, Predictive, Pursuit
from .vision import TargetTracker


class TemporalPursuit:
    controller_type = Pursuit

    def initialize(self, config, public_context):
        self.config = config
        self.limits = public_context.get("vehicle_limits")
        if not self.limits:
            self.limits = dict(
                wheelbase_m=0.32,
                max_speed_mps=1.5,
                max_steering_rad=0.52,
                acceleration_mps2=0.8,
                braking_mps2=1.8,
                steering_rate_rad_s=1.2,
            )

    def reset(self, initial_observation, task_hint):
        self.tracker = TargetTracker(
            temporal=self.config.get("temporal", True),
            topology=self.config.get("topology", True),
            association_gate=float(self.config.get("association_gate_m", 0.16)),
            memory_s=float(self.config.get("memory_s", 0.45)),
        )
        self.motion = MotionEstimate(self.limits)
        self.controller = self.controller_type(
            self.limits, float(self.config.get("speed_mps", 0.85))
        )
        self.last_time = initial_observation.timestamp_s
        self.last_action = Action(steering_angle_rad=0, speed_mps=0)
        self.initial = True

    def step(self, observation):
        elapsed = observation.timestamp_s - self.last_time
        if elapsed < -1e-8:
            return AlgorithmOutput(
                status="ERROR", diagnostics=["时间倒退，请重置算法实例"]
            )
        if not self.initial and elapsed:
            translation, yaw = self.motion.advance(
                self.last_action, elapsed, observation.dt_s
            )
            self.tracker.advance(translation, yaw)
        self.initial, self.last_time = False, observation.timestamp_s
        track = self.tracker.observe(observation, max(elapsed, observation.dt_s))
        action = Action(steering_angle_rad=0, speed_mps=0)
        if track.path is not None:
            action = self.controller.command(track.path, track.confidence, self.motion)
            if track.predicted:
                action.speed_mps = min(action.speed_mps, 0.35)
        self.last_action = action
        path = track.path
        tangent = path[min(6, len(path) - 1)] - path[0] if path is not None else None
        return AlgorithmOutput(
            status=track.status,
            confidence=track.confidence,
            action=action,
            centerline_px=self.tracker.camera.pixels(path).tolist()
            if path is not None
            else None,
            local_path_m=path.tolist() if path is not None else None,
            candidates_px=track.candidates,
            heading_error_rad=float(math.atan2(tangent[1], tangent[0]))
            if tangent is not None
            else None,
            curvature_per_m=math.tan(action.steering_angle_rad)
            / self.limits["wheelbase_m"],
            debug={
                "identity_initialized": self.tracker.initialized,
                "prediction_only": track.predicted,
                "missing_s": self.tracker.missing_s,
                "observed_points": len(path) if path is not None else 0,
                "motion_source": "previous_command_model",
                "motion_model": self.limits.get("motion_model", "kinematic_v1"),
                "estimated_speed_mps": self.motion.speed,
                "estimated_lateral_speed_mps": float(self.motion.state[4]),
            },
            diagnostics=[track.reason],
        )

    def close(self):
        pass


class TemporalMPC(TemporalPursuit):
    controller_type = Predictive
