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
def execute(tmp_path):
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
