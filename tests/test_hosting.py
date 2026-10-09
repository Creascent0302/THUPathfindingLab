"""Authentication, tenant ownership, concurrent capacity and sandbox boundaries."""

import io
from concurrent.futures import ThreadPoolExecutor
import os
import stat
import subprocess
import time
import zipfile

from fastapi.testclient import TestClient
import pytest
from starlette.websockets import WebSocketDisconnect

from pathlab.accounts import password_matches
from pathlab.hosting import COOKIE, HostingSettings, create_portal
from pathlab.registry import PluginSpec
from pathlab.sandbox import DockerSandbox, DockerWorker
from pathlab.scenarios import generate
from pathlab.worker import WorkerClient
from .conftest import wait_until
from .test_api import image_bytes

ORIGIN = "https://lab.test"
PASSWORD = "classroom-password-2026"
WRITE = {"Origin": ORIGIN, "X-PathLab-Request": "1"}


@pytest.fixture
def portal(tmp_path):
    # Only tests inject the host transport. Public CLI always requires Docker.
    app = create_portal(
        tmp_path, HostingSettings(ORIGIN, total_runs=3), worker_factory=WorkerClient
    )
    for username, role in (
        ("teacher", "admin"),
        ("alice", "student"),
        ("bob", "student"),
    ):
        app.state.accounts.create(username, PASSWORD, role=role)
    with TestClient(app, base_url=ORIGIN) as client:
        yield client, app


def login(client, username="alice"):
    response = client.post(
        "/api/auth/login",
        json={"username": username, "password": PASSWORD},
        headers=WRITE,
    )
    assert response.status_code == 200, response.text
    cookie = response.cookies[COOKIE]
    assert "HttpOnly" in response.headers["set-cookie"]
    assert "Secure" in response.headers["set-cookie"]
    client.cookies.clear()
    return {**WRITE, "Cookie": f"{COOKIE}={cookie}"}


def archive():
    raw = io.BytesIO()
    with zipfile.ZipFile(raw, "w") as bundle:
        bundle.writestr(
            "algorithm.py",
            """from pathlab.sdk import Action, AlgorithmOutput
class StudentAlgorithm:
    def initialize(self, config, public_context): pass
    def reset(self, observation, task_hint): pass
    def step(self, observation):
        return AlgorithmOutput(status='TRACK', confidence=1,
            action=Action(steering_angle_rad=0, speed_mps=0.3))
    def close(self): pass
""",
        )
    return raw.getvalue()


def test_authentication_csrf_and_password_storage(portal):
    client, app = portal
    assert client.get("/api/auth/me").json()["user"] is None
    for path in ("/api/catalog", "/api/maps", "/api/results", "/api/benchmarks"):
        assert client.get(path).status_code == 401
    credentials = {"username": "alice", "password": PASSWORD}
    assert client.post("/api/auth/login", json=credentials).status_code == 403
    assert (
        client.post(
            "/api/auth/login",
            json=credentials,
            headers={**WRITE, "Origin": "https://attacker.test"},
        ).status_code
        == 403
    )
    headers = login(client)
    assert (
        client.get("/api/maps", headers=headers).headers["cache-control"] == "no-store"
    )
    assert client.get("/api/admin/users", headers=headers).status_code == 403
    assert (
        client.get(
            "/api/maps", headers={**headers, "Host": "attacker.test"}
        ).status_code
        == 400
    )
    assert client.post("/api/auth/logout", headers=headers).status_code == 200
    assert client.get("/api/maps", headers=headers).status_code == 401
    with app.state.accounts.connect() as db:
        encoded = db.execute(
            "SELECT password FROM users WHERE username='alice'"
        ).fetchone()[0]
    assert PASSWORD not in encoded and password_matches(PASSWORD, encoded)
    assert len(set(u["id"] for u in app.state.accounts.users())) == 3


def test_users_cannot_read_change_or_execute_each_others_data(portal):
    client, app = portal
    alice, bob = login(client), login(client, "bob")
    scene = generate("straight", 7).model_dump()
    saved = client.post("/api/maps", json=scene, headers=alice).json()
    assert client.get("/api/maps", headers=bob).json() == []
    assert client.delete(f"/api/maps/{saved['id']}", headers=bob).status_code == 404
    upload = client.post(
        "/api/submissions",
        files={"file": ("code.zip", archive())},
        data={"name": "Alice private", "capability": "action"},
        headers=alice,
    )
    assert upload.status_code == 201, upload.text
    algorithm = upload.json()["id"]
    assert algorithm not in {
        a["id"] for a in client.get("/api/catalog", headers=bob).json()["algorithms"]
    }
    assert (
        client.delete(f"/api/submissions/{algorithm}", headers=bob).status_code == 404
    )
    assert (
        client.post("/api/runs", json={"algorithm": algorithm}, headers=bob).status_code
        == 400
    )
    source = client.post(
        "/api/sources", files=[("files", ("image.png", image_bytes()))], headers=alice
    ).json()
    assert (
        client.get(f"/api/sources/{source['id']}/preview", headers=bob).status_code
        == 404
    )
    assert client.delete(f"/api/sources/{source['id']}", headers=bob).status_code == 404
    response = client.post(
        "/api/runs",
        json={"algorithm": algorithm, "max_steps": 2, "realtime": False},
        headers=alice,
    )
    assert response.status_code == 201, response.text
    identifier = response.json()["id"]
    for suffix in ("", "/frames/0", "/export/json"):
        assert (
            client.get(f"/api/results/{identifier}{suffix}", headers=bob).status_code
            == 404
        )
    assert (
        client.post(
            f"/api/runs/{identifier}/control", json={"command": "stop"}, headers=bob
        ).status_code
        == 404
    )
    assert client.delete(f"/api/results/{identifier}", headers=bob).status_code == 404
    assert (
        client.delete(f"/api/submissions/{algorithm}", headers=alice).status_code == 409
    )
    client.post(
        f"/api/runs/{identifier}/control", json={"command": "resume"}, headers=alice
    )
    wait_until(
        lambda: client.get(f"/api/runs/{identifier}", headers=alice).json()["state"]
        == "completed"
    )
    assert (
        client.get(f"/api/results/{identifier}", headers=alice).json()["manifest"][
            "failures"
        ]
        == []
    )
    assert client.get("/api/results", headers=bob).json() == []
    assert (
        client.delete(f"/api/submissions/{algorithm}", headers=alice).status_code == 200
    )
    assert (
        client.delete(f"/api/sources/{source['id']}", headers=alice).status_code == 200
    )


def test_parallel_users_and_global_capacity_release(portal):
    client, app = portal
    alice, bob = login(client), login(client, "bob")
    a = [
        client.post("/api/runs", json={"algorithm": "manual"}, headers=alice)
        for _ in range(2)
    ]
    assert all(response.status_code == 201 for response in a)
    assert client.post("/api/runs", json={}, headers=alice).status_code == 429
    b = client.post("/api/runs", json={}, headers=bob)
    assert b.status_code == 201
    assert client.post("/api/runs", json={}, headers=bob).status_code == 429
    identifier = a[0].json()["id"]
    client.post(
        f"/api/runs/{identifier}/control", json={"command": "stop"}, headers=alice
    )
    wait_until(
        lambda: client.get(f"/api/runs/{identifier}", headers=alice).json()["state"]
        == "cancelled"
    )
    assert client.post("/api/runs", json={}, headers=bob).status_code == 201


def test_failed_run_creation_returns_reserved_capacity(portal):
    client, app = portal
    headers = login(client)
    for _ in range(5):
        assert (
            client.post(
                "/api/runs", json={"algorithm": "does_not_exist"}, headers=headers
            ).status_code
            == 400
        )
    assert app.state.workspaces.global_budget.reserved == 0
    assert client.post("/api/runs", json={}, headers=headers).status_code == 201


@pytest.mark.parametrize("students", [10, 30])
def test_classroom_accounts_share_one_ip_and_run_capacity(tmp_path, students):
    # Real HTTP admission and per-user simulation instances. Paused manual
    # runs deliberately test capacity, not Docker or real-time performance.
    app = create_portal(
        tmp_path,
        HostingSettings(ORIGIN, user_runs=1, total_runs=students, total_storage_gb=80),
        worker_factory=WorkerClient,
    )
    app.state.accounts.create("teacher", PASSWORD, role="admin")
    for index in range(students):
        app.state.accounts.create(f"student{index:02d}", PASSWORD)
    with TestClient(app, base_url=ORIGIN) as client:
        headers = [login(client, f"student{index:02d}") for index in range(students)]
        teacher = login(client, "teacher")
        with ThreadPoolExecutor(max_workers=students) as pool:
            responses = list(
                pool.map(
                    lambda auth: client.post(
                        "/api/runs", json={"algorithm": "manual"}, headers=auth
                    ),
                    headers,
                )
            )
        assert all(response.status_code == 201 for response in responses), [
            response.text for response in responses if response.status_code != 201
        ]
        identifiers = [response.json()["id"] for response in responses]
        assert len(set(identifiers)) == students
        for auth, identifier in zip(headers, identifiers):
            records = client.get("/api/results", headers=auth).json()
            assert [record["episode_id"] for record in records] == [identifier]
        # Every student has one slot, and the teacher sees the full global limit.
        for auth in (headers[0], teacher):
            assert client.post("/api/runs", json={}, headers=auth).status_code == 429
        client.post(
            f"/api/runs/{identifiers[0]}/control",
            json={"command": "stop"},
            headers=headers[0],
        ).raise_for_status()
        wait_until(
            lambda: app.state.workspaces.global_budget.reserved
            == (students - 1) * 256 * 1024**2
        )
        assert client.post("/api/runs", json={}, headers=teacher).status_code == 201


def test_websocket_ownership_origin_and_revocation(portal):
    client, app = portal
    alice, bob = login(client), login(client, "bob")
    run = client.post("/api/runs", json={}, headers=alice).json()["id"]
    path = f"wss://lab.test/api/runs/{run}/stream"
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect(
            path, headers={**alice, "Origin": "https://attacker.test"}
        ):
            pass
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect(path, headers=bob) as socket:
            socket.receive_json()
    with client.websocket_connect(path, headers=alice) as socket:
        socket.send_text("snapshot")
        assert socket.receive_json()["id"] == run
        client.post("/api/auth/logout", headers=alice)
        time.sleep(1.05)
        socket.send_text("snapshot")
        with pytest.raises(WebSocketDisconnect) as closed:
            socket.receive_json()
        assert closed.value.code == 4401
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect(path, headers=alice):
            pass


def test_teacher_disables_student_and_stops_runs(portal):
    client, app = portal
    alice, teacher = login(client), login(client, "teacher")
    identifier = client.get("/api/auth/me", headers=alice).json()["user"]["id"]
    client.post("/api/runs", json={}, headers=alice)
    result = client.patch(
        f"/api/admin/users/{identifier}", json={"enabled": False}, headers=teacher
    )
    assert result.status_code == 200
    assert client.get("/api/results", headers=alice).status_code == 401
    manager = app.state.workspaces.entries[identifier]["manager"]
    assert all(not run.thread.is_alive() for run in manager.runs.values())
    assert list((manager.root / "runs").glob("*/manifest.json"))
    own = client.get("/api/auth/me", headers=teacher).json()["user"]["id"]
    assert (
        client.patch(
            f"/api/admin/users/{own}", json={"enabled": False}, headers=teacher
        ).status_code
        == 409
    )


def test_registration_invitation_and_password_reset(portal):
    client, app = portal
    teacher = login(client, "teacher")
    code = client.post(
        "/api/admin/invitations", json={"uses": 1, "days": 1}, headers=teacher
    ).json()["code"]
    data = {"username": "newstudent", "password": PASSWORD, "invitation": code}
    response = client.post("/api/auth/register", json=data, headers=WRITE)
    assert response.status_code == 201
    user_id = response.json()["user"]["id"]
    assert (
        client.post(
            "/api/auth/register", json={**data, "username": "another"}, headers=WRITE
        ).status_code
        == 400
    )
    student = login(client, "newstudent")
    temporary = client.post(
        f"/api/admin/users/{user_id}/reset-password", headers=teacher
    ).json()["temporary_password"]
    assert client.get("/api/maps", headers=student).status_code == 401
    result = client.post(
        "/api/auth/login",
        json={"username": "newstudent", "password": temporary},
        headers=WRITE,
    )
    assert result.json()["user"]["must_change_password"] is True
    cookie = {**WRITE, "Cookie": f"{COOKIE}={result.cookies[COOKIE]}"}
    client.cookies.clear()
    assert client.post("/api/runs", json={}, headers=cookie).status_code == 401
    changed = client.post(
        "/api/auth/password",
        json={"old_password": temporary, "new_password": PASSWORD},
        headers=cookie,
    )
    assert changed.status_code == 200
    assert client.get("/api/maps", headers=cookie).status_code == 401
    assert (
        client.get("/api/maps", headers=login(client, "newstudent")).status_code == 200
    )


def test_quota_and_body_limits(portal):
    client, app = portal
    headers = login(client)
    client.get("/api/maps", headers=headers)
    user_id = client.get("/api/auth/me", headers=headers).json()["user"]["id"]
    app.state.workspaces.entries[user_id]["budget"].limit = 1
    assert (
        client.post(
            "/api/maps", json=generate("straight", 7).model_dump(), headers=headers
        ).status_code
        == 409
    )
    assert app.state.workspaces.global_budget.reserved == 0
    assert (
        client.post(
            "/api/maps", content=b"x" * (2 * 1024**2 + 1), headers=headers
        ).status_code
        == 413
    )
    chunks = (
        chunk for chunk in (b'{"username":"alice","password":"', b"x" * 17000, b'"}')
    )
    assert (
        client.post("/api/auth/login", content=chunks, headers=WRITE).status_code == 413
    )


def test_invitation_revoke_and_atomic_use(portal):
    client, app = portal
    teacher = login(client, "teacher")
    code = client.post(
        "/api/admin/invitations", json={"uses": 1}, headers=teacher
    ).json()["code"]

    def register(name):
        try:
            app.state.accounts.create(name, PASSWORD, invitation=code)
            return True
        except ValueError:
            return False

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sum(pool.map(register, ("student_one", "student_two"))) == 1
    code = client.post(
        "/api/admin/invitations", json={"uses": 2}, headers=teacher
    ).json()["code"]
    invitation = client.get("/api/admin/invitations", headers=teacher).json()[0]
    assert (
        client.delete(
            f"/api/admin/invitations/{invitation['id']}", headers=teacher
        ).status_code
        == 200
    )
    assert (
        client.post(
            "/api/auth/register",
            json={"username": "revoked", "password": PASSWORD, "invitation": code},
            headers=WRITE,
        ).status_code
        == 400
    )


def test_account_switch_does_not_accept_stale_tabs(portal):
    client, app = portal
    alice, bob = login(client), login(client, "bob")
    owner = client.get("/api/auth/me", headers=alice).json()["user"]["id"]
    response = client.post(
        "/api/maps",
        json=generate("straight", 7).model_dump(),
        headers={**bob, "X-PathLab-User": owner},
    )
    assert response.status_code == 401
    assert client.get("/api/maps", headers=bob).json() == []


def test_sandbox_code_is_readable_with_private_service_umask(portal):
    client, app = portal
    headers = login(client)
    previous = os.umask(0o077)
    try:
        response = client.post(
            "/api/submissions", files={"file": ("code.zip", archive())}, headers=headers
        )
    finally:
        os.umask(previous)
    assert response.status_code == 201
    from pathlib import Path

    code = Path(response.json()["working_directory"])
    assert stat.S_IMODE(code.stat().st_mode) == 0o755
    assert stat.S_IMODE((code / "algorithm.py").stat().st_mode) == 0o644


def test_wall_time_limit_releases_run_slot(portal):
    client, app = portal
    headers = login(client)
    client.get("/api/maps", headers=headers)
    owner = client.get("/api/auth/me", headers=headers).json()["user"]["id"]
    manager = app.state.workspaces.entries[owner]["manager"]
    manager.wall_timeout_s = 0.1
    identifier = client.post("/api/runs", json={}, headers=headers).json()["id"]
    wait_until(lambda: not manager.runs[identifier].thread.is_alive())
    result = client.get(f"/api/results/{identifier}", headers=headers).json()
    assert result["manifest"]["metrics"]["reason"] == "server_time_limit"
    assert app.state.workspaces.global_budget.reserved == 0


def test_batches_are_private_and_run_for_both_users(portal):
    client, app = portal
    alice, bob = login(client), login(client, "bob")
    plan = {
        "name": "private batch",
        "algorithms": [{"algorithm": "constant", "execution": "action"}],
        "families": ["straight"],
        "seeds": [1],
        "max_steps": 2,
    }
    a = client.post("/api/benchmarks", json=plan, headers=alice)
    b = client.post("/api/benchmarks", json=plan, headers=bob)
    assert a.status_code == b.status_code == 201
    aid, bid = a.json()["id"], b.json()["id"]
    assert client.get(f"/api/benchmarks/{aid}", headers=bob).status_code == 404
    assert client.post(f"/api/benchmarks/{aid}/cancel", headers=bob).status_code == 404
    assert client.delete(f"/api/benchmarks/{aid}", headers=bob).status_code == 404
    wait_until(
        lambda: client.get(f"/api/benchmarks/{aid}", headers=alice).json()["state"]
        == "completed"
    )
    wait_until(
        lambda: client.get(f"/api/benchmarks/{bid}", headers=bob).json()["state"]
        == "completed"
    )
    assert len(client.get("/api/benchmarks", headers=alice).json()) == 1


def test_login_throttling(portal):
    client, app = portal
    for _ in range(10):
        response = client.post(
            "/api/auth/login",
            json={"username": "unknown", "password": PASSWORD},
            headers=WRITE,
        )
        assert response.status_code == 401
    assert (
        client.post(
            "/api/auth/login",
            json={"username": "unknown", "password": PASSWORD},
            headers=WRITE,
        ).status_code
        == 429
    )


def test_restart_preserves_sessions_and_data(tmp_path):
    settings = HostingSettings(ORIGIN)
    app = create_portal(tmp_path, settings, worker_factory=WorkerClient)
    app.state.accounts.create("teacher", PASSWORD, role="admin")
    with TestClient(app, base_url=ORIGIN) as client:
        headers = login(client, "teacher")
        saved = client.post(
            "/api/maps", json=generate("straight", 7).model_dump(), headers=headers
        ).json()
        second = create_portal(tmp_path, settings, worker_factory=WorkerClient)
        with pytest.raises(RuntimeError, match="只能启动一个"):
            with TestClient(second):
                pass
    with TestClient(
        create_portal(tmp_path, settings, worker_factory=WorkerClient), base_url=ORIGIN
    ) as client:
        assert client.get("/api/maps", headers=headers).json()[0]["id"] == saved["id"]


def test_docker_command_mounts_only_one_submission(tmp_path):
    folder = tmp_path / "users" / "user" / "submissions" / "upload" / "code"
    folder.mkdir(parents=True)
    spec = PluginSpec(
        id="student",
        name="student",
        version="1",
        capabilities=["action"],
        entrypoint="algorithm:StudentAlgorithm",
        working_directory=str(folder),
    )
    sandbox = DockerSandbox(tmp_path)
    command, name = sandbox.command(spec)
    for flag in (
        "--network=none",
        "--read-only",
        "--cap-drop=ALL",
        "--security-opt=no-new-privileges",
        "--user=65534:65534",
        "--memory=512m",
        "--memory-swap=512m",
        "--pids-limit=64",
        "--cpus=1",
    ):
        assert flag in command
    mounts = [
        command[index + 1] for index, item in enumerate(command) if item == "--mount"
    ]
    assert mounts == [f"type=bind,src={folder},dst=/submission,readonly"]
    assert not any("docker.sock" in item for item in command)
    with pytest.raises(ValueError, match="不属于"):
        sandbox.command(spec.model_copy(update={"working_directory": str(tmp_path)}))
    (folder / "escape").symlink_to(tmp_path)
    with pytest.raises(ValueError, match="符号链接"):
        sandbox.command(spec)


def test_docker_failure_never_falls_back_to_host(tmp_path, monkeypatch):
    monkeypatch.setattr("pathlab.sandbox.shutil.which", lambda _: None)
    with pytest.raises(RuntimeError, match="不会降级"):
        DockerSandbox(tmp_path).preflight()


def test_docker_kill_removes_container(monkeypatch):
    calls = []
    worker = object.__new__(DockerWorker)
    worker.closed, worker.container_name = False, "pathlab-worker-test"
    monkeypatch.setattr(
        WorkerClient, "kill", lambda self: setattr(self, "closed", True)
    )
    monkeypatch.setattr(
        subprocess, "run", lambda command, **kwargs: calls.append(command)
    )
    worker.kill()
    worker.kill()
    assert calls == [["docker", "rm", "-f", "pathlab-worker-test"]]


def test_container_startup_keeps_frame_deadlines(monkeypatch):
    deadlines = []
    monkeypatch.setattr(
        WorkerClient,
        "request",
        lambda self, method, payload, timeout: deadlines.append((method, timeout)),
    )
    worker = object.__new__(DockerWorker)
    for method in ("initialize", "reset", "step"):
        worker.request(method, {}, 0.5)
    assert deadlines == [("initialize", 30), ("reset", 0.5), ("step", 0.5)]
