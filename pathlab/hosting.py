"""Account gateway and isolated per-user instances of the existing lab API."""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from dataclasses import dataclass
import fcntl
from http.cookies import SimpleCookie
from pathlib import Path
import secrets
import shutil
import threading
import time
from urllib.parse import urlsplit

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from starlette.datastructures import Headers, QueryParams
from starlette.middleware.trustedhost import TrustedHostMiddleware

from .accounts import Accounts, token_hash
from .api import create_app
from .engine import RunCapacityError, RunManager, TERMINAL
from .registry import ROOT
from .sandbox import DockerSandbox
from .storage import directory_bytes

COOKIE = "pathlab_session"
MIB = 1024**2


@dataclass
class HostingSettings:
    public_url: str
    user_runs: int = 2
    total_runs: int = 8
    user_storage_gb: int = 2
    total_storage_gb: int = 20
    max_users: int = 200
    worker_image: str = "pathlab-worker:local"
    wall_timeout_s: int = 600
    allow_http: bool = False

    def __post_init__(self):
        if not 1 <= self.wall_timeout_s <= 3600:
            raise ValueError("单次实验时间上限应为 1～3600 秒")
        self.public_url = self.public_url.rstrip("/")
        url = urlsplit(self.public_url)
        if (
            url.scheme not in {"http", "https"}
            or not url.hostname
            or url.path
            or url.query
            or url.fragment
            or url.username
            or url.password
        ):
            raise ValueError(
                "public-url 必须是完整网站地址，例如 https://lab.example.edu，不带路径"
            )
        if (
            url.scheme == "http"
            and url.hostname not in {"localhost", "127.0.0.1", "::1"}
            and not self.allow_http
        ):
            raise ValueError(
                "公网账号登录需要 HTTPS；临时 HTTP 调试须显式设置 --allow-http"
            )
        if not 1 <= self.user_runs <= self.total_runs <= 64:
            raise ValueError("并发上限必须满足 1 ≤ 每人 ≤ 全站 ≤ 64")
        if (
            not 1 <= self.user_storage_gb <= self.total_storage_gb <= 10000
            or not 1 <= self.max_users <= 1000
        ):
            raise ValueError("存储或账号上限不合法")

    @property
    def secure(self):
        return self.public_url.startswith("https://")


class Budget:
    """Conservative reservations include in-flight writes and atomic temp files."""

    def __init__(self, root, limit):
        self.root, self.limit, self.reserved = root, limit, 0
        self.lock = threading.Lock()

    def reserve(self, amount):
        with self.lock:
            if directory_bytes(self.root) + self.reserved + amount > self.limit:
                raise HTTPException(409, "存储空间不足，请删除旧记录、算法或素材后重试")
            if shutil.disk_usage(self.root).free < amount + 128 * MIB:
                raise HTTPException(507, "服务器剩余磁盘空间不足，请联系管理员")
            self.reserved += amount
        released = False

        def release():
            nonlocal released
            with self.lock:
                if not released:
                    self.reserved -= amount
                    released = True

        return release


class Credentials(BaseModel):
    username: str = Field(min_length=3, max_length=32)
    password: str = Field(min_length=1, max_length=128)


class Registration(Credentials):
    display_name: str = Field(default="", max_length=60)
    invitation: str = Field(min_length=16, max_length=128)


class NewUser(Credentials):
    display_name: str = Field(default="", max_length=60)


class PasswordChange(BaseModel):
    old_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=12, max_length=128)


class UserState(BaseModel):
    enabled: bool


class Invitation(BaseModel):
    uses: int = Field(default=1, ge=1, le=200)
    days: int = Field(default=7, ge=1, le=30)


def session_token(scope):
    cookies = SimpleCookie()
    try:
        cookies.load(Headers(scope=scope).get("cookie", ""))
        return cookies[COOKIE].value if COOKIE in cookies else None
    except Exception:
        return None


class RequestGuard:
    """Same-origin writes, bounded streamed bodies, and bounded HTTP work."""

    def __init__(self, app, origin):
        self.app, self.origin = app, origin
        self.slots = asyncio.Semaphore(32)
        self.upload_slots = asyncio.Semaphore(4)

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        headers = Headers(scope=scope)
        path = scope["path"]
        unsafe = scope["method"] not in {"GET", "HEAD", "OPTIONS"}
        if unsafe and (
            headers.get("origin") not in {None, self.origin}
            or headers.get("x-pathlab-request") != "1"
        ):
            return await JSONResponse(
                {"detail": "请求来源校验失败，请刷新网页后重试"}, 403
            )(scope, receive, send)
        upload = path in {"/api/submissions", "/api/sources"} and unsafe
        slots = self.upload_slots if upload else self.slots
        if slots.locked():
            return await JSONResponse({"detail": "服务器忙，请稍后重试"}, 429)(
                scope, receive, send
            )
        limit = (
            36 * MIB
            if upload
            else (16 * 1024 if path.startswith("/api/auth/") else 2 * MIB)
        )
        try:
            length = int(headers.get("content-length", "0"))
        except ValueError:
            length = -1
        if length < 0 or length > limit:
            return await JSONResponse({"detail": "请求内容超过大小限制"}, 413)(
                scope, receive, send
            )
        used = 0

        async def bounded_receive():
            nonlocal used
            message = await receive()
            used += len(message.get("body", b""))
            if used > limit:
                raise HTTPException(413, "请求内容超过大小限制")
            return message

        async def secure_send(message):
            if message["type"] == "http.response.start":
                message.setdefault("headers", []).extend(
                    [
                        (b"x-content-type-options", b"nosniff"),
                        (b"referrer-policy", b"same-origin"),
                        (b"x-frame-options", b"DENY"),
                        (
                            b"content-security-policy",
                            b"default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'",
                        ),
                    ]
                )
                if path.startswith("/api/"):
                    message["headers"].append((b"cache-control", b"no-store"))
            await send(message)

        async with slots:
            await self.app(scope, bounded_receive, secure_send)


class Workspaces:
    def __init__(self, root, accounts, settings, worker_factory):
        self.root, self.accounts, self.settings = root, accounts, settings
        self.worker_factory = worker_factory
        self.global_budget = Budget(root, settings.total_storage_gb * 1024**3)
        self.run_slots = threading.BoundedSemaphore(settings.total_runs)
        self.entries = {}
        self.lock = asyncio.Lock()
        self.sockets = {}

    def reserve(self, entry, amount):
        global_release = self.global_budget.reserve(amount)
        try:
            local_release = entry["budget"].reserve(amount)
        except BaseException:
            global_release()
            raise

        def release():
            local_release()
            global_release()

        return release

    async def get(self, identifier):
        async with self.lock:
            if identifier not in self.entries:
                root = self.root / "users" / identifier
                root.mkdir(parents=True, exist_ok=True, mode=0o700)
                entry = {
                    "budget": Budget(root, self.settings.user_storage_gb * 1024**3),
                    "references": 0,
                }

                def admit():
                    if not self.accounts.may_run(identifier):
                        raise HTTPException(403, "账号已停用或需要修改密码")
                    if not self.run_slots.acquire(blocking=False):
                        raise RunCapacityError(
                            "全站实验并发已满，请稍后重试；批量任务会继续排队"
                        )
                    try:
                        release_storage = self.reserve(entry, 256 * MIB)
                    except BaseException:
                        self.run_slots.release()
                        raise
                    released = False
                    release_lock = threading.Lock()

                    def release():
                        nonlocal released
                        with release_lock:
                            if not released:
                                released = True
                                release_storage()
                                self.run_slots.release()

                    return release

                manager = RunManager(
                    root,
                    max_active=self.settings.user_runs,
                    worker_factory=self.worker_factory,
                    admit=admit,
                    wall_timeout_s=self.settings.wall_timeout_s,
                )
                app = create_app(
                    root,
                    run_manager=manager,
                    benchmark_limit_bytes=32 * MIB,
                    hosted=True,
                )

                @app.exception_handler(RunCapacityError)
                async def capacity_error(request, error):
                    return JSONResponse({"detail": str(error)}, 429)

                context = app.router.lifespan_context(app)
                await context.__aenter__()
                entry.update(
                    app=app, context=context, manager=manager, used=time.monotonic()
                )
                self.entries[identifier] = entry
            entry = self.entries[identifier]
            entry["references"] += 1
            entry["used"] = time.monotonic()
            return entry

    async def stop(self, identifier):
        async with self.lock:
            entry = self.entries.get(identifier)
            if entry:
                batches = entry["app"].state.benchmarks
                for batch in list(batches.batches.values()):
                    if batch["state"] not in TERMINAL:
                        await asyncio.to_thread(batches.cancel, batch["id"])
                await asyncio.to_thread(entry["manager"].close)

    async def collect(self):
        async with self.lock:
            for identifier, entry in list(self.entries.items()):
                if entry["references"] or time.monotonic() - entry["used"] < 300:
                    continue
                if any(run.thread.is_alive() for run in entry["manager"].runs.values()):
                    continue
                if any(
                    batch["state"] not in TERMINAL
                    for batch in entry["app"].state.benchmarks.batches.values()
                ):
                    continue
                await entry["context"].__aexit__(None, None, None)
                del self.entries[identifier]

    async def close(self):
        async with self.lock:
            for entry in self.entries.values():
                await entry["context"].__aexit__(None, None, None)
            self.entries.clear()

    async def __call__(self, scope, receive, send):
        websocket = scope["type"] == "websocket"
        token = session_token(scope)
        user = await asyncio.to_thread(self.accounts.authenticate, token)
        if not user or user["must_change_password"]:
            if websocket:
                return await send({"type": "websocket.close", "code": 4401})
            return await JSONResponse({"detail": "请先登录并完成密码修改"}, 401)(
                scope, receive, send
            )
        identifier = user["id"]
        owner = Headers(scope=scope).get("x-pathlab-user")
        if websocket:
            owner = QueryParams(scope.get("query_string", b"")).get("owner") or owner
        if owner and owner != identifier:
            if websocket:
                return await send({"type": "websocket.close", "code": 4401})
            return await JSONResponse(
                {"detail": "当前浏览器账号已切换，请刷新工作区"}, 401
            )(scope, receive, send)
        if websocket:
            if (
                Headers(scope=scope).get("origin") != self.settings.public_url
                or self.sockets.get(identifier, 0) >= 4
            ):
                return await send({"type": "websocket.close", "code": 4403})
            self.sockets[identifier] = self.sockets.get(identifier, 0) + 1
        entry = None
        release = None
        try:
            entry = await self.get(identifier)
            if not websocket:
                await asyncio.to_thread(
                    self.accounts.throttle, "api:" + identifier, 1800, 60
                )
            path = scope["path"]
            if scope.get("method") == "POST":
                amount = {
                    "/api/submissions": 160 * MIB,
                    "/api/sources": 192 * MIB,
                    "/api/maps": 16 * MIB,
                    "/api/benchmarks": 64 * MIB,
                }.get(path)
                if amount:
                    release = await asyncio.to_thread(self.reserve, entry, amount)
            last_check = 0.0
            last_message = 0.0

            async def checked_receive():
                nonlocal last_check, last_message
                message = await receive()
                if websocket and message["type"] == "websocket.receive":
                    now = time.monotonic()
                    # Pull snapshots at at most 30 Hz, without building a frame queue.
                    await asyncio.sleep(max(0, 1 / 30 - (now - last_message)))
                    last_message = time.monotonic()
                    if len(message.get("text") or message.get("bytes") or b"") > 1024:
                        await send({"type": "websocket.close", "code": 1009})
                        return {"type": "websocket.disconnect", "code": 1009}
                    if now - last_check >= 1:
                        last_check = now
                        if not await asyncio.to_thread(
                            self.accounts.authenticate, token
                        ):
                            await send({"type": "websocket.close", "code": 4401})
                            return {"type": "websocket.disconnect", "code": 4401}
                return message

            await entry["app"](scope, checked_receive, send)
        except HTTPException as error:
            if websocket:
                await send({"type": "websocket.close", "code": 4403})
            else:
                await JSONResponse(
                    {"detail": error.detail}, error.status_code, headers=error.headers
                )(scope, receive, send)
        finally:
            if release:
                release()
            if entry:
                entry["references"] -= 1
                entry["used"] = time.monotonic()
            if websocket:
                self.sockets[identifier] -= 1


def create_portal(
    root: Path, settings: HostingSettings, *, worker_factory=None
) -> FastAPI:
    root = root.expanduser().resolve()
    accounts = Accounts(root, max_users=settings.max_users)
    sandbox = worker_factory or DockerSandbox(root, settings.worker_image)
    workspaces = Workspaces(root, accounts, settings, sandbox)

    @asynccontextmanager
    async def lifespan(app):
        with (root / ".server.lock").open("a") as lock:
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as error:
                raise RuntimeError(
                    "同一公网数据目录只能启动一个服务进程；不要使用多个 uvicorn worker"
                ) from error
            if not any(
                user["role"] == "admin" and user["enabled"] for user in accounts.users()
            ):
                raise RuntimeError("请先使用 python run.py create-admin 创建管理员")
            if hasattr(sandbox, "preflight"):
                await asyncio.to_thread(sandbox.preflight)

            async def collect():
                while True:
                    await asyncio.sleep(60)
                    await workspaces.collect()

            task = asyncio.create_task(collect())
            try:
                yield
            finally:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
                await workspaces.close()

    app = FastAPI(
        title="寻迹实验室 · 多人平台",
        lifespan=lifespan,
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )
    app.state.accounts, app.state.workspaces = accounts, workspaces
    app.add_middleware(
        TrustedHostMiddleware, allowed_hosts=[urlsplit(settings.public_url).hostname]
    )
    app.add_middleware(RequestGuard, origin=settings.public_url)

    @app.exception_handler(ValueError)
    async def invalid(request, error):
        return JSONResponse({"detail": str(error)}, 400)

    def current(request, *, admin=False):
        user = accounts.authenticate(request.cookies.get(COOKIE))
        if not user:
            raise HTTPException(401, "请先登录")
        owner = request.headers.get("x-pathlab-user")
        if owner and owner != user["id"]:
            raise HTTPException(401, "当前浏览器账号已切换，请刷新工作区")
        if admin and (user["role"] != "admin" or user["must_change_password"]):
            raise HTTPException(403, "需要管理员权限")
        return user

    @app.get("/api/health")
    def health():
        return {"status": "ok", "mode": "multi_user"}

    @app.get("/api/auth/me")
    def me(request: Request):
        return {
            "enabled": True,
            "user": accounts.authenticate(request.cookies.get(COOKIE)),
            "registration": "invitation",
            "limits": {
                "user_runs": settings.user_runs,
                "total_runs": settings.total_runs,
                "user_storage_gb": settings.user_storage_gb,
            },
        }

    @app.post("/api/auth/login")
    def login(request: Request, data: Credentials):
        address = request.client.host if request.client else "unknown"
        # A whole classroom can share one NAT address; individual accounts
        # retain a much tighter limit below.
        accounts.throttle("login-ip:" + address, 120, 300)
        accounts.throttle("login-user:" + token_hash(data.username.lower()), 10, 900)
        token, user = accounts.login(data.username, data.password)
        # Replacing a browser's account also invalidates its previous live sockets.
        accounts.logout(request.cookies.get(COOKIE, ""))
        response = JSONResponse({"user": user})
        response.set_cookie(
            COOKIE,
            token,
            max_age=accounts.session_seconds,
            httponly=True,
            secure=settings.secure,
            samesite="lax",
            path="/",
        )
        return response

    @app.post("/api/auth/register", status_code=201)
    def register(request: Request, data: Registration):
        accounts.throttle(
            "register:" + (request.client.host if request.client else "unknown"),
            120,
            600,
        )
        return {
            "user": accounts.create(
                data.username,
                data.password,
                data.display_name,
                invitation=data.invitation,
            )
        }

    @app.post("/api/auth/logout")
    def logout(request: Request):
        accounts.logout(request.cookies.get(COOKIE, ""))
        response = JSONResponse({"ok": True})
        response.delete_cookie(
            COOKIE, path="/", secure=settings.secure, httponly=True, samesite="lax"
        )
        return response

    @app.post("/api/auth/password")
    def change_password(request: Request, data: PasswordChange):
        user = current(request)
        accounts.throttle("password:" + user["id"], 5, 300)
        accounts.change_password(user["id"], data.old_password, data.new_password)
        return {"ok": True, "message": "密码已修改，请重新登录"}

    @app.get("/api/account/workspace")
    def workspace(request: Request):
        user = current(request)
        folder = root / "users" / user["id"]
        return {
            "used_bytes": directory_bytes(folder),
            "limit_bytes": settings.user_storage_gb * 1024**3,
            "user_runs": settings.user_runs,
            "total_runs": settings.total_runs,
        }

    @app.get("/api/admin/users")
    def users(request: Request):
        current(request, admin=True)
        return [
            {**user, "used_bytes": directory_bytes(root / "users" / user["id"])}
            for user in accounts.users()
        ]

    @app.post("/api/admin/users", status_code=201)
    def create_user(request: Request, data: NewUser):
        actor = current(request, admin=True)
        return accounts.create(
            data.username,
            data.password,
            data.display_name,
            actor=actor["id"],
            must_change=True,
        )

    @app.patch("/api/admin/users/{identifier}")
    async def update_user(request: Request, identifier: str, data: UserState):
        actor = await asyncio.to_thread(current, request, admin=True)
        user = await asyncio.to_thread(
            accounts.update, identifier, actor=actor["id"], enabled=data.enabled
        )
        if not data.enabled:
            await workspaces.stop(identifier)
        return user

    @app.post("/api/admin/users/{identifier}/reset-password")
    def reset_password(request: Request, identifier: str):
        actor = current(request, admin=True)
        password = secrets.token_urlsafe(18)
        accounts.update(identifier, actor=actor["id"], reset_password=password)
        return {"temporary_password": password}

    @app.post("/api/admin/users/{identifier}/stop")
    async def stop_user(request: Request, identifier: str):
        await asyncio.to_thread(current, request, admin=True)
        await workspaces.stop(identifier)
        return {"ok": True}

    @app.post("/api/admin/invitations")
    def invite(request: Request, data: Invitation):
        actor = current(request, admin=True)
        return {
            "code": accounts.invite(actor["id"], data.uses, data.days),
            "uses": data.uses,
            "days": data.days,
        }

    @app.get("/api/admin/audit")
    def audit(request: Request):
        current(request, admin=True)
        return accounts.events()

    @app.get("/api/admin/invitations")
    def invitations(request: Request):
        current(request, admin=True)
        return accounts.invitations()

    @app.delete("/api/admin/invitations/{identifier}")
    def revoke_invitation(request: Request, identifier: str):
        actor = current(request, admin=True)
        accounts.revoke_invitation(identifier, actor["id"])
        return {"ok": True}

    dist = ROOT / "frontend/dist"
    if (dist / "assets").is_dir():
        app.mount("/assets", StaticFiles(directory=dist / "assets"))

    @app.get("/")
    def index():
        return FileResponse(dist / "index.html")

    app.mount("/", workspaces)
    return app
