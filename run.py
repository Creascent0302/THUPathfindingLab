"""Cross-platform entrypoint; no shell activation needed after setup."""

from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parent
VENV_PYTHON = (
    ROOT / ".venv" / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
)

if __name__ == "__main__":
    if Path(sys.prefix).resolve() != (ROOT / ".venv").resolve():
        if not VENV_PYTHON.exists():
            raise SystemExit("请先运行 python scripts/setup.py 安装环境。")
        raise SystemExit(
            subprocess.call(
                [str(VENV_PYTHON), str(ROOT / "run.py"), *sys.argv[1:]], cwd=ROOT
            )
        )
    from pathlab.cli import main

    main()
