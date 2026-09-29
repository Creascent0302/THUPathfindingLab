"""Cross-platform entrypoint; no shell activation needed after setup."""

import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parent
VENV_PYTHON = (
    ROOT / ".venv" / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
)


def ensure_frontend():
    """A branch switch must not keep serving another version's ignored dist/."""
    frontend = ROOT / "frontend"
    entry = frontend / "dist" / "index.html"
    sources = [p for p in (frontend / "src").rglob("*") if p.is_file()]
    sources += [
        p
        for p in frontend.iterdir()
        if p.is_file() and p.suffix in {".html", ".json", ".ts"}
    ]
    if entry.is_file() and all(
        p.stat().st_mtime <= entry.stat().st_mtime for p in sources
    ):
        return
    env = os.environ.copy()
    env["PATH"] = str(VENV_PYTHON.parent) + os.pathsep + env.get("PATH", "")
    npm = shutil.which("npm", path=env["PATH"])
    if not npm or not (frontend / "node_modules").is_dir():
        raise SystemExit(
            "网页与当前代码不一致，请先运行 python scripts/setup.py 安装并构建。"
        )
    print("检测到网页源码更新，正在构建与当前平台匹配的界面…", flush=True)
    try:
        subprocess.run([npm, "run", "build"], cwd=frontend, env=env, check=True)
    except subprocess.CalledProcessError as error:
        raise SystemExit(
            "网页构建失败，请根据上面的错误修复环境，再重新运行。"
        ) from error


if __name__ == "__main__":
    if Path(sys.prefix).resolve() != (ROOT / ".venv").resolve():
        if not VENV_PYTHON.exists():
            raise SystemExit("请先运行 python scripts/setup.py 安装环境。")
        raise SystemExit(
            subprocess.call(
                [str(VENV_PYTHON), str(ROOT / "run.py"), *sys.argv[1:]], cwd=ROOT
            )
        )
    if len(sys.argv) == 1 or sys.argv[1] == "serve":
        ensure_frontend()
    from pathlab.cli import main

    main()
