"""Real browser regression for draft durability and independent storage quotas."""

import json
from pathlib import Path
import socket
import subprocess
import sys
import tempfile

import httpx
from playwright.sync_api import expect, sync_playwright

from browser_smoke import ROOT, until


def main():
    output = ROOT / "artifacts" / "browser-persistence"
    output.mkdir(parents=True, exist_ok=True)
    checks, errors = [], []
    with tempfile.TemporaryDirectory(prefix="pathlab-persistence-") as data:
        root = Path(data)
        (root / "learning").mkdir()
        with (root / "learning" / "training.npz").open("wb") as handle:
            handle.truncate(2 * 1024**3 + 1)
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
                    base_url=f"http://127.0.0.1:{port}", trust_env=False, timeout=30
                ) as http:

                    def ready():
                        try:
                            return http.get("/api/health").is_success
                        except httpx.ConnectError:
                            return False

                    until(ready)
                    with sync_playwright() as playwright:
                        browser = playwright.chromium.launch(
                            headless=True, args=["--no-sandbox"]
                        )
                        context = browser.new_context(
                            viewport={"width": 1600, "height": 1100}
                        )
                        page = context.new_page()
                        page.on("pageerror", lambda error: errors.append(str(error)))
                        page.goto(str(http.base_url))
                        page.get_by_alt_text("原始摄像头图像").wait_for()
                        algorithm = page.get_by_label("算法", exact=True)
                        for identity in (
                            "temporal_pursuit",
                            "temporal_mpc",
                            "temporal_pursuit_avoidance",
                            "temporal_mpc_avoidance",
                        ):
                            expect(
                                algorithm.locator(f"option[value='{identity}']")
                            ).to_have_count(1)
                            algorithm.select_option(identity)
                            expect(algorithm).to_have_value(identity)
                        algorithm.select_option("manual")
                        checks.append(
                            "original and avoidance policies are four independently selectable algorithms"
                        )
                        page.get_by_role(
                            "button", name="自定义地图", exact=True
                        ).click()
                        name = page.get_by_label("地图名称", exact=True)
                        name.fill("刷新恢复验收")
                        page.get_by_label("相机高度 / m", exact=True).fill("0.38")
                        page.get_by_role("button", name="障碍物", exact=True).click()
                        canvas = page.get_by_label("地图控制点画布")

                        def place(point):
                            canvas.scroll_into_view_if_needed()
                            position = canvas.evaluate(
                                "(el, [x,y]) => { const p = new DOMPoint(x,-y).matrixTransform(el.getScreenCTM()); return [p.x,p.y]; }",
                                point,
                            )
                            page.mouse.click(*position)

                        def draft():
                            return page.evaluate(
                                "JSON.parse(localStorage.getItem('pathlab.map-draft.v1'))"
                            )

                        place([1, -1])
                        page.get_by_role("button", name="干扰线", exact=True).click()
                        page.get_by_role(
                            "button", name="新增干扰线", exact=True
                        ).click()
                        place([0, -2])
                        before = draft()
                        assert before["camera"]["height_m"] == 0.38
                        assert len(before["objects"]) == 1
                        assert len(before["design"]["distractors"][0]["waypoints"]) == 1
                        page.reload()
                        expect(name).to_have_value("刷新恢复验收", timeout=15000)
                        assert draft() == before
                        apply = page.get_by_role(
                            "button", name="应用到实验", exact=True
                        )
                        expect(apply).to_be_disabled()
                        checks.append(
                            "immediate reload restores incomplete line, target, camera and obstacle draft"
                        )

                        page.get_by_role(
                            "button", name="实验工作台", exact=True
                        ).click()
                        page.get_by_role(
                            "button", name="自定义地图", exact=True
                        ).click()
                        expect(name).to_have_value("刷新恢复验收")
                        assert draft() == before
                        page.get_by_role("button", name="干扰线", exact=True).click()
                        place([5, -2])
                        expect(apply).to_be_enabled(timeout=15000)
                        page.get_by_role("button", name="保存地图", exact=True).click()
                        until(lambda: len(http.get("/api/maps").json()) == 1)
                        saved = http.get("/api/maps").json()[0]["scene"]
                        checks.append(
                            "switching tabs retains unfinished edits; completed map saves to server"
                        )

                        apply.click()
                        page.reload()
                        page.get_by_alt_text("原始摄像头图像").wait_for()
                        expect(page.get_by_label("场景", exact=True)).to_have_value(
                            "custom"
                        )
                        with page.expect_response(
                            lambda response: response.url.endswith("/api/runs")
                            and response.request.method == "POST"
                        ) as created:
                            page.get_by_role("button", name="启动实验").click()
                        assert created.value.status == 201
                        run = created.value.json()
                        assert run["scene"] == saved
                        page.get_by_role("button", name="停止", exact=True).click()
                        until(
                            lambda: http.get(f"/api/runs/{run['id']}").json()["state"]
                            in {"cancelled", "failed", "completed"}
                        )
                        checks.append(
                            "applied scene survives reload and starts real experiment despite 2 GiB training data"
                        )

                        with (root / "runs" / run["id"] / "image-test.png").open(
                            "wb"
                        ) as handle:
                            handle.truncate(64 * 1024**2)
                        page.get_by_role(
                            "button", name="运行记录与对比", exact=True
                        ).click()
                        usage = page.get_by_label("运行记录存储", exact=True)
                        expect(usage).to_contain_text("64.")
                        page.get_by_role(
                            "button", name="选择已结束记录", exact=True
                        ).click()
                        page.once("dialog", lambda dialog: dialog.accept())
                        page.get_by_role(
                            "button", name="删除选中记录", exact=True
                        ).click()
                        expect(usage).to_contain_text("0.0 MiB / 2 GiB")
                        assert not (root / "runs" / run["id"]).exists()
                        assert http.get("/api/maps").json()[0]["scene"] == saved
                        checks.append(
                            "deleting record removes images, updates visible quota and preserves saved map"
                        )

                        page.get_by_role(
                            "button", name="自定义地图", exact=True
                        ).click()
                        page.evaluate(
                            "() => { window.savedSetItem = Storage.prototype.setItem; Storage.prototype.setItem = () => { throw new DOMException('full', 'QuotaExceededError'); }; }"
                        )
                        name.fill("存储失败也可保存")
                        expect(page.get_by_label("地图草稿保存状态")).to_contain_text(
                            "自动保存失败"
                        )
                        expect(apply).to_be_enabled(timeout=15000)
                        page.get_by_role("button", name="保存地图", exact=True).click()
                        until(lambda: len(http.get("/api/maps").json()) == 2)
                        assert any(
                            item["scene"]["name"] == "存储失败也可保存"
                            for item in http.get("/api/maps").json()
                        )
                        page.evaluate(
                            "Storage.prototype.setItem = window.savedSetItem; localStorage.setItem('pathlab.map-draft.v1', '{invalid');"
                        )
                        page.reload()
                        expect(page.get_by_label("地图草稿保存状态")).to_contain_text(
                            "无法恢复", timeout=15000
                        )
                        expect(name).to_be_visible()
                        checks.append(
                            "storage write failure and malformed draft show actionable messages without crashing"
                        )

                        fresh = browser.new_context(
                            viewport={"width": 1600, "height": 1100}
                        )
                        second = fresh.new_page()
                        second.on("pageerror", lambda error: errors.append(str(error)))
                        second.goto(str(http.base_url))
                        second.get_by_alt_text("原始摄像头图像").wait_for()
                        second.get_by_role(
                            "button", name="自定义地图", exact=True
                        ).click()
                        card = second.locator(".saved-map").filter(
                            has_text="刷新恢复验收"
                        )
                        card.get_by_role("button", name="加载", exact=True).click()
                        expect(
                            second.get_by_label("地图名称", exact=True)
                        ).to_have_value("刷新恢复验收")
                        expect(
                            second.get_by_role("button", name="应用到实验", exact=True)
                        ).to_be_enabled(timeout=15000)
                        with second.expect_download() as download:
                            second.get_by_role(
                                "button", name="导出 JSON", exact=True
                            ).click()
                        assert (
                            json.loads(Path(download.value.path()).read_text()) == saved
                        )
                        second.reload()
                        expect(
                            second.get_by_label("地图名称", exact=True)
                        ).to_have_value("刷新恢复验收", timeout=15000)
                        checks.append(
                            "fresh browser loads saved map; imported source geometry survives subsequent reload exactly"
                        )
                        for suffix in (1, 2):
                            save = second.get_by_role(
                                "button", name="保存地图", exact=True
                            )
                            expect(save).to_be_enabled(timeout=15000)
                            save.click()
                            expect(
                                second.get_by_label("地图名称", exact=True)
                            ).to_have_value(f"刷新恢复验收({suffix})")
                        copies = http.get("/api/maps").json()
                        assert len({item["scene"]["name"] for item in copies}) == len(
                            copies
                        )
                        chosen = next(
                            item
                            for item in copies
                            if item["scene"]["name"] == "刷新恢复验收(2)"
                        )
                        second.get_by_role(
                            "button", name="实验工作台", exact=True
                        ).click()
                        select = second.get_by_label("场景", exact=True)
                        select.select_option(f"map:{chosen['id']}")
                        second.get_by_alt_text("原始摄像头图像").wait_for()
                        expect(select).to_have_value(f"map:{chosen['id']}")
                        second.reload()
                        expect(select).to_have_value(
                            f"map:{chosen['id']}", timeout=15000
                        )
                        second.get_by_alt_text("原始摄像头图像").wait_for()
                        with second.expect_response(
                            lambda response: response.url.endswith("/api/runs")
                            and response.request.method == "POST"
                        ) as selected_run:
                            second.get_by_role(
                                "button", name="重置", exact=True
                            ).click()
                        assert selected_run.value.status == 201
                        selected_data = selected_run.value.json()
                        assert selected_data["scene"] == chosen["scene"]
                        http.post(
                            f"/api/runs/{selected_data['id']}/control",
                            json={"command": "stop"},
                        )
                        checks.append(
                            "duplicate saves use (1)/(2); homepage selects saved map by ID, restores selection and runs exact scene"
                        )
                        assert http.delete(f"/api/maps/{chosen['id']}").is_success
                        second.evaluate("window.dispatchEvent(new Event('focus'))")
                        expect(select).to_have_value("custom")
                        expect(
                            select.locator(f"option[value='map:{chosen['id']}']")
                        ).to_have_count(0)
                        checks.append(
                            "deleted library entry disappears; current frozen experiment scene remains usable"
                        )
                        assert not errors, errors
                        browser.close()
            finally:
                server.terminate()
                server.wait(timeout=20)
    report = {"passed": checks, "browser_errors": errors}
    (output / "report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2)
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
