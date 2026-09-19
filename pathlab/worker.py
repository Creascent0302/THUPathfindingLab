"""JSON-lines subprocess transport and SDK plugin host (no pickle)."""

from __future__ import annotations

import argparse
from collections import deque
import contextlib
import importlib
import json
import os
import queue
import signal
import subprocess
import sys
import threading
import time

from .registry import ROOT, PluginSpec
from .sdk import AlgorithmOutput, MAX_MESSAGE_BYTES, Observation, TaskHint, VERSION


class WorkerError(RuntimeError):
    def __init__(self, kind: str, message: str):
        self.kind = kind
        super().__init__(message)


def strict_loads(text: str | bytes):
    def invalid(value):
        raise ValueError(f"JSON 非有限数值：{value}")

    return json.loads(text, parse_constant=invalid)


class WorkerClient:
    def __init__(self, spec: PluginSpec):
        environment = os.environ.copy()
        environment.update(
            OMP_NUM_THREADS="1", OPENBLAS_NUM_THREADS="1", PYTHONUNBUFFERED="1"
        )
        # Each submission owns its import directory; the server never imports it.
        environment["PYTHONPATH"] = os.pathsep.join(
            [str(ROOT), *([spec.working_directory] if spec.working_directory else [])]
        )
        self.process = subprocess.Popen(
            spec.argv(),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=spec.working_directory or ROOT,
            env=environment,
            start_new_session=os.name != "nt",
        )
        self.responses: queue.Queue = queue.Queue(maxsize=2)
        self.logs: deque[str] = deque(maxlen=20)
        self.sequence = 0
        self.closed = False
        self.last_raw = None
        self.threads = [
            threading.Thread(target=self._read_stdout, daemon=True),
            threading.Thread(target=self._read_stderr, daemon=True),
        ]
        for thread in self.threads:
            thread.start()

    def _read_stdout(self):
        try:
            while not self.closed:
                line = self.process.stdout.readline(MAX_MESSAGE_BYTES + 1)
                if not line:
                    self.responses.put_nowait(
                        WorkerError("crash", "算法进程退出或关闭了标准输出")
                    )
                    return
                if len(line) > MAX_MESSAGE_BYTES or not line.endswith(b"\n"):
                    self.responses.put_nowait(
                        WorkerError("protocol", "协议消息超限或缺少换行边界")
                    )
                    return
                self.responses.put_nowait(line)
        except (OSError, ValueError, queue.Full):
            return

    def _read_stderr(self):
        try:
            while not self.closed:
                data = self.process.stderr.read1(2048)
                if not data:
                    return
                self.logs.append(data.decode("utf-8", errors="replace"))
        except (OSError, ValueError):
            return

    def request(self, method: str, payload: dict, timeout: float):
        if self.closed:
            raise WorkerError("crash", "算法进程已关闭")
        self.sequence += 1
        message_id = self.sequence
        data = (
            json.dumps(
                {
                    "protocol_version": VERSION,
                    "id": message_id,
                    "method": method,
                    "payload": payload,
                },
                allow_nan=False,
                separators=(",", ":"),
            ).encode()
            + b"\n"
        )
        if len(data) > MAX_MESSAGE_BYTES:
            raise WorkerError("protocol", "请求消息超过 8 MiB")
        write_errors = []

        def write():
            try:
                self.process.stdin.write(data)
                self.process.stdin.flush()
            except (OSError, ValueError) as error:
                write_errors.append(error)

        start = time.monotonic()
        writer = threading.Thread(target=write, daemon=True)
        writer.start()
        try:
            response = self.responses.get(timeout=timeout)
            writer.join(timeout=max(0, timeout - (time.monotonic() - start)))
            if writer.is_alive():
                raise queue.Empty
            if isinstance(response, WorkerError):
                raise response
            self.last_raw = response.decode("utf-8", errors="replace")[:32768]
            parsed = strict_loads(response)
            if (
                not isinstance(parsed, dict)
                or parsed.get("protocol_version") != VERSION
                or parsed.get("id") != message_id
            ):
                raise WorkerError("protocol", "响应版本或消息 id 不匹配")
            if parsed.get("ok") is not True:
                raise WorkerError(
                    "exception", str(parsed.get("error", "算法返回失败"))[:4096]
                )
            if "result" not in parsed:
                raise WorkerError("protocol", "响应缺少 result")
            return parsed["result"]
        except queue.Empty as error:
            self.kill()
            raise WorkerError(
                "timeout", f"{method} 超过 {timeout:.2f} s，worker 已终止"
            ) from error
        except (ValueError, UnicodeError) as error:
            self.kill()
            raise WorkerError("protocol", f"非法 JSON：{error}") from error

    def initialize(
        self,
        parameters: dict,
        public_context: dict,
        observation: Observation,
        timeout: float,
    ):
        self.request(
            "initialize",
            {"config": parameters, "public_context": public_context},
            max(5, timeout),
        )
        self.request(
            "reset",
            {
                "observation": observation.model_dump(),
                "task_hint": observation.task_hint.model_dump(),
            },
            max(5, timeout),
        )

    def step(self, observation: Observation, timeout: float) -> AlgorithmOutput:
        self.last_raw = None
        result = self.request(
            "step", {"observation": observation.model_dump()}, timeout
        )
        try:
            return AlgorithmOutput.model_validate(result)
        except ValueError as error:
            raise WorkerError("invalid_output", str(error)[:4096]) from error

    def kill(self):
        if self.closed:
            return
        self.closed = True
        if os.name != "nt":
            try:
                os.killpg(self.process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        elif self.process.poll() is None:
            subprocess.run(
                ["taskkill", "/PID", str(self.process.pid), "/T", "/F"],
                capture_output=True,
                check=False,
            )
        try:
            self.process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            self.process.kill()
            self.process.wait(timeout=2)
        for stream in (self.process.stdin, self.process.stdout, self.process.stderr):
            with contextlib.suppress(OSError, ValueError):
                stream.close()

    def close(self):
        if not self.closed:
            with contextlib.suppress(Exception):
                self.request("close", {}, 0.2)
        self.kill()


def serve_plugin(entrypoint: str):
    """May also be called by a standalone Python program implementing the protocol."""
    cv_threads = importlib.import_module("cv2")
    cv_threads.setNumThreads(1)
    wire = sys.stdout
    # Plugin prints are diagnostics, never protocol data.
    sys.stdout = sys.stderr
    module, name = entrypoint.split(":", 1)
    plugin = getattr(importlib.import_module(module), name)()
    initialized, reset = False, False
    while True:
        line = sys.stdin.buffer.readline(MAX_MESSAGE_BYTES + 1)
        if not line:
            break
        message_id = None
        method = ""
        try:
            if len(line) > MAX_MESSAGE_BYTES or not line.endswith(b"\n"):
                raise ValueError("消息超限或缺少换行")
            message = strict_loads(line)
            message_id = message.get("id")
            if message.get("protocol_version") != VERSION:
                raise ValueError("不支持的协议版本")
            method, payload = message["method"], message["payload"]
            result = None
            if method == "initialize" and not initialized:
                plugin.initialize(payload["config"], payload["public_context"])
                initialized = True
            elif method == "reset" and initialized:
                obs = Observation.model_validate(payload["observation"])
                obs.rgb()
                plugin.reset(obs, TaskHint.model_validate(payload["task_hint"]))
                reset = True
            elif method == "step" and reset:
                obs = Observation.model_validate(payload["observation"])
                obs.rgb()
                output = plugin.step(obs)
                result = (
                    output.model_dump()
                    if isinstance(output, AlgorithmOutput)
                    else output
                )
            elif method == "close":
                plugin.close()
            else:
                raise ValueError("未知方法或生命周期顺序错误")
            response = {
                "protocol_version": VERSION,
                "id": message_id,
                "ok": True,
                "result": result,
            }
            encoded = json.dumps(response, allow_nan=False)
            if len(encoded.encode()) > MAX_MESSAGE_BYTES - 1:
                raise ValueError("输出消息超限")
        except Exception as error:
            encoded = json.dumps(
                {
                    "protocol_version": VERSION,
                    "id": message_id,
                    "ok": False,
                    "error": f"{type(error).__name__}: {error}"[:4096],
                }
            )
        wire.write(encoded + "\n")
        wire.flush()
        if method == "close":
            break


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--plugin", required=True)
    serve_plugin(parser.parse_args().plugin)
