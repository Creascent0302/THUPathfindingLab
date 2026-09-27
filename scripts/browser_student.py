"""Student UI acceptance, optionally against a standalone release executable."""

from pathlib import Path
import sys
import tempfile

from playwright.sync_api import expect, sync_playwright

from browser_support import ROOT, serve_test, until
from check_release import server


def main():
    output = ROOT / ".cache" / "student-browser"
    output.mkdir(parents=True, exist_ok=True)
    errors = []
    with tempfile.TemporaryDirectory(prefix="pathlab-student-browser-") as temporary:
        service = (
            server(Path(sys.argv[1]).resolve(), Path(temporary))
            if len(sys.argv) > 1
            else serve_test(temporary, output)
        )
        with service as http, sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True, args=["--no-sandbox"])
            page = browser.new_page(viewport={"width": 1440, "height": 1080})
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.goto(str(http.base_url))
            page.get_by_alt_text("原始摄像头图像").wait_for()
            expect(
                page.get_by_label("算法", exact=True).locator("option")
            ).to_have_count(1)
            expect(page.get_by_label("算法", exact=True)).to_have_value("manual")
            page.get_by_role("button", name="▶ 启动实验", exact=True).click()
            page.get_by_role("button", name="Ⅱ 暂停", exact=True).wait_for()
            until(lambda: http.get("/api/results").json())
            run_id = http.get("/api/results").json()[0]["episode_id"]

            def snapshot():
                return http.get(f"/api/runs/{run_id}").json()

            until(lambda: snapshot()["state"] == "running")
            page.get_by_label("目标速度", exact=True).focus()
            for _ in range(12):
                page.keyboard.press("ArrowRight")
            until(
                lambda: (snapshot().get("frame") or {})
                .get("pose", {})
                .get("speed_mps", 0)
                > 0.1
            )
            page.get_by_label("目标速度", exact=True).evaluate("el => el.blur()")
            for _ in range(12):
                page.keyboard.press("ArrowDown")
            until(
                lambda: (snapshot().get("frame") or {})
                .get("pose", {})
                .get("speed_mps", 0)
                < -0.08
            )
            page.get_by_role("button", name="Ⅱ 暂停", exact=True).click()
            until(lambda: snapshot()["paused"])
            count = snapshot()["frame_count"]
            page.get_by_role("button", name="单步", exact=True).click()
            until(lambda: snapshot()["frame_count"] == count + 1)
            page.get_by_role("button", name="停止", exact=True).click()
            until(lambda: snapshot()["state"] == "cancelled")
            assert snapshot()["frame"]["pose"]["speed_mps"] == 0
            page.get_by_role("button", name="进入结果回放", exact=True).click()
            page.get_by_label("回放帧", exact=True).wait_for()
            page.get_by_role("button", name="批量评测", exact=False).click()
            expect(
                page.get_by_text(
                    "请先在「算法提交」上传对应输出类型的代码。", exact=True
                )
            ).to_be_visible()
            page.get_by_role("button", name="算法提交", exact=False).click()
            page.get_by_label("算法名称", exact=True).fill("学生空白模板")
            page.get_by_label("算法压缩包", exact=True).set_input_files(
                {
                    "name": "student.zip",
                    "mimeType": "application/zip",
                    "buffer": http.get("/api/submissions/template").content,
                }
            )
            page.get_by_role("button", name="上传并选用", exact=True).click()
            page.get_by_role("button", name="▶ 启动实验", exact=True).wait_for()
            selected = page.get_by_label("算法", exact=True).input_value()
            assert selected.startswith("upload_")
            page.get_by_text("时限与压力测试", exact=True).click()
            page.get_by_label("最大步数", exact=True).fill("3")
            page.get_by_role("button", name="▶ 启动实验", exact=True).click()
            until(
                lambda: any(
                    r["config"]["algorithm"] == selected and r["metrics"] is not None
                    for r in http.get("/api/results").json()
                )
            )
            result = next(
                r
                for r in http.get("/api/results").json()
                if r["config"]["algorithm"] == selected
            )
            assert not result["failures"], result
            page.get_by_role("button", name="自定义地图", exact=False).click()
            expect(
                page.get_by_role("button", name="应用到实验", exact=True)
            ).to_be_enabled(timeout=15000)
            page.get_by_label("圆角半径", exact=True).fill("0.2")
            expect(page.get_by_role("status", name="地图几何检查")).to_contain_text(
                "圆角半径至少"
            )
            page.get_by_label("圆角半径", exact=True).fill("1")
            page.get_by_role("button", name="应用到实验", exact=True).click()
            page.get_by_alt_text("原始摄像头图像").wait_for()
            scene = http.get("/api/scenes/straight").json()["scene"]
            scene["name"] = "学生地图"
            assert http.post("/api/maps", json=scene).status_code == 201
            page.reload()
            expect(
                page.get_by_label("场景", exact=True)
                .locator("option")
                .filter(has_text="学生地图")
            ).to_have_count(1)
            page.screenshot(path=str(output / "workbench.png"), full_page=True)
            page.get_by_role("button", name="运行记录与对比", exact=False).click()
            page.get_by_role("button", name="刷新记录", exact=True).wait_for()
            page.set_viewport_size({"width": 390, "height": 844})
            assert page.evaluate(
                "document.documentElement.scrollWidth <= window.innerWidth + 1"
            )
            assert not errors, errors
            browser.close()
    print(
        "学生浏览器验收通过：空目录、手动前进/倒车/制动、单步/回放、上传运行、地图约束与主页加载、窄屏；0 页面异常。"
    )


if __name__ == "__main__":
    main()
