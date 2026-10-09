"""Installation must stay local and fail clearly before starting the server."""

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

from scripts import setup


def test_environment_is_created_locally_and_reused(tmp_path, monkeypatch):
    monkeypatch.setattr(setup, "ROOT", tmp_path)
    python = setup.prepare_environment()
    config = tmp_path / ".venv/pyvenv.cfg"
    timestamp = config.stat().st_mtime_ns
    assert setup.prepare_environment() == python
    assert config.stat().st_mtime_ns == timestamp
    details = json.loads(
        subprocess.check_output(
            [
                str(python),
                "-I",
                "-c",
                "import json, sys; print(json.dumps([sys.prefix, sys.base_prefix]))",
            ],
            text=True,
        )
    )
    assert Path(details[0]) == tmp_path / ".venv"
    assert details[0] != details[1]


def test_invalid_environment_is_preserved(tmp_path, monkeypatch):
    monkeypatch.setattr(setup, "ROOT", tmp_path)
    environment = tmp_path / ".venv"
    environment.mkdir()
    sentinel = environment / "keep.txt"
    sentinel.write_text("do not delete")
    with pytest.raises(SystemExit, match="现有 .venv 不可用"):
        setup.prepare_environment()
    assert sentinel.read_text() == "do not delete"


def test_headless_setup_cannot_start_web_server(tmp_path, monkeypatch):
    monkeypatch.setattr(setup, "ROOT", tmp_path)
    with pytest.raises(SystemExit) as error:
        setup.main(["--run", "--skip-frontend"])
    assert error.value.code == 2
    assert not (tmp_path / ".venv").exists()


def test_unsupported_macos_stops_before_install(tmp_path, monkeypatch):
    monkeypatch.setattr(setup, "ROOT", tmp_path)
    monkeypatch.setattr(setup.sys, "platform", "darwin")
    monkeypatch.setattr(setup.platform, "mac_ver", lambda: ("12.7.6", (), "arm64"))
    with pytest.raises(SystemExit, match="macOS 13"):
        setup.main([])
    assert not (tmp_path / ".venv").exists()


def test_failed_install_does_not_start_server(tmp_path, monkeypatch):
    monkeypatch.setattr(setup, "ROOT", tmp_path)
    monkeypatch.setattr(
        setup, "prepare_environment", lambda: tmp_path / ".venv/bin/python"
    )
    commands = []

    def fail_install(argv, **kwargs):
        commands.append(argv)
        if "install" in argv:
            raise subprocess.CalledProcessError(1, argv)

    monkeypatch.setattr(setup.subprocess, "run", fail_install)
    with pytest.raises(subprocess.CalledProcessError):
        setup.main(["--run"])
    assert not any(str(tmp_path / "run.py") in command for command in commands)


@pytest.mark.parametrize("system", ["Linux", "Darwin"])
def test_shell_bootstrap_selects_python_from_another_directory(tmp_path, system):
    project = tmp_path / "project with spaces"
    (project / "scripts").mkdir(parents=True)
    shutil.copy2(setup.ROOT / "setup.sh", project / "setup.sh")
    (project / "scripts/setup.py").write_text(
        "import json, os, sys\n"
        "print(json.dumps({'cwd': os.getcwd(), 'args': sys.argv[1:]}))\n"
    )
    binaries = tmp_path / "bin"
    binaries.mkdir()
    for name in ("dirname",):
        (binaries / name).symlink_to(shutil.which(name))
    uname = binaries / "uname"
    uname.write_text(f"#!/bin/sh\nprintf '%s\\n' '{system}'\n")
    uname.chmod(0o755)
    (binaries / "python3.13").symlink_to(sys.executable)
    # A common Mac/Linux case: the generic python3 command is incompatible.
    unsupported = binaries / "python3"
    unsupported.write_text("#!/bin/sh\nexit 1\n")
    unsupported.chmod(0o755)
    result = subprocess.run(
        [shutil.which("bash"), str(project / "setup.sh"), "--mirror", "--run"],
        cwd=tmp_path,
        env={**os.environ, "PATH": str(binaries)},
        text=True,
        capture_output=True,
        check=True,
    )
    assert json.loads(result.stdout) == {
        "cwd": str(project),
        "args": ["--mirror", "--run"],
    }
