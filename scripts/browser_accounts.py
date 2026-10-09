"""Chromium account acceptance against disposable test data, never a public app."""

import re
import tempfile

from playwright.sync_api import expect, sync_playwright

from browser_support import ROOT, serve_test, until


def login(page, username, password="browser-test-password"):
    page.get_by_label("账号", exact=True).fill(username)
    page.get_by_label("密码", exact=True).fill(password)
    page.get_by_role("button", name="登录", exact=True).click()


def main():
    output = ROOT / ".cache" / "browser-accounts"
    output.mkdir(parents=True, exist_ok=True)
    errors = []
    with tempfile.TemporaryDirectory(prefix="pathlab-accounts-browser-") as data:
        with (
            serve_test(data, output, accounts=True) as http,
            sync_playwright() as playwright,
        ):
            base = str(http.base_url).rstrip("/") + "/"
            browser = playwright.chromium.launch(headless=True, args=["--no-sandbox"])
            pages = [
                browser.new_page(viewport={"width": 1440, "height": 1000})
                for _ in range(4)
            ]
            teacher, alice, bob, new_student = pages
            for page in pages:
                page.on("pageerror", lambda error: errors.append(str(error)))
                page.on("dialog", lambda dialog: dialog.accept())
                page.goto(str(http.base_url))
                page.get_by_role("button", name="登录", exact=True).wait_for()
            alice.screenshot(path=str(output / "login.png"))
            for page, username in (
                (teacher, "teacher"),
                (alice, "alice"),
                (bob, "bob"),
            ):
                login(page, username)
                page.get_by_alt_text("原始摄像头图像").wait_for()
            headers = {
                "X-PathLab-Request": "1",
                "Origin": str(http.base_url).rstrip("/"),
            }
            scene = alice.request.get(base + "api/scenes/straight").json()["scene"]
            scene["name"] = "Alice 私有测试地图"
            assert (
                alice.request.post(
                    base + "api/maps", data=scene, headers=headers
                ).status
                == 201
            )
            assert bob.request.get(base + "api/maps").json() == []
            alice.reload()
            alice.get_by_alt_text("原始摄像头图像").wait_for()
            for page in (alice, bob):
                page.get_by_role("button", name="▶ 启动实验", exact=True).click()
                page.get_by_role("button", name="Ⅱ 暂停", exact=True).wait_for()

            def result(page):
                return page.request.get(base + "api/results").json()[0]

            until(lambda: len(alice.request.get(base + "api/results").json()) == 1)
            alice_id, bob_id = result(alice)["episode_id"], result(bob)["episode_id"]
            assert alice_id != bob_id
            assert bob.request.get(base + f"api/results/{alice_id}").status == 404
            until(
                lambda: bob.request.get(base + f"api/runs/{bob_id}").json()[
                    "frame_count"
                ]
                > 2
            )
            teacher.get_by_role("button", name="账号与用户管理", exact=True).click()
            row = teacher.get_by_role("row").filter(has_text="alice")
            row.get_by_role("button", name="停用", exact=True).click()
            alice.get_by_role("button", name="登录", exact=True).wait_for(timeout=15000)
            expect(bob.get_by_role("button", name="Ⅱ 暂停", exact=True)).to_be_visible()
            row.get_by_role("button", name="启用", exact=True).click()
            row.get_by_role("button", name="停用", exact=True).wait_for()
            row.get_by_role("button", name="重置密码", exact=True).click()
            notice = teacher.get_by_role("textbox", name="请复制保存（关闭后不再展示）")
            expect(notice).to_have_value(re.compile("临时密码"))
            temporary = notice.input_value().split("临时密码：", 1)[1].strip()
            login(alice, "alice", temporary)
            alice.get_by_role("heading", name="请先修改临时密码").wait_for()
            alice.get_by_label("原密码", exact=True).fill(temporary)
            alice.get_by_label("新密码", exact=True).fill("changed-browser-password")
            alice.get_by_label("确认新密码", exact=True).fill(
                "changed-browser-password"
            )
            alice.get_by_role("button", name="保存密码并重新登录").click()
            login(alice, "alice", "changed-browser-password")
            alice.get_by_alt_text("原始摄像头图像").wait_for()
            assert (
                alice.request.get(base + "api/maps").json()[0]["scene"]["name"]
                == scene["name"]
            )
            teacher.get_by_label("可注册人数").fill("1")
            teacher.get_by_role("button", name="生成邀请码", exact=True).click()
            expect(notice).to_have_value(re.compile("邀请码"))
            code = notice.input_value().split("邀请码：", 1)[1].splitlines()[0]
            new_student.get_by_role("button", name="有邀请码，注册账号").click()
            new_student.get_by_label("账号", exact=True).fill("charlie")
            new_student.get_by_label("密码", exact=True).fill("new-student-password")
            new_student.get_by_label("教师提供的邀请码").fill(code)
            new_student.get_by_role("button", name="注册并登录").click()
            new_student.get_by_alt_text("原始摄像头图像").wait_for()
            assert new_student.request.get(base + "api/maps").json() == []
            alice.get_by_role("button", name="自定义地图", exact=True).click()
            alice.get_by_role("button", name="退出", exact=True).click()
            login(alice, "bob")
            alice.get_by_alt_text("原始摄像头图像").wait_for()
            expect(
                alice.get_by_role("button", name="实验工作台", exact=True)
            ).to_have_class("selected")
            assert alice.request.get(base + "api/maps").json() == []
            bob.screenshot(path=str(output / "parallel-workbench.png"), full_page=True)
            new_student.set_viewport_size({"width": 390, "height": 844})
            new_student.get_by_role("button", name="账号与存储", exact=True).click()
            expect(
                new_student.get_by_role("dialog", name="账号与工作区")
            ).to_be_visible()
            new_student.screenshot(
                path=str(output / "account-mobile.png"), full_page=True
            )
            assert not errors, errors
            browser.close()
    print(
        "账号浏览器验收通过：登录、双账号并行、私有地图、停用断开、重置/修改密码、邀请码注册、同浏览器账号切换、手机布局；0 页面异常。"
    )


if __name__ == "__main__":
    main()
