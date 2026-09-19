"""Test-only plugins. These are deliberately not in the production allowlist."""

import json
import os
import sys
import time

from algorithms.examples import Stop
from pathlab.sdk import Action, AlgorithmOutput


class Fault(Stop):
    def initialize(self, config, public_context):
        super().initialize(config, public_context)
        if config.get("fault") == "initialize":
            raise RuntimeError("intentional initialization failure")
        self.context = public_context

    def step(self, observation):
        mode = self.config.get("fault")
        if mode == "exception":
            raise RuntimeError("intentional inference failure")
        if mode == "crash":
            os._exit(23)
        if mode == "hang":
            while True:
                time.sleep(0.05)
        if mode == "nan":
            return {
                "status": "TRACK",
                "action": {"steering_angle_rad": float("nan"), "speed_mps": 1},
            }
        if mode == "shape":
            return {"status": "TRACK", "local_path_m": [[1, 2, 3], [4, 5, 6]]}
        if mode == "empty":
            return {}
        if mode == "missing_action":
            return AlgorithmOutput(status="TRACK")
        if mode == "bounds":
            return AlgorithmOutput(
                status="TRACK", action=Action(steering_angle_rad=20, speed_mps=50)
            )
        if mode == "inspect":
            self.frames += 1
            return AlgorithmOutput(
                status="ACQUIRE",
                action=Action(steering_angle_rad=0, speed_mps=0),
                debug={
                    "observation_keys": list(observation.model_dump()),
                    "context": self.context,
                    "frames_seen": self.frames,
                    "mean_rgb": observation.rgb().mean(axis=(0, 1)).tolist(),
                },
            )
        return super().step(observation)


if __name__ == "__main__":
    mode = sys.argv[1]
    for line in sys.stdin:
        request = json.loads(line)
        if request["method"] == "step":
            if mode == "garbage":
                print("not json", flush=True)
            elif mode == "oversize":
                sys.stdout.write("x" * (8 * 1024 * 1024 + 1))
                sys.stdout.flush()
            elif mode == "version":
                print(
                    json.dumps(
                        {
                            "protocol_version": "9.0",
                            "id": request["id"],
                            "ok": True,
                            "result": {},
                        }
                    ),
                    flush=True,
                )
        else:
            print(
                json.dumps(
                    {
                        "protocol_version": "1.0",
                        "id": request["id"],
                        "ok": True,
                        "result": None,
                    }
                ),
                flush=True,
            )
