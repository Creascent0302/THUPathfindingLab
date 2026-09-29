"""Exercise the real standalone executable without source imports or user data."""

from contextlib import contextmanager
import io
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
import zipfile

import httpx
from websockets.sync.client import connect


def until(predicate, timeout=30):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        result = predicate()
        if result:
            return result
        time.sleep(0.08)
    raise AssertionError("发行包验收等待超时")


@contextmanager
def server(executable, folder):
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    environment = os.environ.copy()
    for name in ("PYTHONPATH", "PYTHONHOME", "VIRTUAL_ENV"):
        environment.pop(name, None)
    with (folder / "server.log").open("w", encoding="utf-8") as log:
        process = subprocess.Popen(
            [
                str(executable),
                "serve",
                "--lan",
                "--port",
                str(port),
                "--data-dir",
                str(folder / "data"),
            ],
            cwd=folder,
            env=environment,
            stdout=log,
            stderr=log,
        )
        try:
            with httpx.Client(
                base_url=f"http://127.0.0.1:{port}", timeout=30, trust_env=False
            ) as client:

                def ready():
                    if process.poll() is not None:
                        raise AssertionError(
                            (folder / "server.log").read_text(encoding="utf-8")
                        )
                    try:
                        return client.get("/api/health").is_success
                    except httpx.ConnectError:
                        return False

                until(ready)
                yield client
        finally:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()


def checked(response, status=200):
    assert response.status_code == status, response.text
    return response.json()


def submission():
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr(
            "algorithm.py",
            """from pathlab.sdk import Action, AlgorithmOutput
from helper import value
import cv2
import numpy as np

class StudentAlgorithm:
    def initialize(self, config, public_context):
        self.count = 0
    def reset(self, initial_observation, task_hint):
        self.count = 0
    def step(self, observation):
        self.count += 1
        gray = cv2.cvtColor(observation.rgb(), cv2.COLOR_RGB2GRAY)
        return AlgorithmOutput(status="ACQUIRE",
            action=Action(steering_angle_rad=0, speed_mps=0.25),
            debug={"frames": self.count, "resource": value(), "mean": float(np.mean(gray))})
    def close(self):
        pass
""",
        )
        archive.writestr(
            "helper.py",
            'import json\nfrom pathlib import Path\ndef value():\n    return json.loads(Path("resource.json").read_text())["value"]\n',
        )
        archive.writestr("resource.json", '{"value": 42}')
    return buffer.getvalue()


def main(executable):
    with tempfile.TemporaryDirectory(prefix="pathlab-release-") as directory:
        folder = Path(directory)
        with server(executable, folder) as client:
            assert client.get("/").is_success
            catalog = checked(client.get("/api/catalog"))
            assert [item["id"] for item in catalog["algorithms"]] == [
                "manual",
                "straight_path",
                "temporal_path",
            ]
            assert len(catalog["families"]) == 12
            template = client.get("/api/submissions/template")
            assert template.is_success
            with zipfile.ZipFile(io.BytesIO(template.content)) as archive:
                assert "algorithm.py" in archive.namelist()
            scene = checked(client.get("/api/scenes/straight"))["scene"]
            assert scene["start_mode"] == "on_path" and not scene["objects"]
            for algorithm, family in [
                ("straight_path", "straight"),
                ("temporal_path", "sharp"),
            ]:
                demo = checked(
                    client.post(
                        "/api/runs",
                        json={
                            "algorithm": algorithm,
                            "execution": "path",
                            "family": family,
                            "max_steps": 1500,
                            "realtime": False,
                        },
                    ),
                    201,
                )["id"]
                checked(
                    client.post(f"/api/runs/{demo}/control", json={"command": "resume"})
                )
                until(
                    lambda: checked(client.get(f"/api/runs/{demo}"))["state"]
                    in {"completed", "failed"},
                    timeout=90,
                )
                record = checked(client.get(f"/api/results/{demo}"))
                assert record["manifest"]["metrics"]["success"], record["manifest"]
                assert all(
                    frame["output"] is None or frame["output"]["action"] is None
                    for frame in record["frames"]
                )
            first = checked(client.post("/api/maps", json=scene), 201)
            second = checked(client.post("/api/maps", json=scene), 201)
            assert second["scene"]["name"] == first["scene"]["name"] + "(1)"
            methods = [
                checked(
                    client.post(
                        "/api/submissions",
                        files={"file": ("student.zip", submission())},
                        data={"name": name, "capability": "action"},
                    ),
                    201,
                )["id"]
                for name in ["学生版本 A", "学生版本 B"]
            ]
            run = checked(
                client.post(
                    "/api/runs",
                    json={"algorithm": methods[0], "max_steps": 3, "realtime": False},
                ),
                201,
            )
            identifier = run["id"]
            until(
                lambda: checked(client.get(f"/api/runs/{identifier}"))["state"]
                in {"running", "failed"}
            )
            with connect(
                str(client.base_url).replace("http://", "ws://")
                + f"/api/runs/{identifier}/stream",
                proxy=None,
            ) as ws:
                ws.send("snapshot")
                assert json.loads(ws.recv())["id"] == identifier
            checked(
                client.post(
                    f"/api/runs/{identifier}/control", json={"command": "resume"}
                )
            )
            result = until(
                lambda: (r if r["manifest"]["metrics"] is not None else None)
                if (r := checked(client.get(f"/api/results/{identifier}")))
                else None
            )
            assert not result["manifest"]["failures"], result["manifest"]
            task_frames = [frame for frame in result["frames"] if frame["output"]]
            assert [frame["output"]["debug"]["frames"] for frame in task_frames] == [
                1,
                2,
                3,
            ]
            assert all(
                frame["output"]["debug"]["resource"] == 42 for frame in task_frames
            )
            assert checked(client.get(f"/api/results/{identifier}/frames/0"))["image"]
            batch = checked(
                client.post(
                    "/api/benchmarks",
                    json={
                        "algorithms": [{"algorithm": name} for name in methods],
                        "families": ["straight"],
                        "seeds": [19],
                        "max_steps": 2,
                    },
                ),
                201,
            )
            batch = until(
                lambda: b
                if (b := checked(client.get(f"/api/benchmarks/{batch['id']}")))["state"]
                == "completed"
                else None
            )
            assert batch["summary"]["comparable"], batch
            assert all(not item.get("error") for item in batch["items"]), batch
            assert len(batch["implementation_versions"]) >= 18
            assert client.get(f"/api/results/{identifier}/export/csv").is_success
            checked(client.delete(f"/api/results/{identifier}"))
            assert client.get(f"/api/results/{identifier}").status_code == 404
        # Restart verifies actual disk persistence, independent of browser storage.
        with server(executable, folder) as client:
            assert len(checked(client.get("/api/maps"))) == 2
            assert len(checked(client.get("/api/catalog"))["algorithms"]) == 5
            assert (
                checked(client.get(f"/api/benchmarks/{batch['id']}"))["state"]
                == "completed"
            )
        print(
            "发行包验收通过：两种轨迹示例、地图与重名、ZIP/辅助模块/资源、Worker、WebSocket、回放、批量评分、删除和重启持久化。"
        )


if __name__ == "__main__":
    target = Path(sys.argv[1]).resolve()
    if target.suffix == ".zip":
        with tempfile.TemporaryDirectory(prefix="pathlab-unpacked-") as temporary:
            with zipfile.ZipFile(target) as archive:
                archive.extractall(temporary)
            executable = next(
                Path(temporary).glob(
                    "*/PathLab.exe" if os.name == "nt" else "*/PathLab"
                )
            )
            executable.chmod(executable.stat().st_mode | 0o111)
            main(executable)
    else:
        main(target)
