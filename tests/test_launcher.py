"""Switching source branches must not serve an incompatible cached student UI."""

import os

import run as launcher


def test_frontend_rebuilds_once_after_source_change(tmp_path, monkeypatch):
    frontend = tmp_path / "frontend"
    source = frontend / "src" / "App.tsx"
    source.parent.mkdir(parents=True)
    source.write_text("new branch")
    entry = frontend / "dist" / "index.html"
    entry.parent.mkdir()
    entry.write_text("old student bundle")
    (frontend / "node_modules").mkdir()
    os.utime(entry, (100, 100))
    os.utime(source, (200, 200))
    monkeypatch.setattr(launcher, "ROOT", tmp_path)
    monkeypatch.setattr(launcher.shutil, "which", lambda *a, **k: "/test/npm")
    builds = []

    def build(command, **kwargs):
        assert command == ["/test/npm", "run", "build"]
        assert kwargs["cwd"] == frontend and kwargs["check"]
        builds.append(command)
        entry.write_text("current full UI")

    monkeypatch.setattr(launcher.subprocess, "run", build)
    launcher.ensure_frontend()
    launcher.ensure_frontend()
    assert len(builds) == 1
    assert entry.read_text() == "current full UI"
