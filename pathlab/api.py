"""Single local HTTP service serving both API and built React UI."""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
import json
import os
from pathlib import Path
import re
import shutil
import threading
import uuid

from fastapi import (
    FastAPI,
    File,
    Form,
    HTTPException,
    Request,
    UploadFile,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles

from .config import RunConfig, Scene
from .engine import RunManager, TERMINAL
from .map_editor import MapRequest, build_scene, geometry_summary
from .registry import ROOT, registry
from .scenarios import FAMILIES, generate, validate_scene
from .sdk import Action, Capability, Model, encode_png
from .simulation import Pose, Renderer
from .sources import MAX_UPLOAD_BYTES, import_media
from .storage import export_csv, read_records, write_json
from .submissions import MAX_ARCHIVE_BYTES, import_submission, template_zip


class Control(Model):
    command: str


def process_exists(pid: int) -> bool:
    if os.name == "nt":
        import ctypes
        from ctypes import wintypes

        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        kernel.OpenProcess.restype = wintypes.HANDLE
        kernel.GetExitCodeProcess.argtypes = [
            wintypes.HANDLE,
            ctypes.POINTER(wintypes.DWORD),
        ]
        kernel.CloseHandle.argtypes = [wintypes.HANDLE]
        handle = kernel.OpenProcess(0x1000, False, pid)
        if not handle:
            return (
                ctypes.get_last_error() == 5
            )  # Access denied means it may still exist.
        try:
            code = wintypes.DWORD()
            return (
                not kernel.GetExitCodeProcess(handle, ctypes.byref(code))
                or code.value == 259
            )
        finally:
            kernel.CloseHandle(handle)
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True


def create_app(artifact_root: Path | None = None) -> FastAPI:
    root = artifact_root or ROOT / "artifacts"
    manager = RunManager(root)
    submission_lock = threading.Lock()
    scene_lock = threading.Lock()

    @asynccontextmanager
    async def lifespan(app):
        for manifest_path in (root / "runs").glob("*/manifest.json"):
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            if manifest["state"] in TERMINAL:
                continue
            if not manifest.get("owner_pid") or not process_exists(
                manifest["owner_pid"]
            ):
                manifest.update(
                    state="failed",
                    failures=[
                        {
                            "kind": "server_restart",
                            "message": "服务在上次实验期间退出；已有帧仍可回放",
                        }
                    ],
                )
                write_json(manifest_path, manifest)
        yield
        await asyncio.to_thread(manager.close)

    app = FastAPI(title="寻迹实验室 API", version="0.1.0", lifespan=lifespan)
    app.state.manager = manager

    @app.exception_handler(ValueError)
    async def value_error_handler(request: Request, error: ValueError):
        return JSONResponse(status_code=400, content={"detail": str(error)})

    @app.exception_handler(FileNotFoundError)
    async def missing_file_handler(request: Request, error: FileNotFoundError):
        return JSONResponse(
            status_code=404, content={"detail": "记录或素材已被删除，请刷新列表"}
        )

    def directory(run_id: str) -> Path:
        if not re.fullmatch(r"[0-9a-f]{32}", run_id):
            raise HTTPException(404, "运行不存在")
        path = root / "runs" / run_id
        if not (path / "manifest.json").is_file():
            raise HTTPException(404, "运行不存在")
        return path

    def live(run_id):
        if run_id not in manager.runs:
            raise HTTPException(404, "实时任务不存在；已保存的任务可从结果列表回放")
        return manager.runs[run_id]

    @app.get("/api/health")
    def health():
        return {"status": "ok", "protocol_version": "1.0"}

    @app.get("/api/catalog")
    def catalog():
        return {
            "algorithms": [
                {
                    "id": "manual",
                    "name": "手动驾驶",
                    "version": "1.0",
                    "capabilities": ["action"],
                    "description": "用方向键或滑块驾驶；松开方向键回正，空格制动。",
                },
                *[
                    {
                        **spec.model_dump(),
                        "available": spec.unavailable_reason() is None,
                        "unavailable_reason": spec.unavailable_reason(),
                    }
                    for spec in registry(artifact_root=root).values()
                ],
            ],
            "families": FAMILIES,
            "limits": {
                "active_runs": 3,
                "upload_mb": 32,
                "source_frames": 600,
                "run_steps": 6000,
            },
        }

    def preview_data(generated: Scene):
        renderer = Renderer(generated)
        return {
            "scene": generated.model_dump(),
            "image": encode_png(renderer.render(generated.initial_pose, 0)),
            "calibration": renderer.camera.calibration().model_dump(),
            "geometry": geometry_summary(generated),
        }

    @app.get("/api/scenes/{family}")
    def scene(family: str, seed: int = 7):
        return preview_data(generate(family, seed))

    @app.post("/api/maps/build")
    def map_build(request: MapRequest):
        return preview_data(build_scene(request))

    @app.get("/api/maps")
    def saved_maps():
        return [
            {"id": path.stem, "scene": json.loads(path.read_text(encoding="utf-8"))}
            for path in sorted((root / "maps").glob("*.json"))
        ]

    @app.post("/api/maps", status_code=201)
    def save_map(scene: Scene):
        errors = validate_scene(scene)
        if errors:
            raise ValueError("；".join(errors))
        with scene_lock:
            folder = root / "maps"
            folder.mkdir(parents=True, exist_ok=True)
            if len(list(folder.glob("*.json"))) >= 100:
                raise HTTPException(409, "最多保存 100 张地图，请先删除不需要的地图")
            identifier = uuid.uuid4().hex
            write_json(folder / f"{identifier}.json", scene.model_dump())
        return {"id": identifier, "scene": scene.model_dump()}

    @app.delete("/api/maps/{map_id}")
    def delete_map(map_id: str):
        if not re.fullmatch(r"[0-9a-f]{32}", map_id):
            raise HTTPException(404, "地图不存在")
        with scene_lock:
            path = root / "maps" / f"{map_id}.json"
            if not path.is_file():
                raise HTTPException(404, "地图不存在")
            path.unlink()
        return {"deleted": map_id}

    @app.get("/api/submissions/template")
    def submission_template():
        return Response(
            template_zip(),
            media_type="application/zip",
            headers={
                "Content-Disposition": 'attachment; filename="student-algorithm.zip"',
            },
        )

    @app.post("/api/submissions", status_code=201)
    async def upload_algorithm(
        file: UploadFile = File(...),
        name: str = Form("上传算法", max_length=80),
        capability: Capability = Form("action"),
    ):
        try:
            raw = await file.read(MAX_ARCHIVE_BYTES + 1)
        finally:
            await file.close()

        def install():
            with submission_lock:
                return import_submission(root, raw, name, capability).model_dump()

        return await asyncio.to_thread(install)

    @app.post("/api/scenes/validate")
    def scene_validation(scene: Scene):
        return {"errors": validate_scene(scene)}

    @app.post("/api/preview")
    def preview(scene: Scene):
        errors = validate_scene(scene)
        if errors:
            raise ValueError("; ".join(errors))
        return preview_data(scene)

    @app.post("/api/sources")
    async def sources(files: list[UploadFile] = File(...), fps: float = Form(20)):
        if len(files) > 600:
            raise HTTPException(413, "最多 600 个文件")
        total, contents = 0, []
        for file in files:
            parts = []
            while chunk := await file.read(1024 * 1024):
                total += len(chunk)
                if total > MAX_UPLOAD_BYTES:
                    raise HTTPException(413, "上传合计超过 32 MiB")
                parts.append(chunk)
            contents.append((file.filename or "image.png", b"".join(parts)))
            await file.close()
        if len(list((root / "uploads").glob("*/source.json"))) >= 50:
            raise HTTPException(409, "已有 50 份素材，请归档并清理 artifacts/uploads")
        return await asyncio.to_thread(import_media, root, contents, fps)

    @app.get("/api/sources/{source_id}/preview")
    def source_preview(source_id: str):
        from .sources import read_source

        try:
            source = read_source(root, source_id)
        except FileNotFoundError:
            raise HTTPException(404, "素材不存在")
        image = (root / "uploads" / source_id / "000000.png").read_bytes()
        import base64

        return {
            "source": source,
            "image": base64.b64encode(image).decode(),
            "scene": None,
            "calibration": None,
        }

    @app.post("/api/runs", status_code=201)
    def create_run(config: RunConfig):
        try:
            return manager.create(config).snapshot()
        except FileNotFoundError:
            raise HTTPException(404, "素材不存在")

    @app.get("/api/runs/{run_id}")
    def get_run(run_id: str):
        return live(run_id).snapshot()

    @app.post("/api/runs/{run_id}/control")
    def control_run(run_id: str, control: Control):
        run = live(run_id)
        run.control(control.command)
        return {"state": run.state, "paused": run.paused}

    @app.post("/api/runs/{run_id}/action")
    def manual_action(run_id: str, action: Action):
        live(run_id).set_action(action)
        return {"accepted": True}

    @app.websocket("/api/runs/{run_id}/stream")
    async def stream(websocket: WebSocket, run_id: str):
        await websocket.accept()
        if run_id not in manager.runs:
            await websocket.close(code=1008)
            return
        run = manager.runs[run_id]
        try:
            # Request/response pull: at most one snapshot is in flight. No image queue.
            while True:
                await asyncio.wait_for(websocket.receive_text(), timeout=15)
                await websocket.send_json(run.snapshot())
        except (WebSocketDisconnect, asyncio.TimeoutError, RuntimeError):
            return

    @app.get("/api/results")
    def results():
        with manager.lock:
            manifests = sorted(
                (root / "runs").glob("*/manifest.json"),
                key=lambda p: p.stat().st_mtime,
                reverse=True,
            )[:200]
            return [json.loads(path.read_text(encoding="utf-8")) for path in manifests]

    @app.get("/api/results/{run_id}")
    def result(run_id: str):
        folder = directory(run_id)
        manifest = json.loads((folder / "manifest.json").read_text(encoding="utf-8"))
        return {"manifest": manifest, "frames": read_records(folder)}

    @app.delete("/api/results/{run_id}")
    def delete_result(run_id: str):
        with manager.lock:
            folder = directory(run_id)
            run = manager.runs.get(run_id)
            manifest = json.loads(
                (folder / "manifest.json").read_text(encoding="utf-8")
            )
            if (run and run.thread.is_alive()) or manifest["state"] not in TERMINAL:
                raise HTTPException(409, "运行尚未结束，请先停止实验再删除")
            shutil.rmtree(folder)
            manager.runs.pop(run_id, None)
        return {"deleted": run_id}

    @app.get("/api/results/{run_id}/frames/{frame_id}")
    def replay(run_id: str, frame_id: int):
        folder = directory(run_id)
        manifest = json.loads((folder / "manifest.json").read_text(encoding="utf-8"))
        rows = read_records(folder)
        if not 0 <= frame_id < len(rows):
            raise HTTPException(404, "帧不存在")
        row = rows[frame_id]
        stored_image = folder / "images" / f"{frame_id:06d}.png"
        import base64

        if stored_image.exists():
            image = base64.b64encode(stored_image.read_bytes()).decode()
        elif manifest["scene"]:
            simulator = Renderer(Scene.model_validate(manifest["scene"]))
            pose = Pose.model_validate(
                {k: row["pose_before"][k] for k in ("x_m", "y_m", "yaw_rad")}
            )
            image = encode_png(simulator.render(pose, row["frame_id"]))
        else:
            source_path = (
                root
                / "uploads"
                / manifest["config"]["source_id"]
                / f"{frame_id:06d}.png"
            )
            if not source_path.exists():
                raise HTTPException(404, "回放素材已被删除")
            image = base64.b64encode(source_path.read_bytes()).decode()
        calibration = (
            Renderer(Scene.model_validate(manifest["scene"]))
            .camera.calibration()
            .model_dump()
            if manifest["scene"]
            else None
        )
        return {
            "id": run_id,
            "state": manifest["state"],
            "paused": True,
            "frame_count": len(rows),
            "frame": row,
            "image": image,
            "scene": manifest["scene"],
            "config": manifest["config"],
            "metrics": manifest["metrics"],
            "failures": manifest["failures"],
            "logs": ["结果回放：直接读取已保存输出，不重新调用算法。"],
            "history": [
                {
                    k: r.get(k)
                    for k in (
                        "frame_id",
                        "timestamp_s",
                        "pose",
                        "applied",
                        "evaluation",
                        "inference_ms",
                    )
                }
                for r in rows[max(0, frame_id - 239) : frame_id + 1]
            ],
            "calibration": calibration,
            "reason": (manifest["metrics"] or {}).get("reason"),
        }

    @app.get("/api/results/{run_id}/export/{format}")
    def export(run_id: str, format: str):
        folder = directory(run_id)
        if format == "json":
            data = {
                "manifest": json.loads(
                    (folder / "manifest.json").read_text(encoding="utf-8")
                ),
                "frames": read_records(folder),
            }
            content, media = (
                json.dumps(data, ensure_ascii=False, allow_nan=False),
                "application/json",
            )
        elif format == "csv":
            content, media = "\ufeff" + export_csv(read_records(folder)), "text/csv"
        else:
            raise HTTPException(404, "仅支持 json 和 csv")
        return Response(
            content,
            media_type=media,
            headers={
                "Content-Disposition": f'attachment; filename="run-{run_id[:8]}.{format}"'
            },
        )

    dist = ROOT / "frontend" / "dist"
    if (dist / "assets").exists():
        app.mount("/assets", StaticFiles(directory=dist / "assets"), name="assets")

    @app.get("/")
    def index():
        if not (dist / "index.html").exists():
            return JSONResponse(
                status_code=503,
                content={"detail": "前端尚未构建，请运行 python scripts/setup.py"},
            )
        return FileResponse(dist / "index.html")

    return app
