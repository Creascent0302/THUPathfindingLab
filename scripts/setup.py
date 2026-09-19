"""One-time setup, for Windows and Linux; run from any working directory."""

import argparse
import os
from pathlib import Path
import shutil
import subprocess
import sys
import venv

ROOT = Path(__file__).resolve().parent.parent


def main():
    parser = argparse.ArgumentParser(description="安装寻迹实验室运行环境")
    parser.add_argument(
        "--skip-frontend", action="store_true", help="仅安装 Python（无界面评测）"
    )
    parser.add_argument(
        "--mirror",
        action="store_true",
        help="使用清华 PyPI 镜像与 npmmirror，适合国内网络",
    )
    args = parser.parse_args()
    if not (3, 10) <= sys.version_info[:2] <= (3, 13):
        raise SystemExit("请使用 Python 3.10–3.13。")
    environment = ROOT / ".venv"
    if not environment.exists():
        print("创建项目虚拟环境…", flush=True)
        venv.EnvBuilder(with_pip=True).create(environment)
    binaries = environment / ("Scripts" if os.name == "nt" else "bin")
    python = binaries / ("python.exe" if os.name == "nt" else "python")
    env = os.environ.copy()
    env["PATH"] = str(binaries) + os.pathsep + env.get("PATH", "")
    env["PIP_CACHE_DIR"] = str(ROOT / ".cache" / "pip")
    env["npm_config_cache"] = str(ROOT / ".cache" / "npm")

    def execute(argv, cwd=ROOT):
        print(" ".join(map(str, argv)), flush=True)
        subprocess.run(list(map(str, argv)), cwd=cwd, env=env, check=True)

    pip_source = (
        ["--index-url", "https://pypi.tuna.tsinghua.edu.cn/simple"]
        if args.mirror
        else []
    )
    execute([python, "-m", "pip", "install", *pip_source, "-r", "requirements.lock"])
    if not args.skip_frontend:
        # A pinned, project-local Node removes a second manual installation step.
        execute([python, "-m", "pip", "install", *pip_source, "nodejs-wheel==22.16.0"])
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
    print("\n安装完成。运行：python run.py\n浏览器：http://127.0.0.1:8000", flush=True)


if __name__ == "__main__":
    main()
