"""Real admission/deletion paths with sparse files: no multi-GiB allocation."""

from fastapi.testclient import TestClient
import pytest

from pathlab.api import create_app
from pathlab.storage import RUN_STORAGE_LIMIT_BYTES, directory_bytes
from pathlab.submissions import import_submission, template_zip
from .conftest import wait_until
from .test_api import run_complete


def sparse_file(path, size):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as handle:
        handle.truncate(size)


def test_training_and_reports_do_not_block_runs_uploads_or_saved_maps(tmp_path):
    training = tmp_path / "learning" / "training.npz"
    sparse_file(training, RUN_STORAGE_LIMIT_BYTES + 1)
    sparse_file(tmp_path / "custom-map-regression" / "report.json", 400 * 1024**2)
    with TestClient(create_app(tmp_path)) as client:
        assert client.get("/api/storage").json()["runs"]["used_bytes"] == 0
        scene = client.get("/api/scenes/straight").json()["scene"]
        saved = client.post("/api/maps", json=scene)
        assert saved.status_code == 201
        uploaded = client.post(
            "/api/submissions", files={"file": ("algorithm.zip", template_zip())}
        )
        assert uploaded.status_code == 201, uploaded.text
        run_id = run_complete(
            client,
            {"algorithm": "stop", "max_steps": 1, "realtime": False},
        )
        wait_until(lambda: not client.app.state.manager.runs[run_id].thread.is_alive())
        assert client.delete(f"/api/results/{run_id}").status_code == 200
        assert client.get("/api/storage").json()["runs"]["used_bytes"] == 0
        assert client.get("/api/maps").json()[0]["id"] == saved.json()["id"]
        assert training.stat().st_size == RUN_STORAGE_LIMIT_BYTES + 1


def test_deleting_record_releases_its_quota_and_allows_next_run(tmp_path):
    with TestClient(create_app(tmp_path)) as client:
        run_id = run_complete(
            client, {"algorithm": "stop", "max_steps": 1, "realtime": False}
        )
        wait_until(lambda: not client.app.state.manager.runs[run_id].thread.is_alive())
        sparse_file(
            tmp_path / "runs" / run_id / "images" / "large.png", RUN_STORAGE_LIMIT_BYTES
        )
        usage = client.get("/api/storage").json()["runs"]
        assert usage["used_bytes"] >= usage["limit_bytes"]
        blocked = client.post("/api/runs", json={"algorithm": "manual"})
        assert blocked.status_code == 400
        assert "运行记录" in blocked.json()["detail"]
        # Algorithm submission has an independent budget.
        assert (
            client.post(
                "/api/submissions", files={"file": ("algorithm.zip", template_zip())}
            ).status_code
            == 201
        )
        assert client.delete(f"/api/results/{run_id}").status_code == 200
        assert client.get("/api/storage").json()["runs"]["used_bytes"] == 0
        run_complete(client, {"algorithm": "stop", "max_steps": 1, "realtime": False})


def test_submission_quota_counts_incoming_expanded_data(tmp_path):
    sparse_file(
        tmp_path / "submissions" / "existing" / "weights.pt",
        RUN_STORAGE_LIMIT_BYTES - 1,
    )
    with pytest.raises(ValueError, match="artifacts/submissions"):
        import_submission(tmp_path, template_zip(), "test", "action")
    assert not list((tmp_path / "submissions").glob(".upload-*"))
    with TestClient(create_app(tmp_path)) as client:
        run_complete(client, {"algorithm": "stop", "max_steps": 1, "realtime": False})


def test_directory_usage_ignores_links_and_missing_directories(tmp_path):
    sparse_file(tmp_path / "training.npz", RUN_STORAGE_LIMIT_BYTES)
    records = tmp_path / "runs"
    records.mkdir()
    (records / "external").symlink_to(tmp_path / "training.npz")
    (records / "loop").symlink_to(tmp_path, target_is_directory=True)
    (records / "broken").symlink_to(tmp_path / "missing")
    (records / "frames.jsonl").write_bytes(b"{}\n")
    assert directory_bytes(records) == 3
    assert directory_bytes(tmp_path / "missing") == 0
