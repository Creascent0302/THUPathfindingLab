"""The shipped framework starts empty and accepts a student's own template."""

from fastapi.testclient import TestClient

from pathlab.api import create_app
from pathlab.registry import PluginSpec, registry
from pathlab.submissions import template_zip
from .test_api import run_complete


def test_fresh_install_has_only_manual_and_upload_works(tmp_path):
    assert registry(artifact_root=tmp_path) == {}
    with TestClient(create_app(tmp_path)) as client:
        assert [p["id"] for p in client.get("/api/catalog").json()["algorithms"]] == [
            "manual"
        ]
        assert client.get("/api/hosting").status_code == 404
        assert client.get("/api/workspace").status_code == 404
        response = client.post(
            "/api/submissions", files={"file": ("template.zip", template_zip())}
        )
        assert response.status_code == 201, response.text
        identifier = response.json()["id"]
        run_id = run_complete(
            client, {"algorithm": identifier, "max_steps": 2, "realtime": False}
        )
        record = client.get(f"/api/results/{run_id}").json()
        assert not record["manifest"]["failures"]
        assert len(record["frames"]) == 2
        assert all(
            frame["applied"]["actual"]["speed_mps"] == 0 for frame in record["frames"]
        )
    assert list(registry(artifact_root=tmp_path)) == [identifier]


def test_native_worker_uses_executable_dispatch(monkeypatch):
    monkeypatch.setattr("pathlab.registry.FROZEN", True)
    spec = PluginSpec(
        id="student",
        name="student",
        version="1",
        capabilities=["action"],
        entrypoint="algorithm:StudentAlgorithm",
    )
    assert spec.argv()[1:] == ["--worker", "algorithm:StudentAlgorithm"]


def test_upload_still_runs_after_moving_data_directory(tmp_path):
    import shutil
    from pathlab.submissions import import_submission

    original, moved = tmp_path / "original", tmp_path / "moved"
    spec = import_submission(original, template_zip(), "portable", "action")
    shutil.move(original, moved)
    restored = registry(artifact_root=moved)[spec.id]
    assert restored.working_directory.startswith(str(moved))
    with TestClient(create_app(moved)) as client:
        run_id = run_complete(
            client, {"algorithm": spec.id, "max_steps": 1, "realtime": False}
        )
        assert not client.get(f"/api/results/{run_id}").json()["manifest"]["failures"]
