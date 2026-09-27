"""Online ownership, bounded archives, and recovery with real worker execution.

Docker flags are asserted separately; API isolation tests use independent real
ASGI apps so they do not require granting the test suite Docker daemon access.
"""

import asyncio
import base64
from contextlib import asynccontextmanager
import io
import json
import stat
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import zipfile

from fastapi.testclient import TestClient
import httpx
import pytest

from pathlab.api import create_app
from pathlab.public import COOKIE, Docker, Settings, create_public_app
from pathlab.scenarios import generate
from pathlab.submissions import template_zip
from pathlab.workspace import FORMAT, restore_workspace
from .conftest import wait_until
from .test_api import run_complete


def zipped(entries):
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("workspace.json", json.dumps({"format": FORMAT}))
        for name, value in entries:
            archive.writestr(name, value)
    return out.getvalue()


def test_workspace_roundtrip_maps_submission_source_and_real_replay(
    tmp_path, monkeypatch
):
    monkeypatch.setenv("PATHLAB_EPHEMERAL", "1")
    first, second = tmp_path / "first", tmp_path / "second"
    with TestClient(create_app(first)) as client:
        scene = generate("straight", 7).model_dump()
        saved_map = client.post("/api/maps", json=scene).json()
        png = base64.b64decode(client.get("/api/scenes/straight").json()["image"])
        source = client.post(
            "/api/sources", files={"files": ("frame.png", png, "image/png")}
        ).json()
        batch = client.post(
            "/api/benchmarks",
            json={
                "algorithms": [{"algorithm": "stop"}],
                "families": ["straight"],
                "seeds": [11],
                "max_steps": 1,
            },
        ).json()
        wait_until(
            lambda: client.get(f"/api/benchmarks/{batch['id']}").json()["state"]
            in {"completed", "failed"}
        )
        spec = client.post(
            "/api/submissions", files={"file": ("code.zip", template_zip())}
        ).json()
        run_id = run_complete(
            client, {"algorithm": spec["id"], "max_steps": 2, "realtime": False}
        )
        wait_until(lambda: not client.app.state.manager.runs[run_id].thread.is_alive())
        expected = client.get(f"/api/results/{run_id}/frames/0").json()
        archive = client.get("/api/workspace/archive")
        assert archive.status_code == 200
        assert client.get("/api/workspace").json()["busy"] is False
    with TestClient(create_app(second)) as client:
        response = client.post("/api/workspace/archive", content=archive.content)
        assert response.status_code == 200, response.text
        assert client.get("/api/maps").json()[0]["id"] == saved_map["id"]
        assert client.get(f"/api/sources/{source['id']}/preview").status_code == 200
        assert (
            client.get(f"/api/benchmarks/{batch['id']}").json()["state"] == "completed"
        )
        restored = client.get(f"/api/results/{run_id}/frames/0").json()
        assert restored["image"] == expected["image"]
        assert restored["frame"] == expected["frame"]
        plugins = client.get("/api/catalog").json()["algorithms"]
        plugin = next(p for p in plugins if p["id"] == spec["id"])
        assert plugin["working_directory"].startswith(str(second))
        rerun = run_complete(
            client, {"algorithm": spec["id"], "max_steps": 1, "realtime": False}
        )
        assert not client.get(f"/api/results/{rerun}").json()["manifest"]["failures"]
        assert client.post(
            "/api/workspace/archive", content=archive.content
        ).status_code in {400, 409}
        assert (second / "runs" / run_id / "manifest.json").is_file()


@pytest.mark.parametrize(
    "name",
    [
        "../escape",
        "/tmp/escape",
        "maps/../../escape",
        "maps\\escape",
        "unrelated/data",
        "maps/C:evil",
    ],
)
def test_workspace_rejects_paths_without_partial_restore(tmp_path, name):
    root = tmp_path / "root"
    root.mkdir()
    source = tmp_path / "archive.zip"
    source.write_bytes(zipped([(name, "payload")]))
    with pytest.raises(ValueError):
        restore_workspace(root, source)
    assert not list(root.iterdir())


def test_workspace_rejects_symlinks_duplicates_and_expansion(tmp_path, monkeypatch):
    root = tmp_path / "root"
    root.mkdir()
    source = tmp_path / "archive.zip"
    link = zipfile.ZipInfo("maps/link")
    link.external_attr = (stat.S_IFLNK | 0o777) << 16
    for contents in (
        [(link, "/etc/passwd")],
        [("maps/a", "a"), ("maps/A", "b")],
        [("maps/huge", "x" * 1024)],
    ):
        source.write_bytes(zipped(contents))
        monkeypatch.setattr("pathlab.workspace.LIMIT", 500)
        with pytest.raises(ValueError):
            restore_workspace(root, source)
        assert not list(root.iterdir())


def test_active_workspace_can_be_reopened_but_not_archived(tmp_path, monkeypatch):
    monkeypatch.setenv("PATHLAB_EPHEMERAL", "1")
    with TestClient(create_app(tmp_path)) as client:
        run = client.post("/api/runs", json={"algorithm": "manual"}).json()["id"]
        assert client.get("/api/workspace/active-run").json()["id"] == run
        assert client.get("/api/workspace").json()["busy"] is True
        assert client.get("/api/workspace/archive").status_code == 409
        client.post(f"/api/runs/{run}/control", json={"command": "stop"})
        wait_until(lambda: not client.app.state.manager.runs[run].thread.is_alive())
        assert client.get("/api/workspace/archive").status_code == 200


def test_local_mode_has_no_archive_import_endpoint(tmp_path):
    with TestClient(create_app(tmp_path)) as client:
        assert client.get("/api/hosting").json() == {"mode": "local"}
        assert (
            client.post("/api/workspace/archive", content=b"untrusted").status_code
            == 404
        )


class InProcessDocker:
    def __init__(self, root):
        self.root, self.apps, self.lifespans = root, {}, {}

    async def validate(self):
        pass

    async def start(self, name):
        app = create_app(self.root / name)
        self.apps[name] = app
        lifespan = app.router.lifespan_context(app)
        await lifespan.__aenter__()
        self.lifespans[name] = lifespan

    async def stop(self, name):
        if name in self.apps:
            await self.lifespans.pop(name).__aexit__(None, None, None)
            self.apps.pop(name)

    async def cleanup(self):
        for name in list(self.apps):
            await self.stop(name)

    @asynccontextmanager
    async def exchange(self, container, method, path, content_type, chunks):
        body = b"".join([chunk async for chunk in chunks])
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=self.apps[container]),
            base_url="http://sandbox",
        ) as client:
            response = await client.request(
                method, path, content=body, headers={"content-type": content_type}
            )
        stream = asyncio.StreamReader()
        stream.feed_data(response.content)
        stream.feed_eof()
        yield (
            {
                "status": response.status_code,
                "headers": {
                    "content-type": response.headers.get(
                        "content-type", "application/json"
                    )
                },
            },
            stream,
        )

    async def small(self, container, path):
        async def empty():
            if False:
                yield b""

        async with self.exchange(container, "GET", path, "", empty()) as (
            metadata,
            stream,
        ):
            return metadata, await stream.read()


@pytest.fixture
def public(tmp_path, monkeypatch):
    monkeypatch.setenv("PATHLAB_EPHEMERAL", "1")
    settings = Settings(
        "https://lab.example.edu",
        {"alice": "a" * 32, "bob": "b" * 32},
        namespace="test",
    )
    docker = InProcessDocker(tmp_path)
    app = create_public_app(settings, docker)
    with TestClient(app, base_url=settings.origin) as client:
        yield client, app, docker


def login(client, code):
    response = client.post(
        "/api/session",
        json={"code": code},
        headers={"origin": "https://lab.example.edu"},
    )
    assert response.status_code == 200, response.text
    assert "HttpOnly" in response.headers["set-cookie"]
    assert "Secure" in response.headers["set-cookie"]
    return client.cookies.get(COOKIE)


def test_public_auth_origin_ownership_and_recovery(public):
    client, app, docker = public
    assert client.get("/api/results").status_code == 401
    assert client.post("/api/session", json={"code": "a" * 32}).status_code == 403
    assert (
        client.post(
            "/api/session",
            json={"code": "wrong"},
            headers={"origin": "https://lab.example.edu"},
        ).status_code
        == 401
    )
    alice = login(client, "a" * 32)
    headers = {"origin": "https://lab.example.edu"}
    scene = generate("straight", 37).model_dump()
    saved = client.post("/api/maps", json=scene, headers=headers).json()
    archived = client.get("/api/workspace/archive").content
    bob = login(client, "b" * 32)
    assert bob != alice
    assert client.get("/api/maps").json() == []
    assert client.delete(f"/api/maps/{saved['id']}", headers=headers).status_code == 404
    assert (
        client.post(
            "/api/workspace/archive", content=archived, headers=headers
        ).status_code
        == 200
    )
    assert client.get("/api/maps").json()[0]["id"] == saved["id"]
    assert client.delete(f"/api/maps/{saved['id']}", headers=headers).status_code == 200
    client.cookies.set(COOKIE, alice)
    assert len(client.get("/api/maps").json()) == 1
    assert client.delete("/api/session", headers=headers).status_code == 200
    assert len(docker.apps) == 1
    assert client.get("/api/maps").status_code == 401


def test_capacity_expiration_body_limit_and_request_budget(public):
    client, app, _ = public
    app.state.sessions.settings.capacity = 1
    token = login(client, "a" * 32)
    assert (
        client.post(
            "/api/session",
            json={"code": "b" * 32},
            headers={"origin": "https://lab.example.edu"},
        ).status_code
        == 429
    )
    assert (
        client.post(
            "/api/maps",
            content=b"x",
            headers={
                "origin": "https://lab.example.edu",
                "content-length": str(131 * 1024**2),
            },
        ).status_code
        == 413
    )
    session = app.state.sessions.items[token]
    session.requests = 4
    assert client.get("/api/maps").status_code == 429
    session.requests = 0
    session.created -= 15000
    assert client.get("/api/maps").status_code == 401
    assert client.get("/api/hosting").json()["authenticated"] is False


def test_websocket_origin_and_ownership(public):
    client, app, _ = public
    login(client, "a" * 32)
    created = client.post(
        "/api/runs",
        json={"algorithm": "manual"},
        headers={"origin": "https://lab.example.edu"},
    ).json()
    with client.websocket_connect(
        f"wss://lab.example.edu/api/runs/{created['id']}/stream",
        headers={"origin": "https://lab.example.edu"},
    ) as ws:
        ws.send_text("snapshot")
        assert ws.receive_json()["id"] == created["id"]
    from starlette.websockets import WebSocketDisconnect

    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect(
            f"wss://lab.example.edu/api/runs/{created['id']}/stream",
            headers={"origin": "https://evil.example"},
        ):
            pass
    login(client, "b" * 32)
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect(
            f"wss://lab.example.edu/api/runs/{created['id']}/stream",
            headers={"origin": "https://lab.example.edu"},
        ) as ws:
            ws.send_text("snapshot")
            ws.receive_json()


def test_docker_configuration_has_resource_and_network_boundaries():
    class Recorder(Docker):
        async def command(self, *args):
            self.calls.append(args)
            return ""

        async def small(self, container, path):
            return {}, b'{"status":"ok"}'

    docker = Recorder(Settings("https://lab.example.edu", {"student": "x" * 32}))
    docker.calls = []
    asyncio.run(docker.start("test"))
    args = list(docker.calls[0])
    for option, value in {
        "--network": "none",
        "--memory": "1g",
        "--memory-swap": "1g",
        "--cpus": "1",
        "--pids-limit": "128",
        "--user": "1000:1000",
        "--cap-drop": "ALL",
        "--log-driver": "none",
    }.items():
        assert args[args.index(option) + 1] == value
    assert "--read-only" in args and "--security-opt" in args
    assert not (
        {"--volume", "-v", "--mount", "--publish", "-p", "--privileged"} & set(args)
    )


def test_tunnel_streams_binary_request_and_response():
    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            chunks = []
            while True:
                size = int(self.rfile.readline(), 16)
                if not size:
                    self.rfile.readline()
                    break
                chunks.append(self.rfile.read(size))
                assert self.rfile.read(2) == b"\r\n"
            body = b"".join(chunks)
            self.send_response(200)
            self.send_header("Content-Type", "application/octet-stream")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        script = f"import pathlab.tunnel as t; c=t.http.client.HTTPConnection; t.http.client.HTTPConnection=lambda host,port,timeout: c(host,{server.server_port},timeout=timeout); t.main()"
        raw = b"\x00\xffbinary\n" * 10000
        request = (
            json.dumps(
                {
                    "method": "POST",
                    "path": "/",
                    "content_type": "application/octet-stream",
                }
            ).encode()
            + b"\n"
        )
        for i in range(0, len(raw), 65536):
            part = raw[i : i + 65536]
            request += f"{len(part):x}\n".encode() + part
        response = subprocess.run(
            [sys.executable, "-c", script],
            input=request + b"0\n",
            capture_output=True,
            timeout=10,
            check=True,
        )
        header, body = response.stdout.split(b"\n", 1)
        assert json.loads(header)["status"] == 200
        assert body == raw
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


def test_online_single_run_and_no_duplicate_images(tmp_path, monkeypatch):
    monkeypatch.setenv("PATHLAB_EPHEMERAL", "1")
    with TestClient(create_app(tmp_path)) as client:
        first = client.post(
            "/api/runs", json={"algorithm": "manual", "record_images": True}
        ).json()
        assert first["config"]["record_images"] is False
        assert client.post("/api/runs", json={"algorithm": "manual"}).status_code == 400
        assert client.get("/api/catalog").json()["limits"]["active_runs"] == 1


def test_access_codes_are_private_unique_and_never_overwritten(tmp_path):
    destination = tmp_path / "codes.json"
    args = [
        sys.executable,
        "scripts/create_access_codes.py",
        "--count",
        "2",
        "--output",
        str(destination),
    ]
    result = subprocess.run(args, check=True, capture_output=True, text=True)
    codes = json.loads(destination.read_text())
    assert len(set(codes.values())) == 2
    assert all(len(code) >= 24 and code not in result.stdout for code in codes.values())
    assert destination.stat().st_mode & 0o777 == 0o600
    assert subprocess.run(args, capture_output=True).returncode != 0
    assert json.loads(destination.read_text()) == codes


def test_docker_refuses_missing_resource_isolation():
    class Unsupported(Docker):
        async def command(self, *args):
            return json.dumps(
                {
                    "MemoryLimit": True,
                    "SwapLimit": False,
                    "CpuCfsQuota": True,
                    "PidsLimit": True,
                }
            )

    docker = Unsupported(Settings("https://lab.example.edu", {"student": "x" * 32}))
    with pytest.raises(RuntimeError, match="不降级"):
        asyncio.run(docker.validate())
