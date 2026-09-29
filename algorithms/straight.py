"""Interface example: a synthetic straight path, not a vision detector."""

import cv2
import numpy as np

from pathlab.sdk import AlgorithmOutput


class StudentAlgorithm:
    def initialize(self, config, public_context):
        self.vehicle = public_context.get("vehicle_limits")

    def reset(self, initial_observation, task_hint):
        self.hint = task_hint
        self.last_time = None

    def step(self, observation):
        rgb = observation.rgb()  # 输入：uint8 RGB 图像
        gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
        dt = (
            observation.dt_s
            if self.last_time is None
            else observation.timestamp_s - self.last_time
        )
        self.last_time = observation.timestamp_s

        calibration = observation.calibration
        if calibration is None or self.vehicle is None:
            return AlgorithmOutput(
                status="LOST", diagnostics=["请在有标定的仿真场景运行示例"]
            )

        # 演示路径：当前车辆前方 0.4～1.6 m 的直线，y=0。
        # 实际作业需将这里替换为“从图像识别目标线并转换为米制坐标”。
        path = np.array([(x, 0.0) for x in (0.4, 0.7, 1.0, 1.3, 1.6)])

        # 将演示路径投影回原图，便于在算法画面检查坐标。
        homography = np.asarray(calibration.ground_to_image, dtype=float)
        ground = np.column_stack((path, np.ones(len(path))))
        projected = ground @ homography.T
        projected = projected[projected[:, 2] > 1e-6]
        pixels = projected[:, :2] / projected[:, 2:3]
        visible = (
            (pixels[:, 0] >= 0)
            & (pixels[:, 0] < observation.width)
            & (pixels[:, 1] >= 0)
            & (pixels[:, 1] < observation.height)
        )

        return AlgorithmOutput(
            status="TRACK",
            local_path_m=path.tolist(),  # 输出给路径执行器
            centerline_px=pixels[visible].tolist(),  # 输出给画面叠加
            debug={
                "frame_id": observation.frame_id,
                "dt_s": float(dt),
                "gray_mean": float(gray.mean()),
                "wheelbase_m": self.vehicle["wheelbase_m"],
                "hint_kind": self.hint.kind,
            },
        )

    def close(self):
        pass
