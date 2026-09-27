"""Authenticated public gateway; one disposable, networkless container per student.

Only this process talks to Docker. Student code gets neither host mounts nor
credentials. HTTP is streamed over exec pipes rather than publishing sandbox ports.
"""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
import hashlib
import hmac
import json
import logging
import os
from pathlib import Path
import re
import secrets
import time
from urllib.parse import urlsplit

from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from .registry import ROOT

COOKIE = "pathlab_session"
BODY_LIMIT = 130 * 1024**2
LABEL = "pathlab.online"


@dataclass
class Settings:
    origin: str
    codes: dict[str, str]
    image: str = "pathlab-session:latest"
    capacity: int = 4
    idle_s: int = 300
    lifetime_s: int = 4 * 3600
    namespace: str = "course"

    def __post_init__(self):
        url = urlsplit(self.origin)
        if (
            url.scheme != "https"
            or not url.netloc
            or url.path
            or url.query
            or url.fragment
        ):
            raise ValueError("PATHLAB_PUBLIC_ORIGIN 必须是无尾斜线的 HTTPS 域名")
        if not 1 <= self.capacity <= 32 or not re.fullmatch(
            r"[a-z0-9-]{1,30}", self.namespace
        ):
            raise ValueError("在线容量或实例名称无效")
        if (
            not self.codes
            or len(self.codes) > 1000
            or len(set(self.codes.values())) != len(self.codes)
        ):
            raise ValueError("请提供 1～1000 个互不重复的学生访问码")
        if any(
            not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", k)
            or not isinstance(v, str)
            or len(v) < 24
            for k, v in self.codes.items()
        ):
            raise ValueError("学生编号须为字母数字，访问码至少 24 字符；请使用生成脚本")

    @classmethod
    def environment(cls):
        codes = json.loads(Path(os.environ["PATHLAB_ACCESS_CODES_FILE"]).read_text())
        return cls(
            origin=os.environ["PATHLAB_PUBLIC_ORIGIN"],
            codes=codes,
            image=os.getenv("PATHLAB_SESSION_IMAGE", "pathlab-session:latest"),
            capacity=int(os.getenv("PATHLAB_MAX_SESSIONS", "4")),
            namespace=os.getenv("PATHLAB_INSTANCE", "course"),
        )


@dataclass
class Session:
    student: str
    token: str
    container: str
    created: float = field(default_factory=time.monotonic)
    seen: float = field(default_factory=time.monotonic)
    requests: int = 0
    sockets: int = 0
    credits: float = 30
    credited_at: float = field(default_factory=time.monotonic)

    def admit(self):
        now = time.monotonic()
        self.credits = min(30, self.credits + (now - self.credited_at) * 12)
        self.credited_at = now
        if self.requests >= 4 or self.credits < 1:
            raise HTTPException(429, "请求过于频繁，请稍后重试")
        self.credits -= 1
        self.seen = now


class Docker:
    def __init__(self, settings):
        self.settings = settings

    async def command(self, *args):
        process = await asyncio.create_subprocess_exec(
            "docker",
            *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout, stderr = await asyncio.wait_for(process.communicate(), 40)
        except BaseException:
            process.kill()
            await process.wait()
            raise
        if process.returncode:
            # Do not expose Docker daemon/host paths to a browser.
            raise RuntimeError(f"Docker {args[0]} failed")
        return stdout.decode().strip()

    async def validate(self):
        info = json.loads(await self.command("info", "--format", "{{json .}}"))
        required = ("MemoryLimit", "SwapLimit", "CpuCfsQuota", "PidsLimit")
        if (
            not all(info.get(key) for key in required)
            or info.get("CgroupDriver") == "none"
        ):
            raise RuntimeError(
                "Docker 必须支持内存、交换、CPU 和进程限制；不降级到无约束运行"
            )
        if not any(
            "name=seccomp" in value for value in info.get("SecurityOptions", [])
        ):
            raise RuntimeError("Docker 必须启用默认 seccomp")
        if info.get("MemTotal", 0) < (self.settings.capacity + 2) * 1024**3:
            raise RuntimeError(
                "Docker 主机总内存不足以支撑配置的席位，请降低 PATHLAB_MAX_SESSIONS"
            )

    async def cleanup(self):
        containers = await self.command(
            "ps", "-aq", "--filter", f"label={LABEL}={self.settings.namespace}"
        )
        if containers:
            await self.command("rm", "-f", *containers.splitlines())

    async def start(self, name):
        # Docker CLI can inject proxy credentials from the administrator's config.
        # Explicit empty values prevent those from entering student containers.
        proxy_names = (
            "HTTP_PROXY",
            "HTTPS_PROXY",
            "ALL_PROXY",
            "FTP_PROXY",
            "NO_PROXY",
            "http_proxy",
            "https_proxy",
            "all_proxy",
            "ftp_proxy",
            "no_proxy",
        )
        proxy_flags = [part for key in proxy_names for part in ("--env", f"{key}=")]
        await self.command(
            "run",
            "-d",
            "--name",
            name,
            "--label",
            f"{LABEL}={self.settings.namespace}",
            "--network",
            "none",
            "--read-only",
            "--user",
            "1000:1000",
            "--cap-drop",
            "ALL",
            "--security-opt",
            "no-new-privileges",
            "--cpus",
            "1",
            "--memory",
            "1g",
            "--memory-swap",
            "1g",
            "--pids-limit",
            "128",
            "--ulimit",
            "nofile=1024:1024",
            "--log-driver",
            "none",
            "--tmpfs",
            "/app/artifacts:rw,nosuid,nodev,noexec,size=384m,uid=1000,gid=1000,mode=0700",
            "--tmpfs",
            "/tmp:rw,nosuid,nodev,noexec,size=192m,mode=1777",
            "--env",
            "PATHLAB_EPHEMERAL=1",
            "--env",
            "PYTHONDONTWRITEBYTECODE=1",
            "--env",
            "OMP_NUM_THREADS=1",
            "--env",
            "OPENBLAS_NUM_THREADS=1",
            *proxy_flags,
            self.settings.image,
        )
        # Uvicorn initialization includes checking optional plugin availability.
        for _ in range(30):
            try:
                _, data = await self.small(name, "/api/health")
                if json.loads(data).get("status") == "ok":
                    return
            except (RuntimeError, ValueError, asyncio.TimeoutError):
                pass
            await asyncio.sleep(0.2)
        raise RuntimeError("运行环境启动超时")

    async def stop(self, name):
        await self.command("rm", "-f", name)

    @asynccontextmanager
    async def exchange(self, container, method, path, content_type, chunks):
        process = await asyncio.create_subprocess_exec(
            "docker",
            "exec",
            "-i",
            container,
            "python",
            "-m",
            "pathlab.tunnel",
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
            limit=65536,
        )

        async def feed():
            metadata = {"method": method, "path": path, "content_type": content_type}
            process.stdin.write(json.dumps(metadata).encode() + b"\n")
            total = 0
            async for data in chunks:
                total += len(data)
                if total > BODY_LIMIT:
                    raise HTTPException(413, "请求体超过 130 MiB")
                for start in range(0, len(data), 65536):
                    part = data[start : start + 65536]
                    process.stdin.write(f"{len(part):x}\n".encode() + part)
                    await process.stdin.drain()
            process.stdin.write(b"0\n")
            await process.stdin.drain()
            process.stdin.close()

        feeder = asyncio.create_task(feed())
        try:
            # Both directions are bounded. Missing/failed upload never leaves exec alive.
            await asyncio.wait_for(feeder, 90)
            line = await asyncio.wait_for(process.stdout.readline(), 90)
            if not line or len(line) > 8192:
                raise RuntimeError("运行环境未响应")
            metadata = json.loads(line)
            yield metadata, process.stdout
        finally:
            feeder.cancel()
            await asyncio.gather(feeder, return_exceptions=True)
            if process.returncode is None:
                try:
                    process.kill()
                except ProcessLookupError:
                    pass
            await asyncio.shield(process.wait())

    async def small(self, container, path):
        async def empty():
            if False:
                yield b""

        async with self.exchange(container, "GET", path, "", empty()) as (
            metadata,
            stream,
        ):
            parts, size = [], 0
            while data := await asyncio.wait_for(stream.read(65536), 45):
                size += len(data)
                if size > 8 * 1024**2:
                    raise RuntimeError("快照超过大小限制")
                parts.append(data)
            return metadata, b"".join(parts)


class Sessions:
    def __init__(self, settings, docker):
        self.settings, self.docker = settings, docker
        self.items: dict[str, Session] = {}
        self.lock = asyncio.Lock()
        self.login_credit, self.login_time = 20.0, time.monotonic()

    def get(self, token):
        session = self.items.get(token)
        if (
            not session
            or time.monotonic() - session.created >= self.settings.lifetime_s
        ):
            raise HTTPException(401, "会话已结束，请重新登录并恢复本地工作区")
        return session

    async def login(self, code):
        now = time.monotonic()
        self.login_credit = min(20, self.login_credit + (now - self.login_time) / 3)
        self.login_time = now
        if self.login_credit < 1:
            raise HTTPException(429, "登录请求过多，请稍后重试")
        self.login_credit -= 1
        student = next(
            (
                k
                for k, value in self.settings.codes.items()
                if hmac.compare_digest(value, code)
            ),
            None,
        )
        if student is None:
            raise HTTPException(401, "访问码不正确")
        async with self.lock:
            for session in self.items.values():
                if session.student == student:
                    self.get(session.token)
                    session.seen = time.monotonic()
                    return session
            if len(self.items) >= self.settings.capacity:
                raise HTTPException(429, "当前运行席位已满，请稍后再进入")
            name = f"pathlab-{self.settings.namespace}-{secrets.token_hex(8)}"
            try:
                await self.docker.start(name)
            except BaseException:
                await self.docker.stop(name)
                raise
            session = Session(student, secrets.token_urlsafe(32), name)
            self.items[session.token] = session
            return session

    async def remove(self, token):
        async with self.lock:
            session = self.items.get(token)
            if session:
                await self.docker.stop(session.container)
                self.items.pop(token, None)

    async def reap(self):
        while True:
            await asyncio.sleep(15)
            now = time.monotonic()
            for token, session in list(self.items.items()):
                if (
                    now - session.seen > self.settings.idle_s
                    or now - session.created > self.settings.lifetime_s
                ):
                    try:
                        await self.remove(token)
                    except Exception:
                        logging.getLogger(__name__).warning(
                            "临时环境回收失败，将重试；席位不会因此释放"
                        )


def create_public_app(settings=None, docker=None):
    settings = settings or Settings.environment()
    docker = docker or Docker(settings)
    sessions = Sessions(settings, docker)

    @asynccontextmanager
    async def lifespan(app):
        # Exactly one gateway owns an instance, including startup cleanup.
        import fcntl

        namespace = hashlib.sha256(settings.namespace.encode()).hexdigest()[:16]
        descriptor = os.open(
            f"/tmp/pathlab-online-{namespace}.lock",
            os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW,
            0o600,
        )
        with os.fdopen(descriptor, "a") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            await docker.validate()
            await docker.cleanup()
            reaper = asyncio.create_task(sessions.reap())
            try:
                yield
            finally:
                reaper.cancel()
                await asyncio.gather(reaper, return_exceptions=True)
                await docker.cleanup()

    app = FastAPI(lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)
    app.state.sessions = sessions

    @app.middleware("http")
    async def protection(request, call_next):
        if (
            request.method not in {"GET", "HEAD"}
            and request.headers.get("origin") != settings.origin
        ):
            return JSONResponse({"detail": "请求来源不匹配"}, status_code=403)
        length = request.headers.get("content-length", "0")
        if len(length) > 12 or not length.isdigit() or int(length) > BODY_LIMIT:
            return JSONResponse({"detail": "请求体超过上限"}, status_code=413)
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "same-origin"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Cache-Control"] = (
            "no-store" if request.url.path.startswith("/api") else "public, max-age=300"
        )
        return response

    @app.get("/api/hosting")
    async def hosting(request: Request):
        try:
            session = sessions.get(request.cookies.get(COOKIE))
        except HTTPException:
            return {"mode": "online", "authenticated": False}
        session.seen = time.monotonic()
        return {
            "mode": "online",
            "authenticated": True,
            "student": session.student,
            "expires_in_s": max(
                0, int(settings.lifetime_s - (time.monotonic() - session.created))
            ),
            "idle_timeout_s": settings.idle_s,
            "workspace_limit_mb": 128,
        }

    @app.post("/api/session")
    async def login(request: Request):
        raw = bytearray()
        async for chunk in request.stream():
            raw.extend(chunk)
            if len(raw) > 4096:
                raise HTTPException(413)
        try:
            code = json.loads(raw)["code"]
            if not isinstance(code, str) or not code.isascii() or len(code) > 256:
                raise ValueError()
        except (ValueError, KeyError, TypeError):
            raise HTTPException(400, "请提供访问码")
        try:
            session = await sessions.login(code)
        except (RuntimeError, FileNotFoundError, asyncio.TimeoutError):
            raise HTTPException(503, "隔离运行环境暂不可用，请联系教师")
        response = JSONResponse({"student": session.student})
        response.set_cookie(
            COOKIE,
            session.token,
            secure=True,
            httponly=True,
            samesite="strict",
            max_age=settings.lifetime_s,
        )
        return response

    @app.delete("/api/session")
    async def logout(request: Request):
        session = sessions.get(request.cookies.get(COOKIE))
        await sessions.remove(session.token)
        response = JSONResponse({"closed": True})
        response.delete_cookie(COOKIE, secure=True, httponly=True, samesite="strict")
        return response

    @app.api_route(
        "/api/{path:path}", methods=["GET", "POST", "DELETE", "PUT", "PATCH"]
    )
    async def proxy(request: Request, path: str):
        session = sessions.get(request.cookies.get(COOKIE))
        session.admit()
        session.requests += 1
        # Pass the encoded path to prevent query/path reinterpretation by HTTPClient.
        target = request.scope["raw_path"].decode("ascii")
        if request.url.query:
            target += "?" + request.url.query
        exchange = docker.exchange(
            session.container,
            request.method,
            target,
            request.headers.get("content-type", ""),
            request.stream(),
        )
        try:
            metadata, stream = await exchange.__aenter__()
        except (RuntimeError, FileNotFoundError, asyncio.TimeoutError) as error:
            session.requests -= 1
            raise HTTPException(
                502, "临时运行环境未响应，请保留本地备份并重试"
            ) from error
        except BaseException:
            session.requests -= 1
            raise

        async def body():
            total = 0
            try:
                while chunk := await asyncio.wait_for(stream.read(65536), 90):
                    total += len(chunk)
                    if total > 160 * 1024**2:
                        raise RuntimeError("响应过大")
                    yield chunk
            finally:
                session.requests -= 1
                await asyncio.shield(exchange.__aexit__(None, None, None))

        return StreamingResponse(
            body(), status_code=metadata["status"], headers=metadata["headers"]
        )

    @app.websocket("/api/runs/{run_id}/stream")
    async def stream(websocket: WebSocket, run_id: str):
        if websocket.headers.get("origin") != settings.origin or not re.fullmatch(
            r"[0-9a-f]{32}", run_id
        ):
            await websocket.close(code=1008)
            return
        try:
            session = sessions.get(websocket.cookies.get(COOKIE))
        except HTTPException:
            await websocket.close(code=1008)
            return
        if session.sockets >= 2:
            await websocket.close(code=1013)
            return
        session.sockets += 1
        await websocket.accept()
        try:
            while True:
                message = await asyncio.wait_for(websocket.receive_text(), 20)
                if message != "snapshot":
                    break
                sessions.get(session.token)
                session.admit()
                session.requests += 1
                try:
                    metadata, data = await docker.small(
                        session.container, f"/api/runs/{run_id}"
                    )
                finally:
                    session.requests -= 1
                if metadata["status"] != 200:
                    break
                await websocket.send_text(data.decode())
        except (HTTPException, RuntimeError, WebSocketDisconnect, asyncio.TimeoutError):
            pass
        finally:
            session.sockets -= 1
            try:
                await websocket.close()
            except RuntimeError:
                pass

    dist = ROOT / "frontend" / "dist"
    if (dist / "assets").exists():
        app.mount("/assets", StaticFiles(directory=dist / "assets"))

    @app.get("/")
    def index():
        return FileResponse(dist / "index.html")

    return app
