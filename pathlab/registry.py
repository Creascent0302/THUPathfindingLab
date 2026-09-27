"""Uploaded student plugins and locations shared by source and native builds."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from pydantic import Field, model_validator

from .config import Model
from .sdk import Capability

FROZEN = getattr(sys, "frozen", False)
ROOT = Path(sys._MEIPASS) if FROZEN else Path(__file__).resolve().parent.parent
DATA_ROOT = (Path(sys.executable).parent if FROZEN else ROOT) / "artifacts"


class PluginSpec(Model):
    id: str = Field(pattern=r"^[a-z][a-z0-9_-]{0,63}$")
    name: str
    version: str
    capabilities: list[Capability]
    entrypoint: str | None = None
    command: list[str] | None = None
    description: str = ""
    working_directory: str | None = None
    submission_sha256: str | None = None

    @model_validator(mode="after")
    def implementation(self):
        if (self.entrypoint is None) == (self.command is None):
            raise ValueError("须且只能配置 entrypoint 或 command")
        return self

    def argv(self) -> list[str]:
        if self.entrypoint:
            if FROZEN:
                return [sys.executable, "--worker", self.entrypoint]
            return [sys.executable, "-m", "pathlab.worker", "--plugin", self.entrypoint]
        if FROZEN and "{python}" in (self.command or []):
            raise ValueError(
                "发行包请使用 StudentAlgorithm 类接口；外部命令须指定独立解释器"
            )
        return [part.replace("{python}", sys.executable) for part in self.command or []]


def registry(
    path: Path | None = None, *, artifact_root: Path | None = None
) -> dict[str, PluginSpec]:
    # Explicit manifests support framework tests and external protocol clients.
    # A new student installation has no preinstalled algorithms.
    rows = json.loads(path.read_text(encoding="utf-8")) if path else []
    specs = [PluginSpec.model_validate(row) for row in rows]
    for manifest in ((artifact_root or DATA_ROOT) / "submissions").glob(
        "upload_*/plugin.json"
    ):
        spec = PluginSpec.model_validate_json(manifest.read_text(encoding="utf-8"))
        code = manifest.parent / "code"
        entries = [
            p
            for p in [code, *code.iterdir()]
            if p.is_dir() and (p / "algorithm.py").is_file()
        ]
        if len(entries) != 1:
            raise ValueError(f"提交 {spec.name} 的 algorithm.py 缺失或不唯一")
        # Rebind to this installation when a student moves their data folder.
        spec.working_directory = str(entries[0].resolve())
        specs.append(spec)
    if len({p.id for p in specs}) != len(specs):
        raise ValueError("算法 id 不得重复")
    return {p.id: p for p in specs}
