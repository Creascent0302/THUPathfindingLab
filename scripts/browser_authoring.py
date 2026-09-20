"""Browser acceptance for deletion, ZIP submissions, map authoring and rendering."""

import io
import json
import os
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
    output = ROOT / "artifacts" / "browser-authoring"
    output.mkdir(parents=True, exist_ok=True)
    checks, errors = [], []
    with tempfile.TemporaryDirectory(prefix="pathlab-browser-") as data:
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
                    base_url=f"http://127.0.0.1:{port}", trust_env=False, timeout=20
                ) as http:

                    def healthy():
                        try:
                            return http.get("/api/health").status_code == 200
                        except httpx.ConnectError:
                            return False

                    until(healthy)
                    with sync_playwright() as playwright:
                        browser = playwright.chromium.launch(
                            headless=True, args=["--no-sandbox"]
                        )
                        page = browser.new_page(
                            viewport={"width": 1600, "height": 1080}
                        )
                        page.on("pageerror", lambda error: errors.append(str(error)))
                        page.on("dialog", lambda dialog: dialog.accept())
                        page.goto(str(http.base_url))
                        page.get_by_alt_text("原始摄像头图像").wait_for()
                        assert not page.get_by_text("接入与使用", exact=True).count()
                        checks.append("removed help navigation")
                        page.get_by_text("时限与压力测试", exact=True).click()
                        assert (
                            page.get_by_label("最大步数", exact=True).input_value()
                            == "4000"
                        )
                        page.get_by_label("最大步数", exact=True).fill("8")
                        for algorithm in (
                            "temporal_pursuit",
                            "temporal_mpc",
                            "scanline_pid",
                            "cnn_gru",
                        ):
                            catalog = http.get("/api/catalog").json()
                            plugin = next(
                                p for p in catalog["algorithms"] if p["id"] == algorithm
                            )
                            if not plugin.get("available", True):
                                assert page.locator(
                                    f'option[value="{algorithm}"]'
                                ).is_disabled()
                                checks.append(f"{algorithm}: unavailable reason shown")
                                continue
                            page.get_by_label("算法", exact=True).select_option(
                                algorithm
                            )
                            page.get_by_role(
                                "button", name="▶ 启动实验", exact=True
                            ).click()

                            def finished():
                                rows = http.get("/api/results").json()
                                return any(
                                    r["config"]["algorithm"] == algorithm
                                    and r["state"] in {"completed", "failed"}
                                    for r in rows
                                )

                            until(finished, timeout=30)
                            result = next(
                                r
                                for r in http.get("/api/results").json()
                                if r["config"]["algorithm"] == algorithm
                            )
                            assert result["state"] == "completed", result
                            assert result["metrics"]["task_frames"] == 8
                            assert not result["failures"]
                            checks.append(
                                f"{algorithm}: selected and executed from browser"
                            )
                        page.get_by_label("算法", exact=True).select_option("manual")
                        for row in http.get("/api/results").json():
                            until(
                                lambda: http.delete(
                                    f"/api/results/{row['episode_id']}"
                                ).status_code
                                == 200
                            )
                        page.get_by_label("最大步数", exact=True).fill("4000")
                        page.get_by_text("时限与压力测试", exact=True).click()
                        page.get_by_label("场景", exact=True).select_option("repeated")
                        page.wait_for_timeout(1000)
                        expect(
                            page.get_by_label("立体场景与四轮车模型")
                        ).to_be_visible()
                        page.get_by_role("button", name="俯视图", exact=True).click()
                        expect(page.get_by_label("地图与实际轨迹")).to_be_visible()
                        page.get_by_role("button", name="立体视图", exact=True).click()
                        page.get_by_label("场景观察角度").fill("40")
                        page.screenshot(
                            path=str(output / "repeated-scene.png"), full_page=True
                        )
                        checks.append("complex scene and rotating model / top view")

                        page.get_by_role(
                            "button", name="自定义地图", exact=False
                        ).click()
                        apply = page.get_by_role(
                            "button", name="应用到实验", exact=True
                        )
                        expect(apply).to_be_enabled(timeout=15000)
                        page.get_by_label("圆角半径", exact=True).fill("0.2")
                        expect(
                            page.get_by_role("status", name="地图几何检查")
                        ).to_contain_text("圆角半径至少")
                        expect(apply).to_be_disabled()
                        page.get_by_label("圆角半径", exact=True).fill("1")
                        expect(apply).to_be_enabled()
                        page.get_by_label("编辑轴距", exact=True).fill("1")
                        expect(
                            page.get_by_role("status", name="地图几何检查")
                        ).to_contain_text("圆角半径至少")
                        page.get_by_label("编辑轴距", exact=True).fill("0.32")
                        expect(apply).to_be_enabled()
                        checks.append(
                            "radius and vehicle constraints reject invalid map"
                        )

                        canvas = page.get_by_label("地图控制点画布")
                        positions = canvas.evaluate(
                            "el => [[6,0],[7,0]].map(([x,y]) => {const p=new DOMPoint(x,y).matrixTransform(el.getScreenCTM()); return [p.x,p.y];})"
                        )
                        page.mouse.move(*positions[0])
                        page.mouse.down()
                        page.mouse.move(*positions[1], steps=10)
                        page.mouse.up()
                        expect(apply).to_be_enabled()
                        page.get_by_text("控制点坐标 · 4 个", exact=True).click()
                        expect(page.get_by_label("点 2 x", exact=True)).to_have_value(
                            "7"
                        )
                        page.get_by_label("地图名称", exact=True).fill("浏览器验收地图")
                        expect(apply).to_be_enabled()
                        page.get_by_role("button", name="保存地图", exact=True).click()
                        expect(
                            page.get_by_text(
                                "地图已保存，下次打开仍可加载。", exact=True
                            )
                        ).to_be_visible()
                        with page.expect_download() as download:
                            page.get_by_role(
                                "button", name="导出 JSON", exact=True
                            ).click()
                        downloaded = download.value.path()
                        exported = json.loads(Path(downloaded).read_text())
                        assert exported["design"]["waypoints"][1] == [7, 0]
                        checks.append("pointer editing / save / JSON export")
                        page.screenshot(
                            path=str(output / "map-editor.png"), full_page=True
                        )
                        page.set_viewport_size({"width": 390, "height": 844})
                        assert page.evaluate(
                            "document.documentElement.scrollWidth <= innerWidth + 1"
                        )
                        page.set_viewport_size({"width": 1600, "height": 1080})
                        checks.append("map editor mobile width")
                        apply.click()
                        expect(page.get_by_label("场景", exact=True)).to_have_value(
                            "custom"
                        )
                        page.get_by_role(
                            "button", name="自定义地图", exact=False
                        ).click()
                        expect(page.get_by_label("地图名称", exact=True)).to_have_value(
                            "浏览器验收地图"
                        )
                        page.get_by_role("button", name="恢复示例", exact=True).click()
                        page.get_by_role("button", name="加载", exact=True).click()
                        expect(apply).to_be_enabled()
                        page.get_by_label("导入地图", exact=True).set_input_files(
                            {
                                "name": "map.json",
                                "mimeType": "application/json",
                                "buffer": json.dumps(exported).encode(),
                            }
                        )
                        expect(apply).to_be_enabled()
                        apply.click()
                        checks.append("saved map reload / import / apply")

                        page.get_by_role("button", name="算法提交", exact=False).click()
                        template = http.get("/api/submissions/template").content
                        page.get_by_label("算法压缩包", exact=True).set_input_files(
                            {
                                "name": "team.zip",
                                "mimeType": "application/zip",
                                "buffer": template,
                            }
                        )
                        page.get_by_label("算法名称", exact=True).fill("浏览器提交算法")
                        page.screenshot(
                            path=str(output / "submission.png"), full_page=True
                        )
                        page.get_by_role(
                            "button", name="上传并选用", exact=True
                        ).click()
                        page.get_by_role(
                            "button", name="▶ 启动实验", exact=True
                        ).wait_for()
                        algorithm = page.get_by_label("算法", exact=True).input_value()
                        assert algorithm.startswith("upload_")
                        page.get_by_text("时限与压力测试", exact=True).click()
                        page.get_by_label("最大步数", exact=True).fill("3")
                        page.get_by_role(
                            "button", name="▶ 启动实验", exact=True
                        ).click()
                        until(
                            lambda: any(
                                r["metrics"] for r in http.get("/api/results").json()
                            ),
                            timeout=20,
                        )
                        result = http.get("/api/results").json()[0]
                        assert not result["failures"], result["failures"]
                        assert result["config"]["algorithm"] == algorithm
                        assert result["scene"]["design"]["waypoints"][1] == [7, 0]
                        assert result["metrics"]["task_frames"] == 3
                        checks.append(
                            "ZIP upload selection and actual execution on custom map"
                        )

                        # Add one independent record so bulk deletion has multiple targets.
                        second = http.post(
                            "/api/runs",
                            json={
                                "algorithm": "stop",
                                "max_steps": 1,
                                "realtime": False,
                            },
                        ).json()["id"]
                        http.post(
                            f"/api/runs/{second}/control", json={"command": "resume"}
                        )
                        until(
                            lambda: http.get(f"/api/results/{second}").json()[
                                "manifest"
                            ]["metrics"]
                            is not None
                        )
                        page.get_by_role(
                            "button", name="运行记录与对比", exact=False
                        ).click()
                        expect(page.locator("tbody tr")).to_have_count(2)
                        page.locator("tbody tr").last.get_by_role(
                            "button", name="回放", exact=True
                        ).click()
                        page.get_by_label("回放帧", exact=True).wait_for()
                        page.get_by_role(
                            "button", name="运行记录与对比", exact=False
                        ).click()
                        page.get_by_role(
                            "button", name="选择已结束记录", exact=True
                        ).click()
                        page.get_by_role(
                            "button", name="删除选中记录", exact=True
                        ).click()
                        expect(
                            page.get_by_text("还没有实验记录。", exact=False)
                        ).to_be_visible()
                        assert http.get("/api/results").json() == []
                        page.get_by_role(
                            "button", name="实验工作台", exact=False
                        ).click()
                        assert not page.get_by_label("回放帧", exact=True).count()
                        checks.append(
                            "bulk deletion clears recordings and active replay"
                        )

                        page.get_by_role("button", name="算法提交", exact=False).click()
                        bad = io.BytesIO()
                        with zipfile.ZipFile(bad, "w") as zipped:
                            zipped.writestr("../escape.py", "pass")
                        page.get_by_label("算法压缩包", exact=True).set_input_files(
                            {
                                "name": "bad.zip",
                                "mimeType": "application/zip",
                                "buffer": bad.getvalue(),
                            }
                        )
                        page.get_by_role(
                            "button", name="上传并选用", exact=True
                        ).click()
                        expect(page.get_by_role("alert")).to_contain_text(
                            "不允许的路径"
                        )
                        checks.append("archive validation error appears in UI")
                        assert not errors, errors
                        browser.close()
            finally:
                server.terminate()
                try:
                    server.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    server.kill()
                    server.wait()
    (output / "report.json").write_text(
        json.dumps(
            {"passed": checks, "page_errors": errors}, ensure_ascii=False, indent=2
        ),
        encoding="utf-8",
    )
    print(f"PASS: {len(checks)} authoring workflows; 0 page errors")


if __name__ == "__main__":
    os.environ.setdefault("PLAYWRIGHT_BROWSERS_PATH", str(ROOT / ".cache" / "browsers"))
    main()
