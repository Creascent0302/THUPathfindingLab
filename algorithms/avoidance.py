"""Opt-in avoidance variants. The original temporal algorithms remain line followers."""

import math
import numpy as np

from pathlab.sdk import Action
from .modular.algorithm import VisualDriver
from .modular.control import Predictive, Pursuit
from .modular.obstacles import AvoidanceTracker, DetourPlanner
from .modular.recovery import ReverseRecovery


class AvoidingPursuit(VisualDriver):
    tracker_type = AvoidanceTracker

    def reset(self, observation, hint):
        super().reset(observation, hint)
        self.tracker.planner = DetourPlanner(self.limits)
        self.tracker.recovery = ReverseRecovery(self.limits)
        self.detour_controller = self.controller_type(
            self.limits, speed=0.28, lookahead_m=0.34
        )

    def step(self, observation):
        elapsed = max(observation.dt_s, observation.timestamp_s - self.last_time)
        output = super().step(observation)
        if output.status == "ERROR":
            return output
        tracker = self.tracker
        recovery = tracker.recovery
        path, avoiding = (
            (None, True)
            if recovery.active
            else tracker.planner.command_path(
                output.local_path_m
                if output.local_path_m is not None
                else tracker.path,
                tracker.components,
                tracker.obstacles.items,
                elapsed,
            )
        )
        if (
            avoiding
            and path is None
            and not recovery.active
            and not tracker.planner.visibility_exhausted
            and not tracker.planner.predicted_route
        ):
            recovery.request(tracker, self.motion, elapsed)
        elif not recovery.active:
            recovery.wait_s = 0
        recovering = recovery.active
        override = (
            recovery.command(tracker, self.motion, elapsed) if recovering else None
        )
        if avoiding:
            # MPC must predict the speed that will actually be requested.
            self.detour_controller.cruise = 0.25 if tracker.planner.peeking else 0.28
            control_path = path
            if (
                path is not None
                and (tracker.planner.peeking or tracker.planner.continuing)
                and self.controller_type is Pursuit
                and len(path) >= 3
            ):
                # A finite side-view path has a meaningful terminal heading.
                # Extend ONLY the controller's lookahead along that tangent;
                # the planner still stops at the verified path endpoint.
                tangent = path[-1] - path[-3]
                tangent /= max(float(np.linalg.norm(tangent)), 1e-8)
                tail = path[-1] + np.arange(0.05, 0.71, 0.05)[:, None] * tangent
                control_path = np.vstack([path, tail])
            action = (
                self.detour_controller.command(control_path, 0.8, self.motion)
                if path is not None
                else Action(steering_angle_rad=0, speed_mps=0)
            )
            if override is not None:
                action = override
            if tracker.planner.visibility_exhausted:
                action = Action(steering_angle_rad=self.motion.steering, speed_mps=0)
            output.confidence = 0.7 if path is not None else 0
            output.action = self.last_action = action
            output.status = "TRACK" if path is not None or recovering else "LOST"
            output.local_path_m = path.tolist() if path is not None else None
            output.centerline_px = (
                tracker.camera.pixels(path).tolist() if path is not None else None
            )
            output.diagnostics = [tracker.planner.reason]
            if recovering or recovery.stage == "failed":
                output.diagnostics.append(recovery.reason)
            output.curvature_per_m = (
                math.tan(action.steering_angle_rad) / self.limits["wheelbase_m"]
            )
            tangent = (
                path[min(6, len(path) - 1)] - path[0] if path is not None else None
            )
            output.heading_error_rad = (
                math.atan2(tangent[1], tangent[0]) if tangent is not None else None
            )
        output.debug.update(
            avoidance_active=avoiding,
            avoidance_state=tracker.planner.reason,
            recovery_stage=recovery.stage,
            recovery_reason=recovery.reason,
            reverse_target_m=recovery.target_distance,
            reverse_recoveries=recovery.completed,
            detour_handoffs=tracker.planner.handoffs,
            planned_obstacles=tracker.planner.planned_obstacles,
            detour_continuing=tracker.planner.continuing,
            route_unseen_s=tracker.planner.route_unseen_s,
            route_unseen_m=tracker.planner.route_unseen_m,
            route_prediction=tracker.planner.predicted_route,
            prediction_available=tracker.planner.forecast.trustworthy,
            prediction_rejection=tracker.planner.prediction_rejection,
            prediction_age_s=tracker.planner.forecast.age,
            prediction_curvature=tracker.planner.forecast.curvature,
            prediction_error_2m=tracker.planner.forecast.uncertainty(2.0),
            planning_rejections=tracker.planner.rejections,
            observed_obstacles=[
                {
                    "center_m": item.center.tolist(),
                    "radius_m": item.radius,
                    "age_s": item.age,
                }
                for item in tracker.obstacles.items
            ],
            obstacle_source="rgb_ground_contact_and_command_memory",
        )
        return output


class AvoidingMPC(AvoidingPursuit):
    controller_type = Predictive
