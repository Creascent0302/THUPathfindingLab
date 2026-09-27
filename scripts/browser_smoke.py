"""Real Chromium acceptance. Optional maintainer dependency: playwright==1.52.0."""

import json
import tempfile

import cv2
import numpy as np
from playwright.sync_api import sync_playwright

from browser_support import ROOT, serve_test, until


def main():
    output = ROOT / "artifacts" / "browser"
    output.mkdir(parents=True, exist_ok=True)
    errors = []
    with (
        tempfile.TemporaryDirectory(prefix="pathlab-smoke-") as data,
        serve_test(data, output) as http,
    ):
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True, args=["--no-sandbox"])
            page = browser.new_page(
                viewport={"width": 1440, "height": 1080}, device_scale_factor=1
            )
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.goto(str(http.base_url))
            page.get_by_alt_text("原始摄像头图像").wait_for()
            page.evaluate("document.fonts.ready")
            page.set_viewport_size({"width": 1920, "height": 1080})
            page.get_by_text("参数与初始化提示", exact=True).click()
            page.get_by_role("button", name="点击目标", exact=True).click()
            page.locator(".camera-panel svg").first.scroll_into_view_if_needed()
            location = page.locator(".camera-panel svg").first.evaluate(
                "el => { const p = new DOMPoint(200, 120).matrixTransform(el.getScreenCTM()); return {x:p.x,y:p.y}; }"
            )
            page.mouse.click(location["x"], location["y"])
            selected_hint = json.loads(
                page.locator(".sidebar small.field-note")
                .filter(has_text='"kind":"point"')
                .inner_text()
            )
            assert (
                max(abs(a - b) for a, b in zip(selected_hint["point_px"], [200, 120]))
                < 0.75
            )
            page.get_by_role("button", name="默认提示", exact=True).click()
            page.get_by_text("参数与初始化提示", exact=True).click()
            page.set_viewport_size({"width": 1440, "height": 1080})
            page.get_by_text("车辆惯性与制动", exact=True).click()
            page.get_by_label("允许倒车", exact=True).check()
            page.get_by_label("最高倒车速度 / m/s", exact=True).fill("0.4")
            page.get_by_role("button", name="应用车辆设置", exact=True).click()
            until(
                lambda: float(
                    page.get_by_label("目标速度", exact=True).get_attribute("min")
                )
                == -0.4
            )
            page.get_by_text("车辆惯性与制动", exact=True).click()
            page.screenshot(path=str(output / "workbench.png"), full_page=True)
            page.get_by_role("button", name="▶ 启动实验", exact=True).click()
            page.get_by_role("button", name="Ⅱ 暂停", exact=True).wait_for()
            until(lambda: len(http.get("/api/results").json()) > 0)
            run_id = http.get("/api/results").json()[0]["episode_id"]

            def snapshot():
                return http.get(f"/api/runs/{run_id}").json()

            until(lambda: snapshot()["state"] == "running")
            initial_x = snapshot()["scene"]["initial_pose"]["x_m"]
            page.get_by_label("目标速度", exact=True).focus()
            for _ in range(12):
                page.keyboard.press("ArrowRight")
            until(
                lambda: (snapshot().get("frame") or {})
                .get("pose", {})
                .get("x_m", initial_x)
                > initial_x + 0.08
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
            assert (
                float(page.get_by_label("目标速度", exact=True).input_value()) == -0.4
            )
            page.get_by_role("button", name="Ⅱ 暂停", exact=True).click()
            until(lambda: snapshot()["paused"])
            page.wait_for_timeout(300)
            n = snapshot()["frame_count"]
            page.wait_for_timeout(250)
            assert snapshot()["frame_count"] == n
            page.get_by_role("button", name="单步", exact=True).click()
            until(lambda: snapshot()["frame_count"] == n + 1)
            page.screenshot(path=str(output / "manual-paused.png"), full_page=True)
            page.get_by_role("button", name="停止", exact=True).click()
            until(lambda: snapshot()["state"] == "cancelled")
            assert snapshot()["frame"]["pose"]["speed_mps"] == 0
            page.get_by_role("button", name="进入结果回放", exact=True).click()
            page.get_by_label("回放帧", exact=True).wait_for()
            page.get_by_label("回放帧", exact=True).focus()
            page.keyboard.press("End")
            page.wait_for_timeout(350)
            page.keyboard.press("Home")
            page.wait_for_timeout(350)
            assert page.get_by_label("回放帧", exact=True).input_value() == "0"
            page.get_by_role("button", name="重置", exact=True).click()
            page.get_by_role("button", name="▶ 继续运行", exact=True).wait_for()
            reset_id = http.get("/api/results").json()[0]["episode_id"]
            assert reset_id != run_id
            assert http.get(f"/api/runs/{reset_id}").json()["frame_count"] == 0
            page.get_by_role("button", name="停止", exact=True).click()
            until(
                lambda: http.get(f"/api/runs/{reset_id}").json()["state"] == "cancelled"
            )
            page.wait_for_timeout(250)
            page.get_by_label("输入来源", exact=True).select_option("image")
            image = np.full((120, 160, 3), 225, np.uint8)
            cv2.line(image, (80, 110), (60, 20), (30, 30, 30), 6)
            png = output / "input.png"
            cv2.imwrite(str(png), image)
            page.get_by_label("上传素材", exact=True).set_input_files(str(png))
            page.get_by_text("已导入 1 帧", exact=True).wait_for()
            page.get_by_role("button", name="▶ 启动实验", exact=True).click()
            page.get_by_text("本次结果：素材处理完成。", exact=False).wait_for()
            page.screenshot(path=str(output / "single-frame.png"), full_page=True)
            page.get_by_role("button", name="运行记录与对比", exact=False).click()
            page.get_by_role("button", name="刷新记录", exact=True).wait_for()
            page.wait_for_function("document.querySelectorAll('tbody tr').length >= 3")
            assert page.get_by_role("row").count() >= 4
            page.locator("table input[type=checkbox]").first.check()
            page.get_by_role("heading", name="选中实验对比", exact=True).wait_for()
            page.screenshot(path=str(output / "results.png"), full_page=True)
            page.set_viewport_size({"width": 390, "height": 844})
            assert page.evaluate(
                "document.documentElement.scrollWidth <= window.innerWidth + 1"
            )
            page.set_viewport_size({"width": 1440, "height": 1080})
            page.get_by_role("button", name="实验工作台", exact=False).click()
            page.get_by_label("输入来源", exact=True).select_option("simulation")
            page.get_by_label("场景", exact=True).select_option("hairpin")
            page.wait_for_timeout(700)
            assert page.get_by_text("首帧预览", exact=False).count() == 2
            page.get_by_role("button", name="运行记录与对比", exact=False).click()
            page.wait_for_function("document.querySelectorAll('tbody tr').length >= 3")
            page.locator("tbody tr").first.get_by_role(
                "button", name="回放", exact=True
            ).click()
            page.get_by_text("录制素材没有地图真值", exact=False).wait_for()
            assert not errors, errors
            browser.close()
        print(
            "Chromium 验收通过：手动前进与倒车、倒车制动、车辆设置、回放、素材、结果对比、窄屏、配置切换；0 个页面异常。"
        )
        (output / "report.txt").write_text(
            "PASS: 18 browser acceptance checks, including reverse driving; 0 page errors.\n",
            encoding="utf-8",
        )


if __name__ == "__main__":
    main()
