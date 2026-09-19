"""Platform probes only. Deliberately not presented as line-following algorithms."""

import cv2
import numpy as np

from pathlab.sdk import Action, AlgorithmOutput


class Stop:
    def initialize(self, config, public_context):
        self.config = config

    def reset(self, initial_observation, task_hint):
        self.frames = 0

    def step(self, observation):
        self.frames += 1
        return AlgorithmOutput(
            status="UNINITIALIZED",
            action=Action(steering_angle_rad=0, speed_mps=0),
            diagnostics=["停车探针，不执行目标识别"],
            debug={"frames_seen": self.frames},
        )

    def close(self):
        pass


class Constant(Stop):
    def step(self, observation):
        self.frames += 1
        return AlgorithmOutput(
            status="ACQUIRE",
            action=Action(
                steering_angle_rad=self.config.get("steering_angle_rad", 0),
                speed_mps=self.config.get("speed_mps", 0.45),
            ),
            diagnostics=["固定动作：未使用地图或图像决策，不代表寻迹能力"],
            debug={"frames_seen": self.frames},
        )


class ImageProbe(Stop):
    def step(self, observation):
        self.frames += 1
        rgb = observation.rgb()
        gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
        mask = (gray < float(self.config.get("threshold", 100))).astype(np.uint8)
        mask[: round(rgb.shape[0] * 0.12)] = 0
        count, labels, stats, _ = cv2.connectedComponentsWithStats(mask)
        candidates = []
        for index in sorted(
            range(1, count), key=lambda i: stats[i, cv2.CC_STAT_AREA], reverse=True
        )[:12]:
            if stats[index, cv2.CC_STAT_AREA] < 30:
                continue
            points = []
            for y in range(rgb.shape[0] - 1, 0, -6):
                xs = np.flatnonzero(labels[y] == index)
                if len(xs):
                    points.append((float(np.median(xs)), float(y)))
            if points:
                candidates.append(points)
        # Multiple visible components do not establish physical line identity.
        status = (
            "AMBIGUOUS" if len(candidates) > 1 else "ACQUIRE" if candidates else "LOST"
        )
        return AlgorithmOutput(
            status=status,
            candidates_px=candidates,
            debug={
                "frames_seen": self.frames,
                "dark_pixels": int(mask.sum()),
                "visible_components": len(candidates),
            },
            diagnostics=["仅显示当前帧候选；没有目标关联、米制路径或动作输出"],
        )
