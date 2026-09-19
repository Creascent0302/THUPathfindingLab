"""Install the optional CPU learning runtime into the existing project venv."""

from pathlib import Path
import os
import subprocess

ROOT = Path(__file__).resolve().parents[1]
python = ROOT / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
if not python.is_file():
    raise SystemExit("请先运行 python scripts/setup.py --mirror")
subprocess.run(
    [
        str(python),
        "-m",
        "pip",
        "install",
        "torch==2.7.1",
        "--index-url",
        "https://download.pytorch.org/whl/cpu",
    ],
    check=True,
)
print("学习环境就绪：python run.py learning collect --help；现有权重可直接在前端选择运行")
