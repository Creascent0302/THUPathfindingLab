import time

import pytest

from pathlab.engine import Run
from pathlab.config import RunConfig


def wait_until(predicate, timeout=10):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return
        time.sleep(0.015)
    raise AssertionError("等待条件超时")


@pytest.fixture
def execute(tmp_path, test_plugins):
    runs = []

    def run(config=None, *, spec=None):
        instance = Run(
            config or RunConfig(algorithm="constant", max_steps=6, realtime=False),
            tmp_path,
            headless=True,
            spec=spec,
        )
        runs.append(instance)
        instance.start()
        instance.control("resume")
        instance.thread.join(timeout=15)
        assert not instance.thread.is_alive(), instance.snapshot(touch=False)
        return instance

    yield run
    for instance in runs:
        if instance.thread.is_alive():
            instance.control("stop")
            instance.thread.join(5)


@pytest.fixture
def test_plugins(monkeypatch, request):
    """Install test-only protocol fixtures into participating tests, never the app."""
    import importlib
    from pathlab.registry import PluginSpec, registry as uploaded_registry

    def catalog(path=None, **kwargs):
        found = uploaded_registry(path, **kwargs)
        if path is not None:
            return found
        for key, implementation, capability in [
            ("stop", "Stop", "action"),
            ("constant", "Constant", "action"),
            ("image_probe", "ImageProbe", "perception"),
        ]:
            found[key] = PluginSpec(
                id=key,
                name=key,
                version="test",
                capabilities=[capability],
                entrypoint=f"tests.faults:{implementation}",
            )
        found["external_stop"] = PluginSpec(
            id="external_stop",
            name="stdio test",
            version="test",
            capabilities=["action"],
            command=["{python}", "-m", "student_template.stdio"],
        )
        return found

    for name in ["pathlab.api", "pathlab.engine", "pathlab.benchmark"]:
        monkeypatch.setattr(importlib.import_module(name), "registry", catalog)
    if hasattr(request.module, "registry"):
        monkeypatch.setattr(request.module, "registry", catalog)
