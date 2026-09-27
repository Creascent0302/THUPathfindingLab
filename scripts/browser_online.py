"""Browser workspace regression with real files (OPFS) and a test-only API.

The browser picker and login are substituted; archive/restore, replay, streamed
writes, and native directory handles are real. Docker deployment needs a host smoke test.
"""

import json
import os
from pathlib import Path
import tempfile

from playwright.sync_api import expect, sync_playwright

from browser_support import serve_test, until


def main():
    os.environ["PATHLAB_EPHEMERAL"] = "1"
    with tempfile.TemporaryDirectory(prefix="pathlab-online-browser-") as temporary:
        root = Path(temporary)
        with (
            serve_test(root / "artifacts", root) as http,
            sync_playwright() as playwright,
        ):
            browser = playwright.chromium.launch(headless=True, args=["--no-sandbox"])
            context = browser.new_context(viewport={"width": 1440, "height": 1000})
            state = {"authenticated": False}
            context.route(
                "**/api/hosting",
                lambda route: route.fulfill(
                    json={
                        "mode": "online",
                        **state,
                        "student": "student001",
                        "expires_in_s": 14000,
                    }
                ),
            )

            def login(route):
                state["authenticated"] = route.request.method != "DELETE"
                route.fulfill(json={"student": "student001"})

            context.route("**/api/session", login)
            context.add_init_script("""
                window.showDirectoryPicker = async () => {
                  const root = await navigator.storage.getDirectory();
                  const directory = await root.getDirectoryHandle('course-test', {create:true});
                  directory.requestPermission = async () => 'granted';
                  window.testDirectory = directory;
                  return directory;
                };
            """)
            page = context.new_page()
            errors = []
            page.on("pageerror", lambda e: errors.append(str(e)))
            page.on("dialog", lambda dialog: dialog.accept())
            page.goto(str(http.base_url))
            page.get_by_label("个人访问码").fill("classroom-code")
            page.get_by_role("button", name="进入课堂", exact=True).click()
            page.get_by_role("button", name="选择本地目录", exact=True).click()
            page.get_by_alt_text("原始摄像头图像").wait_for()
            expect(page.get_by_text("最近保存：", exact=False)).to_be_visible(
                timeout=15000
            )

            scene = http.get("/api/scenes/straight").json()["scene"]
            scene["name"] = "browser-local-map"
            saved = http.post("/api/maps", json=scene).json()
            run = http.post(
                "/api/runs",
                json={"algorithm": "stop", "max_steps": 2, "realtime": False},
            ).json()["id"]
            http.post(f"/api/runs/{run}/control", json={"command": "resume"})
            until(
                lambda: http.get(f"/api/runs/{run}").json()["state"]
                in {"completed", "failed"}
            )
            page.get_by_role("button", name="立即保存到本地", exact=True).click()
            expect(
                page.get_by_text("已保存到 course-test", exact=False)
            ).to_be_visible()

            def checkpoint():
                return page.evaluate(
                    "async () => JSON.parse(await (await (await window.testDirectory.getFileHandle('pathlab-workspace.json')).getFile()).text())"
                )

            until(
                lambda: checkpoint()["revision"]
                == http.get("/api/workspace").json()["revision"]
            )
            expect(
                page.get_by_role("button", name="立即保存到本地", exact=True)
            ).to_be_enabled()
            original = checkpoint()
            assert original["format"] == "pathlab-local-v1"
            before = http.get(f"/api/results/{run}/frames/0").json()

            # A failed download cannot replace the committed local checkpoint.
            page.route("**/api/workspace/archive", lambda route: route.abort())
            page.get_by_role("button", name="立即保存到本地", exact=True).click()
            expect(page.get_by_role("alert")).to_be_visible()
            assert checkpoint() == original
            page.unroute("**/api/workspace/archive")

            # Another tab cannot become a competing directory writer.
            other = context.new_page()
            other.goto(str(http.base_url))
            other.get_by_role("button", name="选择本地目录", exact=True).click()
            expect(other.get_by_role("alert")).to_contain_text("另一个标签页")
            other.close()

            # Simulate a discarded sandbox: clean test data, then reload from disk.
            assert http.delete(f"/api/results/{run}").is_success
            assert http.delete(f"/api/maps/{saved['id']}").is_success
            page.reload()
            page.get_by_role("button", name="选择本地目录", exact=True).click()
            page.get_by_alt_text("原始摄像头图像").wait_for()
            after = http.get(f"/api/results/{run}/frames/0").json()
            assert after["image"] == before["image"]
            assert after["frame"] == before["frame"]
            assert http.get("/api/maps").json()[0]["scene"]["name"] == scene["name"]
            active = http.post("/api/runs", json={"algorithm": "manual"}).json()["id"]
            page.reload()
            page.get_by_role("button", name="选择本地目录", exact=True).click()
            expect(
                page.get_by_role("button", name="▶ 继续运行", exact=True)
            ).to_be_visible()
            page.get_by_role("button", name="停止", exact=True).click()
            until(
                lambda: http.get(f"/api/runs/{active}").json()["state"] == "cancelled"
            )
            assert not errors, errors
            print(
                json.dumps(
                    {
                        "passed": [
                            "login gate",
                            "native directory write",
                            "maps and run checkpoint",
                            "failed-save rollback",
                            "single-tab writer lock",
                            "restore and real replay",
                            "refresh reconnects active run",
                        ],
                        "page_errors": errors,
                    },
                    ensure_ascii=False,
                )
            )
            context.close()
            browser.close()


if __name__ == "__main__":
    main()
