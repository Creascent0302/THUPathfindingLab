"""Implement StudentAlgorithm, zip algorithm.py, and upload in the workbench."""

from pathlab.sdk import Action, AlgorithmOutput, Observation, TaskHint


class StudentAlgorithm:
    def initialize(self, config: dict, public_context: dict) -> None:
        self.config = config

    def reset(self, initial_observation: Observation, task_hint: TaskHint) -> None:
        self.hint = task_hint
        self.frames = 0

    def step(self, observation: Observation) -> AlgorithmOutput:
        rgb = observation.rgb()
        self.frames += 1
        # Replace the safe stop with your own visual logic.
        return AlgorithmOutput(
            status="UNINITIALIZED",
            action=Action(steering_angle_rad=0, speed_mps=0),
            debug={
                "frames_seen": self.frames,
                "mean_rgb": rgb.mean(axis=(0, 1)).tolist(),
            },
            diagnostics=["模板安全停车；请实现视觉决策"],
        )

    def close(self) -> None:
        """Release resources if your implementation allocates them."""
