import base64
import json

import cv2
from fastapi.testclient import TestClient
import numpy as np
import pytest

from pathlab.api import create_app
from .conftest import wait_until


@pytest.fixture
def client(tmp_path):
    with TestClient(create_app(tmp_path)) as http:
        yield http


def image_bytes(color=(225, 30, 12)):
    rgb = np.full((64, 96, 3), color, np.uint8)
    ok, raw = cv2.imencode(".png", cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR))
    assert ok
    return raw.tobytes()


def run_complete(client, config):
    response = client.post("/api/runs", json=config)
    assert response.status_code == 201, response.text
    run_id = response.json()["id"]
    assert (
        client.post(
            f"/api/runs/{run_id}/control", json={"command": "resume"}
        ).status_code
        == 200
    )
    wait_until(
        lambda: client.get(f"/api/runs/{run_id}").json()["state"]
        in {"completed", "failed"}
    )
    wait_until(
        lambda: client.get(f"/api/results/{run_id}").json()["manifest"]["metrics"]
        is not None
    )
    return run_id


def test_api_simulation_export_and_reconstruction(client):
    assert client.get("/api/health").json()["status"] == "ok"
    assert len(client.get("/api/catalog").json()["families"]) == 8
    preview = client.get("/api/scenes/straight?seed=7").json()
    assert preview["image"]
    run_id = run_complete(
        client, {"algorithm": "constant", "max_steps": 5, "realtime": False}
    )
    result = client.get(f"/api/results/{run_id}").json()
    assert result["manifest"]["metrics"]["task_frames"] == 5
    assert len(result["frames"]) >= 5
    assert result["frames"][-1]["applied"]["actual"]["speed_mps"] == 0
    assert result["manifest"]["environment"]["python"]
    frame = client.get(f"/api/results/{run_id}/frames/0").json()
    assert frame["image"] == preview["image"]
    assert frame["frame"]["output"]["debug"]["frames_seen"] == 1
    assert client.get(f"/api/results/{run_id}/frames/99").status_code == 404
    exported = client.get(f"/api/results/{run_id}/export/json").json()
    assert exported == result
    csv = client.get(f"/api/results/{run_id}/export/csv").text
    assert "steering_angle_rad" in csv and "confidence" in csv
    assert client.get("/api/results").json()[0]["episode_id"] == run_id


def test_single_image_no_fabricated_truth(client):
    source = client.post(
        "/api/sources", files=[("files", ("red.png", image_bytes(), "image/png"))]
    ).json()
    run_id = run_complete(
        client,
        {
            "mode": "image",
            "algorithm": "image_probe",
            "execution": "perception",
            "source_id": source["id"],
        },
    )
    result = client.get(f"/api/results/{run_id}").json()
    assert len(result["frames"]) == 1
    assert result["manifest"]["metrics"]["success"] is None
    assert result["manifest"]["metrics"]["completion"] is None
    assert result["frames"][0]["evaluation"] is None
    assert result["frames"][0]["applied"] is None
    assert (
        client.get(f"/api/results/{run_id}/frames/0").json()["image"]
        == base64.b64encode(image_bytes()).decode()
    )


def test_sequence_natural_order_state_and_replay_seek(client):
    source = client.post(
        "/api/sources",
        files=[
            ("files", (name, image_bytes(), "image/png"))
            for name in ["frame10.png", "frame2.png", "frame1.png"]
        ],
        data={"fps": "10"},
    ).json()
    assert [f["name"] for f in source["frames"]] == [
        "frame1.png",
        "frame2.png",
        "frame10.png",
    ]
    run_id = run_complete(
        client,
        {
            "mode": "sequence",
            "algorithm": "image_probe",
            "execution": "perception",
            "source_id": source["id"],
            "realtime": False,
        },
    )
    result = client.get(f"/api/results/{run_id}").json()
    assert [f["output"]["debug"]["frames_seen"] for f in result["frames"]] == [1, 2, 3]
    for index in [2, 0, 1, 0]:
        frame = client.get(f"/api/results/{run_id}/frames/{index}").json()["frame"]
        assert frame["output"]["debug"]["frames_seen"] == index + 1
        assert frame["observation_timestamp_s"] == index / 10


def test_video_import_and_run(client, tmp_path):
    path = tmp_path / "clip.avi"
    writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"MJPG"), 10, (96, 64))
    assert writer.isOpened()
    for i in range(4):
        writer.write(np.full((64, 96, 3), (i * 50, 200, 150), np.uint8))
    writer.release()
    response = client.post(
        "/api/sources", files={"files": ("clip.avi", path.read_bytes(), "video/avi")}
    )
    assert response.status_code == 200, response.text
    assert response.json()["frame_count"] == 4
    run_id = run_complete(
        client,
        {
            "mode": "sequence",
            "algorithm": "image_probe",
            "execution": "perception",
            "source_id": response.json()["id"],
            "realtime": False,
        },
    )
    assert (
        client.get(f"/api/results/{run_id}").json()["manifest"]["metrics"]["frames"]
        == 4
    )


def test_invalid_sources_and_run_config(client):
    assert (
        client.post(
            "/api/sources", files={"files": ("broken.png", b"bad", "image/png")}
        ).status_code
        == 400
    )
    assert (
        client.post("/api/runs", json={"algorithm": "unregistered"}).status_code == 400
    )
    assert (
        client.post(
            "/api/runs", json={"algorithm": "stop", "execution": "path"}
        ).status_code
        == 400
    )
    assert (
        client.post(
            "/api/runs", json={"algorithm": "manual", "mode": "image"}
        ).status_code
        == 400
    )
    assert (
        client.post(
            "/api/runs", json={"algorithm": "stop", "mode": "image", "source_id": "bad"}
        ).status_code
        == 400
    )
    assert client.post("/api/runs", json={"max_steps": 1000000}).status_code == 422


def test_websocket_control_and_restart(client):
    response = client.post("/api/runs", json={"algorithm": "manual", "max_steps": 30})
    run_id = response.json()["id"]
    wait_until(lambda: client.get(f"/api/runs/{run_id}").json()["state"] == "running")
    with client.websocket_connect(f"/api/runs/{run_id}/stream") as ws:
        ws.send_text("snapshot")
        assert ws.receive_json()["paused"]
        client.post(
            f"/api/runs/{run_id}/action",
            json={"steering_angle_rad": 0.3, "speed_mps": 0.5},
        )
        client.post(f"/api/runs/{run_id}/control", json={"command": "step"})
        wait_until(lambda: client.get(f"/api/runs/{run_id}").json()["frame_count"] == 1)
        ws.send_text("snapshot")
        data = ws.receive_json()
        assert (
            data["frame"]["pose"]["yaw_rad"] != data["scene"]["initial_pose"]["yaw_rad"]
        )
    client.post(f"/api/runs/{run_id}/control", json={"command": "stop"})
    wait_until(lambda: client.get(f"/api/runs/{run_id}").json()["state"] == "cancelled")
    next_id = run_complete(
        client, {"algorithm": "external_stop", "max_steps": 1, "realtime": False}
    )
    assert next_id != run_id
    assert client.get("/api/health").status_code == 200


def test_running_manifest_recovers_after_server_exit(tmp_path):
    folder = tmp_path / "runs" / ("a" * 32)
    folder.mkdir(parents=True)
    (folder / "manifest.json").write_text(
        json.dumps({"state": "running", "failures": []})
    )
    with TestClient(create_app(tmp_path)) as client:
        assert client.get("/api/results").json()[0]["state"] == "failed"


def test_running_cli_job_is_not_marked_stale(tmp_path):
    import os

    folder = tmp_path / "runs" / ("b" * 32)
    folder.mkdir(parents=True)
    (folder / "manifest.json").write_text(
        json.dumps({"state": "running", "owner_pid": os.getpid(), "failures": []})
    )
    with TestClient(create_app(tmp_path)) as client:
        assert client.get("/api/results").json()[0]["state"] == "running"
