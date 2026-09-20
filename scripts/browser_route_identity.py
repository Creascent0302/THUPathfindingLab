"""Real Chromium acceptance for algorithm status versus private route identity."""

import io
import json
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import zipfile

import httpx
from playwright.sync_api import expect, sync_playwright

from browser_smoke import ROOT, until


def main():
    output = ROOT / "artifacts" / "browser-route-identity"
    output.mkdir(parents=True, exist_ok=True)
    checks, errors = [], []
    with tempfile.TemporaryDirectory(prefix="pathlab-identity-ui-") as data:
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
        with (output / "server.log").open("w") as log:
            command = (
                "from pathlib import Path; import uvicorn; from pathlab.api import create_app; "
                f"uvicorn.run(create_app(Path({data!r})), host='127.0.0.1', port={port})"
            )
            server = subprocess.Popen(
                [sys.executable, "-c", command], cwd=ROOT, stdout=log, stderr=log
            )
            try:
                with httpx.Client(
                    base_url=f"http://127.0.0.1:{port}", timeout=20, trust_env=False
                ) as http:

                    def healthy():
                        try:
                            return http.get("/api/health").status_code == 200
                        except httpx.ConnectError:
                            return False

                    until(healthy)
                    # An actual Worker plugin deliberately reports TRACK even
                    # before entering the start gate, exercising the disputed UI.
                    archive = io.BytesIO()
                    with zipfile.ZipFile(archive, "w") as bundle:
                        bundle.writestr(
                            "algorithm.py",
                            "from algorithms.modular.algorithm import TemporalPursuit\n"
                            "class StudentAlgorithm(TemporalPursuit):\n"
                            "    def step(self, observation):\n"
                            "        output = super().step(observation)\n"
                            "        output.status = 'TRACK'\n"
                            "        return output\n",
                        )
                    uploaded = http.post(
                        "/api/submissions",
                        files={
                            "file": (
                                "status-probe.zip", archive.getvalue(), "application/zip"
                            )
                        },
                        data={"name": "状态隔离测试", "capability": "action"},
                    )
                    uploaded.raise_for_status()
                    plugin_id = uploaded.json()["id"]
                    with sync_playwright() as playwright:
                        browser = playwright.chromium.launch(
                            headless=True, args=["--no-sandbox"]
                        )
                        page = browser.new_page(viewport={"width": 1600, "height": 1080})
                        page.on("pageerror", lambda error: errors.append(str(error)))
                        page.goto(str(http.base_url))
                        page.get_by_alt_text("原始摄像头图像").wait_for()
                        assessment = page.get_by_role("region", name="当前帧路径评测")
                        expect(assessment).to_contain_text("等待首帧评测")
                        expect(page.locator(".metrics-strip > div").first).to_contain_text("UNINITIALIZED")
                        page.get_by_label("算法", exact=True).select_option(plugin_id)
                        with page.expect_response(
                            lambda response: response.url.endswith("/api/runs")
                            and response.request.method == "POST"
                        ) as created:
                            page.get_by_role("button", name="单步", exact=True).click()
                        run_id = created.value.json()["id"]
                        expect(assessment).to_contain_text("尚未合法接入起点")
                        expect(page.locator(".metrics-strip > div").first).to_contain_text("TRACK")
                        expect(assessment).to_contain_text("距起点")
                        checks.append("live TRACK remains separate from unacquired route")
                        page.screenshot(path=str(output / "unacquired.png"), full_page=True)

                        page.get_by_role("button", name="▶ 继续运行", exact=True).click()
                        expect(assessment).to_contain_text("已合法接入 · 有序跟踪", timeout=15000)
                        expect(assessment).to_contain_text("当前参考段")
                        checks.append("actual legal acquisition updates independent assessment")
                        page.get_by_role("button", name="停止", exact=True).click()
                        until(
                            lambda: http.get(f"/api/runs/{run_id}").json()["state"]
                            == "cancelled"
                        )
                        page.get_by_role("button", name="进入结果回放", exact=True).click()
                        expect(assessment).to_contain_text("尚未合法接入起点")
                        expect(page.locator(".notice")).to_contain_text("该次运行最终结果")
                        checks.append("replay shows frame acquisition separately from final result")

                        def open_replay(identifier):
                            page.get_by_role("button", name="运行记录与对比", exact=True).click()
                            row = page.get_by_role("row").filter(has_text=identifier[:8])
                            row.get_by_role("button", name="回放", exact=True).click()
                            page.get_by_label("回放帧", exact=True).press("End")

                        scene = http.get("/api/scenes/straight?seed=7").json()["scene"]
                        scene["initial_pose"] = {"x_m": -1.5, "y_m": 0.12, "yaw_rad": 0}
                        scene["distractors"] = [[[-1.5 + i * 0.1, 0.12] for i in range(116)]]
                        scene["objects"] = []

                        def simulate(test_scene, speed):
                            response = http.post(
                                "/api/runs",
                                json={
                                    "algorithm": "constant", "scene": test_scene,
                                    "parameters": {"speed_mps": speed},
                                    "realtime": False, "max_steps": 200,
                                },
                            )
                            assert response.is_success, response.text
                            identifier = response.json()["id"]
                            http.post(
                                f"/api/runs/{identifier}/control",
                                json={"command": "resume"},
                            )
                            until(
                                lambda: http.get(f"/api/runs/{identifier}").json()["state"]
                                in {"completed", "failed", "cancelled"},
                                timeout=30,
                            )
                            return identifier, http.get(f"/api/runs/{identifier}").json()

                        wrong_id, wrong = simulate(scene, 0.45)
                        assert wrong["reason"] == "illegal_switch", wrong["reason"]
                        open_replay(wrong_id)
                        expect(assessment).to_contain_text("非法换线")
                        expect(assessment).to_contain_text("邻近干扰线 1")
                        expect(assessment).to_contain_text("错线证据持续")
                        expect(page.locator(".metrics-strip > div").first).to_contain_text("安全制动")
                        checks.append("physical wrong-line replay exposes ordered-reference evidence")
                        checks.append("coasting frame does not pretend the algorithm was reset")
                        page.screenshot(path=str(output / "wrong-branch.png"), full_page=True)

                        scene["initial_pose"] = {"x_m": -1.5, "y_m": 0, "yaw_rad": 0}
                        scene["distractors"] = []
                        stopped_id, stopped = simulate(scene, 0)
                        assert stopped["reason"] == "acquisition_failed", stopped["reason"]
                        open_replay(stopped_id)
                        expect(assessment).to_contain_text("未从起点合法接入")
                        checks.append("acquisition failure uses explicit Chinese assessment reason")

                        # Compatibility fixture only: copy a real new run inside
                        # the temporary test store, removing fields unavailable
                        # in v2. Never rewrite user histories or map files.
                        legacy_id = "0123456789abcdef0123456789abcdef"
                        source = Path(data) / "runs" / run_id
                        target = Path(data) / "runs" / legacy_id
                        target.mkdir()
                        manifest = json.loads((source / "manifest.json").read_text())
                        manifest.update(
                            episode_id=legacy_id, evaluator_version="2.0", score_version="2.0"
                        )
                        manifest.pop("comparison_key", None)
                        (target / "manifest.json").write_text(json.dumps(manifest))
                        fields = {
                            "phase", "lateral_error_m", "heading_error_rad", "progress_m",
                            "completion", "reason", "switch_count", "collision_ids",
                        }
                        with (target / "frames.jsonl").open("w") as handle:
                            for line in (source / "frames.jsonl").read_text().splitlines():
                                row = json.loads(line)
                                row["evaluation"] = {
                                    key: value for key, value in row["evaluation"].items()
                                    if key in fields
                                }
                                handle.write(json.dumps(row) + "\n")
                        open_replay(legacy_id)
                        expect(assessment).to_contain_text("该历史帧未保存道路身份明细，按原始评测显示。")
                        checks.append("legacy replay preserves recorded evaluation without inventing identity")
                        page.set_viewport_size({"width": 760, "height": 1080})
                        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1")
                        checks.append("assessment remains readable without horizontal overflow on narrow screen")
                        browser.close()
                assert not errors, errors
                report = json.dumps(
                    {"checks": checks, "errors": errors}, ensure_ascii=False, indent=2
                )
                (output / "checks.json").write_text(report)
                print(report)
            finally:
                server.terminate()
                try:
                    server.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    server.kill()
                    server.wait()


if __name__ == "__main__":
    main()
