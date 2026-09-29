"""Exercise layer drawing, legacy upgrade and persistence through real Chromium."""

import json
from pathlib import Path
import tempfile

from playwright.sync_api import expect, sync_playwright

from browser_support import ROOT, serve_test, until


def main():
    output = ROOT / ".cache" / "browser-map-layers"
    output.mkdir(parents=True, exist_ok=True)
    checks, errors = [], []
    original = ROOT / "scenarios/challenges/user-original.json"
    raw = original.read_text(encoding="utf-8")
    legacy = json.loads(raw)
    with tempfile.TemporaryDirectory(prefix="pathlab-layers-") as data:
        source = Path(data) / "legacy.json"
        source.write_text(raw)
        with serve_test(Path(data) / "data", output) as http:
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(
                    headless=True, args=["--no-sandbox"]
                )
                page = browser.new_page(viewport={"width": 1600, "height": 1100})
                page.on("pageerror", lambda error: errors.append(str(error)))
                page.goto(str(http.base_url))
                page.get_by_alt_text("原始摄像头图像").wait_for()
                page.get_by_role("button", name="自定义地图", exact=True).click()
                page.get_by_label("导入地图").set_input_files(source)
                apply = page.get_by_role("button", name="应用到实验", exact=True)
                expect(apply).to_be_enabled(timeout=15000)
                expect(page.locator(".editor-upgrade-note")).to_contain_text("版本 3")
                camera = page.get_by_alt_text("自定义地图摄像头预览")
                before_image = camera.get_attribute("src")
                canvas = page.get_by_label("地图控制点画布")

                def position(point):
                    canvas.scroll_into_view_if_needed()
                    return canvas.evaluate(
                        "(el, [x,y]) => { const p = new DOMPoint(x,-y).matrixTransform(el.getScreenCTM()); return [p.x,p.y]; }",
                        point,
                    )

                def place(point):
                    page.mouse.click(*position(point))

                def export():
                    expect(apply).to_be_enabled(timeout=15000)
                    with page.expect_download() as downloaded:
                        page.get_by_role("button", name="导出 JSON", exact=True).click()
                    return json.loads(Path(downloaded.value.path()).read_text())

                upgraded = export()
                assert upgraded["target_path"] == legacy["target_path"]
                assert [upgraded["initial_pose"]["x_m"], upgraded["initial_pose"]["y_m"]] == legacy["target_path"][0]
                for key, value in legacy["vehicle"].items():
                    assert upgraded["vehicle"][key] == value
                assert upgraded["vehicle"]["motion_model"] == legacy["vehicle"].get(
                    "motion_model", "kinematic_v1"
                )
                checks.append(
                    "real legacy map upgrades rendering preserving target geometry and placing car at its start"
                )

                page.get_by_role("button", name="障碍物", exact=True).click()
                page.get_by_label("添加物件类型").select_option("box")
                place([1, -0.7])
                expect(page.get_by_label("物件X", exact=True)).to_have_value("1")
                start, end = position([1, -0.7]), position([1.3, -0.7])
                page.mouse.move(*start)
                page.mouse.down()
                page.mouse.move(*end, steps=8)
                page.mouse.up()
                expect(page.get_by_label("物件X", exact=True)).to_have_value("1.3")
                expect(apply).to_be_enabled(timeout=15000)
                until(lambda: camera.get_attribute("src") != before_image)
                checks.append(
                    "click places selected solid, drag moves it, RGB camera shows actual object"
                )

                page.get_by_role("button", name="干扰线", exact=True).click()
                page.get_by_role("button", name="新增干扰线", exact=True).click()
                place([-0.5, 0.7])
                expect(apply).to_be_disabled()
                place([2, 0.7])
                expect(apply).to_be_enabled(timeout=15000)
                page.get_by_role("button", name="新增干扰线", exact=True).click()
                place([-0.5, -1.4])
                place([1, -1.7])
                place([2.3, -1.4])
                page.get_by_label("干扰线形状").select_option("smooth")
                expect(apply).to_be_enabled(timeout=15000)
                start, end = position([2.3, -1.4]), position([2.4, -1.4])
                page.mouse.move(*start)
                page.mouse.down()
                page.mouse.move(*end, steps=8)
                page.mouse.up()
                scene = export()
                assert len(scene["distractors"]) == 2
                assert scene["distractors"][1][-1] == [2.4, -1.4]
                assert scene["design"]["distractors"][1]["interpolation"] == "smooth"
                assert scene["target_path"] == legacy["target_path"]
                assert scene["objects"][0]["x_m"] == 1.3
                checks.append(
                    "two independent line layers, smooth mode and pointer control preserve target"
                )

                page.get_by_label("干扰控制点", exact=True).select_option("1")
                page.get_by_role("button", name="删除此干扰控制点", exact=True).click()
                assert len(export()["design"]["distractors"][1]["waypoints"]) == 2
                page.get_by_role("button", name="删除此干扰线", exact=True).click()
                assert len(export()["distractors"]) == 1
                checks.append("point and line deletion affect only selected distractor")

                page.get_by_label("地图名称", exact=True).fill("分层编辑验收")
                expect(apply).to_be_enabled(timeout=15000)
                page.get_by_role("button", name="保存地图", exact=True).click()
                until(lambda: len(http.get("/api/maps").json()) == 1)
                saved = http.get("/api/maps").json()[0]["scene"]
                assert len(saved["distractors"]) == len(saved["objects"]) == 1
                page.get_by_role("button", name="加载", exact=True).click()
                reloaded = export()
                assert reloaded["distractors"] == saved["distractors"]
                assert reloaded["objects"] == saved["objects"]
                with tempfile.NamedTemporaryFile(
                    suffix=".json", mode="w", dir=data
                ) as transfer:
                    json.dump(saved, transfer)
                    transfer.flush()
                    page.get_by_label("导入地图").set_input_files(transfer.name)
                    assert export()["distractors"] == saved["distractors"]
                checks.append("save / reload / export / import preserve all map layers")
                page.screenshot(path=str(output / "layers.png"), full_page=True)
                page.set_viewport_size({"width": 390, "height": 844})
                assert page.evaluate(
                    "document.documentElement.scrollWidth <= innerWidth + 1"
                )
                page.get_by_role("button", name="障碍物", exact=True).click()
                expect(page.get_by_label("添加物件类型")).to_be_visible()
                checks.append(
                    "three editing modes remain usable without horizontal overflow on mobile"
                )
                page.set_viewport_size({"width": 1600, "height": 1100})
                apply.click()
                expect(page.get_by_label("场景", exact=True)).to_have_value("custom")
                page.get_by_text("时限与压力测试", exact=True).click()
                page.get_by_label("最大步数", exact=True).fill("2")
                page.get_by_label("算法", exact=True).select_option("stop")
                page.get_by_role("button", name="▶ 启动实验", exact=True).click()
                until(lambda: bool(http.get("/api/results").json()), timeout=30)
                result = http.get("/api/results").json()[0]
                run_scene = http.get(f"/api/results/{result['episode_id']}").json()[
                    "manifest"
                ]["scene"]
                assert run_scene["distractors"] == saved["distractors"]
                assert run_scene["objects"] == saved["objects"]
                assert run_scene["render_version"] == "3"
                checks.append(
                    "applied map reaches real experiment with solids and distractors intact"
                )
                assert not errors, errors
                browser.close()
    if original.exists():
        assert original.read_text() == raw
    report = {"passed": checks, "browser_errors": errors}
    (output / "report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2)
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
