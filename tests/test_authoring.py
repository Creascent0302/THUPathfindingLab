"""Authoring boundaries and real uploaded-code execution, not UI-only mocks."""

import io
import json
import math
import stat
import zipfile

import numpy as np
import pytest
from fastapi.testclient import TestClient

from pathlab.api import create_app
from pathlab.config import MapDesign, Scene, VehicleConfig
from pathlab.map_editor import MapRequest, build_scene, geometry_summary, rounded_path
from pathlab.registry import registry
from pathlab.scenarios import generate, validate_scene
from pathlab.simulation import Renderer
from pathlab.submissions import import_submission, template_zip
from .conftest import wait_until
from .test_api import run_complete


@pytest.fixture
def client(tmp_path):
    with TestClient(create_app(tmp_path)) as http:
        yield http


def archive(files: dict[str, str | bytes]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zipped:
        for name, content in files.items():
            zipped.writestr(name, content)
    return buffer.getvalue()


def test_delete_finished_record_and_active_guard(client):
    active = client.post("/api/runs", json={"algorithm": "manual"}).json()["id"]
    assert client.delete(f"/api/results/{active}").status_code == 409
    run_id = run_complete(
        client,
        {"algorithm": "stop", "max_steps": 1, "realtime": False, "record_images": True},
    )
    wait_until(lambda: not client.app.state.manager.runs[run_id].thread.is_alive())
    folder = client.app.state.manager.root / "runs" / run_id
    assert (folder / "images").is_dir()
    assert client.delete(f"/api/results/{run_id}").json() == {"deleted": run_id}
    assert not folder.exists()
    for suffix in ("", "/frames/0", "/export/json"):
        assert client.get(f"/api/results/{run_id}{suffix}").status_code == 404
    assert client.get(f"/api/runs/{run_id}").status_code == 404
    assert client.delete(f"/api/results/{run_id}").status_code == 404
    assert all(r["episode_id"] != run_id for r in client.get("/api/results").json())


def test_upload_template_real_execution_and_restart(tmp_path):
    with TestClient(create_app(tmp_path)) as http:
        raw = http.get("/api/submissions/template").content
        result = http.post(
            "/api/submissions",
            files={"file": ("算法.zip", raw)},
            data={"name": "第 1 组", "capability": "action"},
        )
        assert result.status_code == 201, result.text
        spec = result.json()
        assert len(spec["submission_sha256"]) == 64
        run_id = run_complete(
            http, {"algorithm": spec["id"], "max_steps": 2, "realtime": False}
        )
        record = http.get(f"/api/results/{run_id}").json()
        assert not record["manifest"]["failures"]
        assert [r["output"]["debug"]["frames_seen"] for r in record["frames"]] == [1, 2]
        assert (
            record["manifest"]["algorithm"]["submission_sha256"]
            == spec["submission_sha256"]
        )
    with TestClient(create_app(tmp_path)) as http:
        assert spec["id"] in {
            s["id"] for s in http.get("/api/catalog").json()["algorithms"]
        }
        run_complete(http, {"algorithm": spec["id"], "max_steps": 1, "realtime": False})


def test_upload_helpers_resources_and_no_server_import(client, tmp_path):
    marker = tmp_path / "executed.txt"
    code = f"""from pathlib import Path
from helper import value
Path({str(marker)!r}).write_text("worker")
class StudentAlgorithm:
    def initialize(self, config, public_context): pass
    def reset(self, observation, hint): pass
    def step(self, observation):
        return {{"status": "TRACK", "action": {{"speed_mps": value, "steering_angle_rad": 0}}, "debug": {{"asset": Path("data.txt").read_text()}}}}
    def close(self): pass
"""
    raw = archive(
        {
            "team/algorithm.py": code,
            "team/helper.py": "value = 0.2",
            "team/data.txt": "resource",
        }
    )
    response = client.post("/api/submissions", files={"file": ("team.zip", raw)})
    assert response.status_code == 201, response.text
    assert not marker.exists()  # AST checks cannot execute import-time code.
    run_id = run_complete(
        client, {"algorithm": response.json()["id"], "max_steps": 1, "realtime": False}
    )
    assert marker.read_text() == "worker"
    result = client.get(f"/api/results/{run_id}").json()
    assert not result["manifest"]["failures"], result["manifest"]["failures"]
    row = result["frames"][0]
    assert row["output"]["debug"]["asset"] == "resource"
    assert row["output"]["action"]["speed_mps"] == 0.2


@pytest.mark.parametrize(
    "files",
    [
        {"../escape.py": "pass"},
        {"/absolute.py": "pass"},
        {"C:\\escape.py": "pass"},
        {"algorithm.py": "class StudentAlgorithm(:"},
        {"algorithm.py": "class Wrong: pass"},
        {
            "a/algorithm.py": "class StudentAlgorithm: pass",
            "b/algorithm.py": "class StudentAlgorithm: pass",
        },
    ],
)
def test_invalid_archives_leave_no_install(tmp_path, files):
    with pytest.raises(ValueError):
        import_submission(tmp_path, archive(files), "bad", "action")
    assert not list((tmp_path / "submissions").iterdir())


def test_zip_symlink_duplicate_and_size_limits(tmp_path):
    for kind in ("symlink", "oversize"):
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zipped:
            info = zipfile.ZipInfo("algorithm.py")
            if kind == "symlink":
                info.external_attr = (stat.S_IFLNK | 0o777) << 16
                zipped.writestr(info, "/etc/passwd")
            else:
                zipped.writestr("large.bin", b"0" * (33 * 1024**2))
        with pytest.raises(ValueError):
            import_submission(tmp_path, buffer.getvalue(), "bad", "action")
    with pytest.raises(ValueError, match="重复"):
        import_submission(
            tmp_path,
            archive({"algorithm.py": "pass", "ALGORITHM.py": "pass"}),
            "bad",
            "action",
        )
    with pytest.raises(ValueError):
        import_submission(tmp_path, b"not zip", "bad", "action")


def test_uploaded_registry_isolated_per_artifact_root(tmp_path):
    spec = import_submission(tmp_path / "a", template_zip(), "A", "action")
    assert spec.id in registry(artifact_root=tmp_path / "a")
    assert spec.id not in registry(artifact_root=tmp_path / "b")


def test_staging_upload_is_not_discoverable(tmp_path):
    spec = import_submission(tmp_path, template_zip(), "A", "action")
    folder = tmp_path / "submissions" / spec.id
    folder.rename(folder.with_name(".upload-incomplete"))
    assert spec.id not in registry(artifact_root=tmp_path)


@pytest.mark.parametrize("radius", [0.58, 1, 2])
def test_editor_curvature_and_start_visibility(radius):
    scene = build_scene(
        MapRequest(
            design=MapDesign(
                waypoints=[(0, 0), (7, 0), (7, 7), (0, 7)], radius_m=radius
            )
        )
    )
    assert validate_scene(scene) == []
    summary = geometry_summary(scene)
    assert summary["minimum_path_radius_m"] == pytest.approx(radius, rel=0.001)
    assert summary["minimum_path_radius_m"] >= summary["minimum_vehicle_radius_m"]
    assert scene.design.radius_m == radius


@pytest.mark.parametrize(
    "points,radius,message",
    [
        ([(0, 0), (3, 0), (3, 3)], 0.2, "圆角半径"),
        ([(0, 0), (0.3, 0), (0.3, 0.3)], 1, "长度不足"),
        ([(0, 0), (5, 0), (0, 0)], 1, "折返"),
        ([(0, 0), (0, 0), (2, 0)], 1, "相邻控制点"),
        ([(0, 0), (40, 0)], 1, "范围"),
        ([(0, 0), (8, 0), (8, 6), (4, 6), (4, -4)], 1, "交叉"),
    ],
)
def test_editor_rejects_bad_geometry(points, radius, message):
    with pytest.raises(ValueError, match=message):
        build_scene(MapRequest(design=MapDesign(waypoints=points, radius_m=radius)))


def test_editor_vehicle_constraint_reacts_to_wheelbase():
    design = MapDesign(waypoints=[(0, 0), (5, 0), (5, 5)], radius_m=1)
    rounded_path(design, VehicleConfig())
    with pytest.raises(ValueError, match="圆角半径"):
        rounded_path(design, VehicleConfig(wheelbase_m=1))


def test_maps_save_load_delete_and_run(client):
    request = {
        "name": "自定义 S",
        "design": {"waypoints": [[0, 0], [5, 0], [5, 4], [10, 4]], "radius_m": 1},
    }
    response = client.post("/api/maps/build", json=request)
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["image"] and data["geometry"]["length_m"] > 10
    saved = client.post("/api/maps", json=data["scene"])
    assert saved.status_code == 201
    identifier = saved.json()["id"]
    loaded = client.get("/api/maps").json()[0]["scene"]
    assert loaded == data["scene"]
    run_id = run_complete(
        client,
        {"algorithm": "stop", "scene": loaded, "max_steps": 1, "realtime": False},
    )
    assert client.delete(f"/api/maps/{identifier}").status_code == 200
    assert client.get("/api/maps").json() == []
    assert (
        client.get(f"/api/results/{run_id}/frames/0").json()["image"] == data["image"]
    )


def test_repeated_has_more_turns_and_texture_is_versioned():
    scene = generate("repeated")
    delta = np.diff(scene.target_path, axis=0)
    heading = np.unwrap(np.arctan2(delta[:, 1], delta[:, 0]))
    assert np.abs(np.diff(heading)).sum() > 4 * math.pi
    scene = generate("straight")
    new = Renderer(scene).render(scene.initial_pose, 0)
    legacy = scene.model_copy(update={"render_version": "1"})
    old = Renderer(legacy).render(scene.initial_pose, 0)
    assert np.abs(new.astype(float) - old).mean() > 0.1
    raw = json.loads(legacy.model_dump_json())
    raw.pop("render_version")
    assert Scene.model_validate(raw).render_version == "1"
