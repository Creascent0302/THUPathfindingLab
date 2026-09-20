"""Real Chromium acceptance of configurable objects, inertia, and paired batches."""

import json
import socket
import subprocess
import sys
import tempfile

import httpx
from playwright.sync_api import expect, sync_playwright

from browser_smoke import ROOT, until


def main():
    output = ROOT / "artifacts" / "browser-evaluation"
    output.mkdir(parents=True, exist_ok=True)
    checks, errors = [], []
    with tempfile.TemporaryDirectory(prefix="pathlab-evaluation-") as data:
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
                    base_url=f"http://127.0.0.1:{port}", timeout=30, trust_env=False
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
                        page = browser.new_page(
                            viewport={"width": 1600, "height": 1100}
                        )
                        page.on("pageerror", lambda error: errors.append(str(error)))
                        page.on("dialog", lambda dialog: dialog.accept())
                        page.goto(str(http.base_url))
                        page.get_by_alt_text("原始摄像头图像").wait_for()
                        scene = http.get("/api/scenes/straight?seed=7").json()["scene"]
                        assert (
                            scene["render_version"] == "3"
                            and len(scene["objects"]) >= 2
                        )
                        assert scene["vehicle"]["motion_model"] == "inertial_v2"
                        checks.append(
                            "new scene uses actual 3D objects and inertial dynamics"
                        )
                        page.screenshot(
                            path=str(output / "workbench.png"), full_page=True
                        )

                        page.get_by_text("车辆惯性与制动", exact=True).click()
                        page.get_by_label("制动减速度 / m/s²", exact=True).fill("0.8")
                        page.get_by_role(
                            "button", name="应用车辆设置", exact=True
                        ).click()
                        expect(page.get_by_label("场景", exact=True)).to_have_value(
                            "custom"
                        )
                        checks.append(
                            "vehicle controls apply as a validated custom scene"
                        )

                        page.get_by_role(
                            "button", name="自定义地图", exact=True
                        ).click()
                        page.get_by_label("地图名称", exact=True).fill(
                            "惯性与物件验收图"
                        )
                        page.get_by_role("button", name="障碍物", exact=True).click()
                        page.get_by_label("自动物件数量", exact=True).fill("3")
                        page.get_by_role(
                            "button", name="重新自动布置", exact=True
                        ).click()
                        checks.append("automatic configurable clutter placement")
                        page.get_by_role("button", name="清空物件", exact=True).click()
                        page.get_by_label("添加物件类型").select_option("box")
                        page.get_by_role("button", name="添加物件", exact=True).click()
                        page.get_by_label("物件高度", exact=True).fill("0.7")
                        expect(
                            page.get_by_role("button", name="保存地图", exact=True)
                        ).to_be_enabled(timeout=10000)
                        page.get_by_role("button", name="保存地图", exact=True).click()
                        until(lambda: len(http.get("/api/maps").json()) == 1)
                        saved = http.get("/api/maps").json()[0]
                        assert saved["scene"]["objects"][0]["kind"] == "box"
                        assert saved["scene"]["objects"][0]["height_m"] == 0.7
                        assert saved["scene"]["vehicle"]["braking_mps2"] == 0.8
                        checks.append(
                            "custom object and inertia settings persist in saved map"
                        )
                        page.screenshot(
                            path=str(output / "map-editor.png"), full_page=True
                        )

                        page.get_by_role("button", name="批量评测", exact=True).click()
                        page.get_by_label("批次名称", exact=True).fill("浏览器配对验收")
                        page.get_by_label("测试种子", exact=True).fill("901")
                        page.get_by_label("单次最大帧数", exact=True).fill("6")
                        builtins = page.locator("fieldset").filter(
                            has=page.locator("legend", has_text="内置地图")
                        )
                        for checkbox in builtins.get_by_role("checkbox").all():
                            checkbox.uncheck()
                        page.get_by_role(
                            "checkbox", name="惯性与物件验收图", exact=True
                        ).check()
                        page.get_by_role(
                            "button", name="启动批量评测", exact=True
                        ).click()
                        until(lambda: len(http.get("/api/benchmarks").json()) == 1)
                        batch_id = http.get("/api/benchmarks").json()[0]["id"]

                        def done():
                            return (
                                http.get(f"/api/benchmarks/{batch_id}").json()["state"]
                                == "completed"
                            )

                        # Navigate away while its independent workers finish.
                        page.get_by_role(
                            "button", name="实验工作台", exact=True
                        ).click()
                        until(done, timeout=90)
                        batch = http.get(f"/api/benchmarks/{batch_id}").json()
                        assert batch["summary"]["comparable"]
                        assert batch["summary"]["finished"] == 2
                        assert all(
                            item["metrics"] and item["state"] == "completed"
                            for item in batch["items"]
                        )
                        assert all(
                            item["metrics"]["score"]["total"] <= 49
                            for item in batch["items"]
                        )
                        assert (
                            batch["cases"][0]["scene"]["vehicle"]["braking_mps2"] == 0.8
                        )
                        checks.append(
                            "paired batch uses saved physics, survives navigation, retains timeouts"
                        )
                        for kind in ("json", "csv"):
                            exported = http.get(
                                f"/api/benchmarks/{batch_id}/export?format={kind}"
                            )
                            exported.raise_for_status()
                            assert "test_set_sha256" in exported.text
                        checks.append(
                            "batch JSON and CSV export include reproducibility identity"
                        )
                        page.get_by_role("button", name="批量评测", exact=True).click()
                        expect(
                            page.get_by_text("全量配对结果；执行失败计零分", exact=True)
                        ).to_be_visible(timeout=10000)
                        page.screenshot(
                            path=str(output / "comparison.png"), full_page=True
                        )
                        page.get_by_role(
                            "button", name="回放", exact=True
                        ).first.click()
                        expect(page.get_by_label("回放帧", exact=True)).to_be_visible(
                            timeout=10000
                        )
                        checks.append("batch results open real recorded replay")

                        page.get_by_role("button", name="批量评测", exact=True).click()
                        page.get_by_label("批次名称", exact=True).fill("取消验收")
                        page.get_by_label("单次最大帧数", exact=True).fill("4000")
                        page.get_by_role(
                            "button", name="启动批量评测", exact=True
                        ).click()
                        until(lambda: len(http.get("/api/benchmarks").json()) == 2)
                        page.get_by_role("button", name="取消批次", exact=True).click()
                        cancelled = next(
                            b
                            for b in http.get("/api/benchmarks").json()
                            if b["name"] == "取消验收"
                        )
                        assert (
                            cancelled["state"] == "cancelled"
                            and not cancelled["summary"]["comparable"]
                        )
                        checks.append("cancelled batch has no misleading rank")
                        assert not errors, errors
                        checks.append("no uncaught browser errors")
                        browser.close()
            finally:
                server.terminate()
                try:
                    server.wait(timeout=12)
                except subprocess.TimeoutExpired:
                    server.kill()
                    server.wait()
    report = {"checks": checks, "errors": errors}
    (output / "report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
