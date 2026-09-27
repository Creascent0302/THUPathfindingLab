"""Portable, bounded workspaces for ephemeral online sessions.

Archives are data, never configuration for host commands or absolute paths.
The online API only snapshots quiescent workspaces and restores into an empty one.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import tempfile
import zipfile

from .config import RunConfig, Scene
from .registry import PluginSpec
from .storage import write_json

LIMIT = 128 * 1024**2
MAX_FILES = 12000
FOLDERS = {"maps", "runs", "uploads", "submissions", "benchmarks"}
FORMAT = "pathlab-workspace-v1"


def files(root: Path):
    result = []
    for name in sorted(FOLDERS):
        folder = root / name
        if folder.is_symlink():
            raise ValueError("工作区不能包含符号链接")
        for path in sorted(folder.rglob("*")):
            if path.is_symlink():
                raise ValueError("工作区不能包含符号链接")
            if (
                path.is_file()
                and not path.name.endswith(".tmp")
                and "__pycache__" not in path.parts
            ):
                result.append(path)
    if len(result) > MAX_FILES:
        raise ValueError("工作区文件过多，请清理历史记录")
    return result


def inventory(root: Path):
    items = files(root)
    sizes = [(p, p.stat()) for p in items]
    revision = hashlib.sha256()
    for path, info in sizes:
        revision.update(
            f"{path.relative_to(root)}:{info.st_size}:{info.st_mtime_ns}\n".encode()
        )
    return {
        "revision": revision.hexdigest(),
        "used_bytes": sum(s.st_size for _, s in sizes),
        "limit_bytes": LIMIT,
        "empty": not items,
    }


def export_workspace(root: Path, destination: Path):
    items = files(root)
    marker = json.dumps({"format": FORMAT})
    if sum(p.stat().st_size for p in items) + len(marker.encode()) > LIMIT:
        raise ValueError("临时工作区超过 128 MiB，请先删除不需要的记录或图像")
    with zipfile.ZipFile(
        destination, "w", zipfile.ZIP_DEFLATED, compresslevel=1
    ) as archive:
        archive.writestr("workspace.json", marker)
        for path in items:
            archive.write(path, path.relative_to(root).as_posix())


def _json(path):
    if path.stat().st_size > 8 * 1024**2:
        raise ValueError("工作区元数据文件过大")
    return json.loads(path.read_text(encoding="utf-8"))


def _validate(staging: Path, destination: Path):
    if _json(staging / "workspace.json") != {"format": FORMAT}:
        raise ValueError("不是当前版本的寻迹实验工作区")
    for path in (staging / "maps").glob("*.json"):
        if not re.fullmatch(r"[0-9a-f]{32}", path.stem):
            raise ValueError("地图编号无效")
        Scene.model_validate(_json(path))
    for folder in (staging / "runs").iterdir() if (staging / "runs").exists() else []:
        if not folder.is_dir() or not re.fullmatch(r"[0-9a-f]{32}", folder.name):
            raise ValueError("实验目录无效")
        data = _json(folder / "manifest.json")
        if data.get("episode_id") != folder.name or data.get("state") not in {
            "completed",
            "failed",
            "cancelled",
        }:
            raise ValueError("工作区只能恢复已结束的实验")
        RunConfig.model_validate(data["config"])
        if data.get("scene"):
            Scene.model_validate(data["scene"])
        if not (folder / "frames.jsonl").is_file():
            raise ValueError("实验缺少帧记录")
        data["owner_pid"] = None
        write_json(folder / "manifest.json", data)
    for path in (staging / "submissions").glob("*/plugin.json"):
        plugin = PluginSpec.model_validate(_json(path))
        if (
            not re.fullmatch(r"upload_[0-9a-f]{32}", path.parent.name)
            or plugin.id != path.parent.name
        ):
            raise ValueError("提交算法编号无效")
        code = path.parent / "code"
        entries = [
            p
            for p in [code, *code.iterdir()]
            if p.is_dir() and (p / "algorithm.py").is_file()
        ]
        if (
            len(entries) != 1
            or plugin.entrypoint != "algorithm:StudentAlgorithm"
            or plugin.command
        ):
            raise ValueError("仅可恢复通过上传接口提交的算法")
        plugin.working_directory = str(destination / entries[0].relative_to(staging))
        plugin.runtime_requirements = []
        plugin.checkpoint_file = None
        write_json(path, plugin.model_dump())
    for path in (staging / "uploads").glob("*/source.json"):
        if not re.fullmatch(r"[0-9a-f]{32}", path.parent.name):
            raise ValueError("素材编号无效")
        if _json(path).get("id") != path.parent.name:
            raise ValueError("素材编号与目录不一致")
    for path in (staging / "benchmarks").glob("*.json"):
        data = _json(path)
        if not re.fullmatch(r"[0-9a-f]{32}", path.stem) or data.get("id") != path.stem:
            raise ValueError("批次编号无效")
        if data.get("state") not in {"completed", "failed", "cancelled"}:
            raise ValueError("请先结束批量测试再保存工作区")


def restore_workspace(root: Path, source: Path):
    if files(root):
        raise ValueError("当前临时工作区非空；为避免覆盖，请结束会话后重新登录再恢复")
    if source.stat().st_size > LIMIT + 2 * 1024**2:
        raise ValueError("工作区压缩包过大")
    # Staging and destination are on the same bounded filesystem.
    staging = Path(tempfile.mkdtemp(prefix=".restore-", dir=root))
    installed = []
    try:
        with zipfile.ZipFile(source) as archive:
            members = archive.infolist()
            if len(members) > MAX_FILES + 1:
                raise ValueError("工作区文件数量超限")
            seen, total = set(), 0
            for item in members:
                path = PurePosixPath(item.filename)
                key = str(path).casefold()
                mode = item.external_attr >> 16
                if (
                    not path.parts
                    or path.is_absolute()
                    or ".." in path.parts
                    or "\\" in item.filename
                    or ":" in item.filename
                    or key in seen
                    or item.flag_bits & 1
                    or (stat.S_IFMT(mode) not in {0, stat.S_IFREG, stat.S_IFDIR})
                    or (path.parts[0] not in FOLDERS and str(path) != "workspace.json")
                ):
                    raise ValueError("工作区包含非法路径、链接或重复文件")
                seen.add(key)
                total += item.file_size
                if total > LIMIT:
                    raise ValueError("工作区解压后超过 128 MiB")
                target = staging.joinpath(*path.parts)
                if item.is_dir():
                    target.mkdir(parents=True, exist_ok=True)
                    continue
                target.parent.mkdir(parents=True, exist_ok=True)
                with archive.open(item) as incoming, target.open("xb") as outgoing:
                    count = 0
                    while chunk := incoming.read(64 * 1024):
                        count += len(chunk)
                        if count > item.file_size:
                            raise ValueError("解压数据超过声明大小")
                        outgoing.write(chunk)
        _validate(staging, root)
        for name in FOLDERS:
            folder = staging / name
            if folder.exists():
                current = root / name
                if current.exists():
                    current.rmdir()  # Empty only. Never replace existing user files.
                folder.rename(current)
                installed.append(current)
    except Exception:
        for folder in installed:
            shutil.rmtree(folder)
        raise
    finally:
        shutil.rmtree(staging, ignore_errors=True)
