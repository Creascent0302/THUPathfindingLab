"""Install a project-local environment on Linux/macOS, optionally then serve."""

import argparse
import os
from pathlib import Path
import platform
import shlex
import shutil
import subprocess
import sys
import sysconfig
import venv

ROOT = Path(__file__).resolve().parent.parent


def prepare_environment():
    environment = ROOT / ".venv"
    python = environment / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    if not environment.exists():
        print(f"创建虚拟环境：{environment}", flush=True)
        try:
            venv.EnvBuilder(with_pip=True).create(environment)
        except (OSError, subprocess.CalledProcessError) as error:
            raise SystemExit(
                "创建 .venv 失败。Ubuntu/WSL 请先安装 python3-venv；"
                "其他情况请查看上方错误。修复步骤见 docs/student-local.md。"
            ) from error
    # Never let a stale/copied environment redirect pip to another interpreter.
    probe = (
        "import sys, sysconfig; from pathlib import Path; "
        "sys.exit(not (sys.prefix != sys.base_prefix "
        "and Path(sys.prefix).resolve() == Path(sys.argv[1]).resolve() "
        "and (3, 10) <= sys.version_info[:2] <= (3, 13) "
        "and sys.implementation.name == 'cpython' "
        "and not sysconfig.get_config_var('Py_GIL_DISABLED')))"
    )
    try:
        subprocess.run(
            [str(python), "-I", "-c", probe, str(environment)],
            check=True,
            capture_output=True,
        )
    except (OSError, subprocess.CalledProcessError) as error:
        raise SystemExit(
            "现有 .venv 不可用或 Python 版本不兼容。请按 docs/student-local.md "
            "的“重建环境”步骤备份 .venv 后重新配置；不会自动删除已有文件。"
        ) from error
    return python


def main(argv=None):
    parser = argparse.ArgumentParser(description="安装寻迹实验室运行环境")
    parser.add_argument(
        "--skip-frontend", action="store_true", help="仅安装 Python（无界面评测）"
    )
    parser.add_argument(
        "--mirror",
        action="store_true",
        help="使用清华 PyPI 镜像与 npmmirror，适合国内网络",
    )
    parser.add_argument("--run", action="store_true", help="安装成功后立即启动网页平台")
    args = parser.parse_args(argv)
    if args.run and args.skip_frontend:
        parser.error("--run 需要网页，不能与 --skip-frontend 同时使用")
    if (
        not (3, 10) <= sys.version_info[:2] <= (3, 13)
        or sys.implementation.name != "cpython"
        or sysconfig.get_config_var("Py_GIL_DISABLED")
    ):
        raise SystemExit(
            "请使用标准 CPython 3.10–3.13，或运行 bash setup.sh 自动选择。"
        )
    if sys.platform == "darwin" and int(platform.mac_ver()[0].split(".")[0]) < 13:
        raise SystemExit("当前 OpenCV 预编译依赖需要 macOS 13 或以上，请先升级系统。")
    python = prepare_environment()
    env = os.environ.copy()
    env.pop("PYTHONHOME", None)
    env.pop("PYTHONPATH", None)
    env["PATH"] = str(python.parent) + os.pathsep + env.get("PATH", "")
    env["VIRTUAL_ENV"] = str(ROOT / ".venv")
    env["PYTHONNOUSERSITE"] = "1"
    env["PIP_REQUIRE_VIRTUALENV"] = "true"
    env["PIP_CACHE_DIR"] = str(ROOT / ".cache" / "pip")
    env["npm_config_cache"] = str(ROOT / ".cache" / "npm")

    def execute(argv, cwd=ROOT):
        print(shlex.join(map(str, argv)), flush=True)
        subprocess.run(list(map(str, argv)), cwd=cwd, env=env, check=True)

    pip_source = (
        ["--index-url", "https://pypi.tuna.tsinghua.edu.cn/simple"]
        if args.mirror
        else []
    )
    execute([python, "-m", "ensurepip", "--upgrade"])
    execute([python, "-m", "pip", "install", *pip_source, "--upgrade", "pip"])
    packages = [] if args.skip_frontend else ["nodejs-wheel==22.16.0"]
    execute(
        [
            python,
            "-m",
            "pip",
            "install",
            *pip_source,
            "--only-binary=:all:",
            "-r",
            "requirements.lock",
            *packages,
        ]
    )
    execute([python, "-m", "pip", "check"])
    if not args.skip_frontend:
        # A pinned, project-local Node removes a second manual installation step.
        npm = shutil.which("npm", path=env["PATH"])
        if not npm:
            raise SystemExit("Node 工具安装失败。可手动安装 Node.js 22 后重试。")
        npm_source = (
            ["--registry=https://registry.npmmirror.com"] if args.mirror else []
        )
        execute(
            [
                npm,
                "ci"
                if (ROOT / "frontend" / "package-lock.json").exists()
                else "install",
                *npm_source,
                "--no-audit",
                "--no-fund",
            ],
            ROOT / "frontend",
        )
        execute([npm, "run", "build"], ROOT / "frontend")
    execute([python, ROOT / "run.py", "doctor"])
    print(
        "\n安装完成，无需激活虚拟环境。以后在项目目录运行：\n"
        ".venv/bin/python run.py\n浏览器：http://127.0.0.1:8000",
        flush=True,
    )
    if args.run:
        execute([python, ROOT / "run.py"])


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        raise SystemExit(130)
    except (OSError, subprocess.CalledProcessError) as error:
        raise SystemExit(
            f"配置或启动失败：{error}\n请查看上方错误；安装中断后可以重新运行 "
            "bash setup.sh。网络较慢时可加 --mirror。"
        ) from error
