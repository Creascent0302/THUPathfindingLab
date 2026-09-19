"""A local allowlist. New plugins need only an entry in algorithms.json."""

from __future__ import annotations

import json
import importlib.util
import sys
from pathlib import Path

from pydantic import Field, model_validator

from .sdk import Capability, Model

ROOT = Path(__file__).resolve().parent.parent


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
    runtime_requirements: list[str] = Field(default_factory=list)
    checkpoint_file: str | None = None

    @model_validator(mode="after")
    def implementation(self):
        if (self.entrypoint is None) == (self.command is None):
            raise ValueError("须且只能配置 entrypoint 或 command")
        return self

    def argv(self) -> list[str]:
        if self.entrypoint:
            return [sys.executable, "-m", "pathlab.worker", "--plugin", self.entrypoint]
        return [part.replace("{python}", sys.executable) for part in self.command or []]

    def unavailable_reason(self) -> str | None:
        if any(
            importlib.util.find_spec(name) is None for name in self.runtime_requirements
        ):
            return "缺少学习依赖，请运行 python scripts/setup_learning.py"
        if self.checkpoint_file and not (ROOT / self.checkpoint_file).is_file():
            return "缺少训练权重，请先运行 python run.py learning fit"
        return None


def registry(
    path: Path | None = None, *, artifact_root: Path | None = None
) -> dict[str, PluginSpec]:
    rows = json.loads((path or ROOT / "algorithms.json").read_text(encoding="utf-8"))
    specs = [PluginSpec.model_validate(row) for row in rows]
    for manifest in ((artifact_root or ROOT / "artifacts") / "submissions").glob(
        "upload_*/plugin.json"
    ):
        specs.append(
            PluginSpec.model_validate_json(manifest.read_text(encoding="utf-8"))
        )
    if len({p.id for p in specs}) != len(specs):
        raise ValueError("算法 id 不得重复")
    return {p.id: p for p in specs}
