"""Shared local server lifecycle for browser regressions with isolated data."""

from contextlib import contextmanager
import os
from pathlib import Path
import signal
import socket
import subprocess
import sys
import time

import httpx

ROOT = Path(__file__).resolve().parent.parent
os.environ.setdefault("PLAYWRIGHT_BROWSERS_PATH", str(ROOT / ".cache" / "browsers"))


def until(predicate, timeout=12):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return
        time.sleep(0.08)
    raise AssertionError("浏览器验收等待超时")


@contextmanager
def serve_test(data, output):
    """Start a test-only API server and always reap its process on exit."""
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    command = (
        "from pathlib import Path; import uvicorn; from pathlab.api import create_app; "
        f"uvicorn.run(create_app(Path({str(data)!r})), host='127.0.0.1', port={port})"
    )
    with (output / "server.log").open("w") as log:
        server = subprocess.Popen(
            [sys.executable, "-c", command],
            cwd=ROOT,
            stdout=log,
            stderr=log,
            start_new_session=os.name != "nt",
        )
        try:
            with httpx.Client(
                base_url=f"http://127.0.0.1:{port}", timeout=30, trust_env=False
            ) as http:

                def ready():
                    if server.poll() is not None:
                        raise RuntimeError(
                            f"测试服务启动失败，见 {output / 'server.log'}"
                        )
                    try:
                        return http.get("/api/health").is_success
                    except httpx.ConnectError:
                        return False

                until(ready)
                yield http
        finally:
            if server.poll() is None:
                server.terminate()
                try:
                    server.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    if os.name == "nt":
                        server.kill()
                    else:
                        os.killpg(server.pid, signal.SIGKILL)
                    server.wait()
