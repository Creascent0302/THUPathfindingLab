"""Hosted algorithms run in disposable, resource-limited Docker containers."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import uuid

from .registry import ROOT, PluginSpec
from .worker import WorkerClient


class DockerWorker(WorkerClient):
    def __init__(self, spec, command, name):
        self.container_name = name
        super().__init__(spec, command=command, working_directory=ROOT)

    def request(self, method, payload, timeout):
        # Container creation shares the first initialize request's deadline.
        # Give cold starts time without weakening the per-frame algorithm limit.
        if method == "initialize":
            timeout = max(30, timeout)
        return super().request(method, payload, timeout)

    def kill(self):
        if self.closed:
            return
        try:
            super().kill()
        finally:
            # Killing the docker CLI alone does not stop its container.
            try:
                subprocess.run(
                    ["docker", "rm", "-f", self.container_name],
                    capture_output=True,
                    timeout=10,
                    check=False,
                )
            except (OSError, subprocess.TimeoutExpired):
                pass  # Label-based startup cleanup handles a temporarily unavailable daemon.


class DockerSandbox:
    def __init__(
        self, root: Path, image="pathlab-worker:local", *, memory_mb=512, cpus=1
    ):
        self.root, self.image = root.resolve(), image
        self.memory_mb, self.cpus = memory_mb, cpus
        self.label = (
            "pathlab.workspace="
            + hashlib.sha256(str(self.root).encode()).hexdigest()[:20]
        )

    def preflight(self):
        if not shutil.which("docker"):
            raise RuntimeError(
                "公网模式需要 Docker。请按 docs/hosting.md 构建算法镜像；不会降级为宿主机执行。"
            )
        try:
            info = json.loads(
                subprocess.check_output(
                    ["docker", "info", "--format", "{{json .}}"],
                    timeout=15,
                    stderr=subprocess.PIPE,
                )
            )
            if not all(
                (
                    info.get("MemoryLimit"),
                    info.get("PidsLimit"),
                    info.get("CPUCfsQuota", info.get("CpuCfsQuota")),
                )
            ):
                raise RuntimeError(
                    "Docker 未启用内存、进程数或 CPU 限制，请检查 cgroup 配置"
                )
            subprocess.run(
                ["docker", "image", "inspect", self.image],
                check=True,
                capture_output=True,
                timeout=15,
            )
            orphaned = subprocess.check_output(
                ["docker", "ps", "-aq", "--filter", f"label={self.label}"],
                timeout=15,
                text=True,
            ).split()
            if orphaned:
                subprocess.run(
                    ["docker", "rm", "-f", *orphaned],
                    check=True,
                    capture_output=True,
                    timeout=30,
                )
        except (OSError, subprocess.SubprocessError, ValueError) as error:
            raise RuntimeError(
                "无法使用 Docker 或算法镜像尚未构建，请检查 docs/hosting.md"
            ) from error

    def command(self, spec: PluginSpec):
        if spec.runtime_requirements:
            raise ValueError(
                "默认公网镜像未安装可选学习依赖，请选择普通算法或由教师构建匹配镜像"
            )
        name = "pathlab-worker-" + uuid.uuid4().hex
        command = [
            "docker",
            "run",
            "--rm",
            "--pull=never",
            "-i",
            "--init",
            "--name",
            name,
            "--label",
            self.label,
            "--network=none",
            "--read-only",
            "--cap-drop=ALL",
            "--security-opt=no-new-privileges",
            "--user=65534:65534",
            f"--memory={self.memory_mb}m",
            f"--memory-swap={self.memory_mb}m",
            f"--cpus={self.cpus}",
            "--pids-limit=64",
            "--ulimit=nofile=128:128",
            "--tmpfs=/tmp:rw,noexec,nosuid,size=64m,mode=1777",
            "--log-driver=none",
            "-e",
            "HOME=/tmp",
            "-e",
            "PYTHONDONTWRITEBYTECODE=1",
            "-e",
            "OMP_NUM_THREADS=1",
            "-e",
            "OPENBLAS_NUM_THREADS=1",
            "-e",
            "PYTHONUNBUFFERED=1",
            "-e",
            "PYTHONPATH=/app:/submission",
        ]
        if spec.working_directory:
            code = Path(spec.working_directory).resolve()
            if not code.is_relative_to(self.root / "users") or not code.is_dir():
                raise ValueError("算法目录不属于公网用户工作区")
            if any(path.is_symlink() for path in code.rglob("*")):
                raise ValueError("算法目录不允许符号链接")
            command.extend(
                [
                    "--mount",
                    f"type=bind,src={code},dst=/submission,readonly",
                    "--workdir=/submission",
                ]
            )
        else:
            command.append("--workdir=/app")
        if spec.entrypoint:
            if not re.fullmatch(r"[a-zA-Z_][\w.]*:[a-zA-Z_]\w*", spec.entrypoint):
                raise ValueError("算法入口无效")
            entry = ["python", "-m", "pathlab.worker", "--plugin", spec.entrypoint]
        else:
            entry = [
                "python" if part == "{python}" else part for part in spec.command or []
            ]
        return [*command, self.image, *entry], name

    def __call__(self, spec):
        command, name = self.command(spec)
        return DockerWorker(spec, command, name)
