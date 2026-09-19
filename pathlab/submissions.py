"""Bounded ZIP intake. Validation never imports or executes submitted code."""

from __future__ import annotations

import ast
import hashlib
import io
from pathlib import Path, PurePosixPath
import shutil
import stat
import tempfile
import uuid
import zipfile

from .registry import PluginSpec, ROOT
from .sdk import Capability
from .storage import write_json

MAX_ARCHIVE_BYTES = 32 * 1024**2
MAX_EXPANDED_BYTES = 128 * 1024**2
MAX_FILES = 512


def template_zip() -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.write(ROOT / "student_template" / "algorithm.py", "algorithm.py")
    return buffer.getvalue()


def import_submission(
    root: Path, raw: bytes, name: str, capability: Capability
) -> PluginSpec:
    if len(raw) > MAX_ARCHIVE_BYTES:
        raise ValueError("算法 ZIP 超过 32 MiB")
    parent = root / "submissions"
    parent.mkdir(parents=True, exist_ok=True)
    if len(list(parent.glob("*/plugin.json"))) >= 100:
        raise ValueError("最多保存 100 个算法包，请先由管理员归档")
    if (
        sum(path.stat().st_size for path in root.rglob("*") if path.is_file())
        >= 2 * 1024**3
    ):
        raise ValueError("artifacts 已达到 2 GiB，请先归档并清理")
    staging = Path(tempfile.mkdtemp(prefix=".upload-", dir=parent))
    identifier = "upload_" + uuid.uuid4().hex
    destination = parent / identifier
    try:
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            members = archive.infolist()
            if not members or len(members) > MAX_FILES:
                raise ValueError("ZIP 必须包含文件，且最多 512 个条目")
            total, seen = 0, set()
            for member in members:
                path = PurePosixPath(member.filename)
                mode = member.external_attr >> 16
                if (
                    path.is_absolute()
                    or ".." in path.parts
                    or "\\" in member.filename
                    or ":" in member.filename
                    or not path.parts
                    or stat.S_ISLNK(mode)
                    or member.flag_bits & 1
                ):
                    raise ValueError("ZIP 包含不允许的路径、符号链接或加密文件")
                key = str(path).casefold()
                if key in seen:
                    raise ValueError("ZIP 中存在重复路径")
                seen.add(key)
                total += member.file_size
                if total > MAX_EXPANDED_BYTES:
                    raise ValueError("ZIP 解压后超过 128 MiB")
                if member.is_dir():
                    continue
                if member.file_size > MAX_ARCHIVE_BYTES:
                    raise ValueError("单个文件不得超过 32 MiB")
                if path.parts[0] == "__MACOSX" or path.name == ".DS_Store":
                    continue
                target = staging / "code" / path
                target.parent.mkdir(parents=True, exist_ok=True)
                with archive.open(member) as source, target.open("xb") as output:
                    written = 0
                    while chunk := source.read(1024 * 1024):
                        written += len(chunk)
                        if written > member.file_size or written > MAX_ARCHIVE_BYTES:
                            raise ValueError("ZIP 文件实际大小与声明不符")
                        output.write(chunk)
                if path.suffix == ".py":
                    try:
                        compile(
                            target.read_bytes(), str(path), "exec", ast.PyCF_ONLY_AST
                        )
                    except (SyntaxError, ValueError) as error:
                        raise ValueError(f"Python 语法错误 {path}: {error}") from error
        code = staging / "code"
        candidates = [
            p
            for p in [code, *code.iterdir()]
            if p.is_dir() and (p / "algorithm.py").is_file()
        ]
        if len(candidates) != 1:
            raise ValueError("请在 ZIP 根目录或唯一的一层文件夹内提供 algorithm.py")
        entry = candidates[0]
        tree = ast.parse((entry / "algorithm.py").read_bytes())
        classes = [
            node
            for node in tree.body
            if isinstance(node, ast.ClassDef) and node.name == "StudentAlgorithm"
        ]
        if not classes:
            raise ValueError(
                "algorithm.py 需要定义 StudentAlgorithm 类，请使用下载的模板"
            )
        # Give every upload its own version directory and original ZIP digest.
        relative = entry.relative_to(staging)
        spec = PluginSpec(
            id=identifier,
            name=name.strip() or "上传算法",
            version="1.0",
            capabilities=[capability],
            entrypoint="algorithm:StudentAlgorithm",
            description="已上传的学生算法",
            working_directory=str((destination / relative).resolve()),
            submission_sha256=hashlib.sha256(raw).hexdigest(),
        )
        write_json(staging / "plugin.json", spec.model_dump())
        staging.rename(destination)
        return spec
    except (zipfile.BadZipFile, RuntimeError, NotImplementedError, OSError) as error:
        raise ValueError(f"无法读取算法 ZIP：{error}") from error
    finally:
        if staging.exists():
            shutil.rmtree(staging)
