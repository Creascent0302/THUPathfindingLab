"""Opt-in avoidance variants. The original temporal algorithms remain line followers."""

import math

from pathlab.sdk import Action
from .modular.algorithm import VisualDriver
from .modular.control import Predictive
from .modular.obstacles import AvoidanceTracker, DetourPlanner


class AvoidingPursuit(VisualDriver):
    tracker_type = AvoidanceTracker

    def reset(self, observation, hint):
        super().reset(observation, hint)
        self.tracker.planner = DetourPlanner(self.limits)
        self.detour_controller = self.controller_type(self.limits, speed=0.38)

    def step(self, observation):
        output = super().step(observation)
        if output.status == "ERROR":
            return output
        tracker = self.tracker
        path, avoiding = tracker.planner.command_path(
            output.local_path_m,
            tracker.components,
            tracker.obstacles.items,
            observation.dt_s,
        )
        if avoiding:
            # MPC must predict the speed that will actually be requested.
            self.detour_controller.cruise = 0.25 if tracker.planner.peeking else 0.38
            action = (
                self.detour_controller.command(path, 0.8, self.motion)
                if path is not None
                else Action(steering_angle_rad=0, speed_mps=0)
            )
            output.confidence = 0.7 if path is not None else 0
            output.action = self.last_action = action
            output.status = "TRACK" if path is not None else "LOST"
            output.local_path_m = path.tolist() if path is not None else None
            output.centerline_px = (
                tracker.camera.pixels(path).tolist() if path is not None else None
            )
            output.diagnostics = [tracker.planner.reason]
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
