"""Build a native student release on the target OS; never package the worktree."""

from __future__ import annotations

import ast
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import venv
import zipfile

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / ".cache" / "student-build"
ENV = ROOT / ".cache" / "student-build-env"
TOOLS = [
    "Cython==3.1.2",
    "pyinstaller==6.14.1",
    "setuptools==80.9.0",
    "pyinstaller-hooks-contrib==2026.7",
    "altgraph==0.17.5",
]
PUBLIC = {"__init__", "sdk"}


def run(*command, cwd=ROOT, env=None):
    subprocess.run([str(part) for part in command], cwd=cwd, env=env, check=True)


def main():
    python = ENV / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    if not python.exists():
        venv.EnvBuilder(with_pip=True).create(ENV)
    run(python, "-m", "pip", "install", "-r", ROOT / "requirements.lock", *TOOLS)
    environment = os.environ.copy()
    environment["PATH"] = (
        str(ROOT / ".venv" / ("Scripts" if os.name == "nt" else "bin"))
        + os.pathsep
        + environment["PATH"]
    )
    npm = shutil.which("npm", path=environment["PATH"])
    if not npm:
        raise SystemExit("请先运行 python scripts/setup.py，或安装 Node.js 22")
    run(npm, "run", "build", cwd=ROOT / "frontend", env=environment)
    stage = CACHE / "stage"
    if stage.exists():
        shutil.rmtree(stage)
    (stage / "pathlab").mkdir(parents=True)
    hidden = {
        "uvicorn.logging",
        "uvicorn.loops.auto",
        "uvicorn.protocols.http.auto",
        "uvicorn.protocols.http.h11_impl",
        "uvicorn.protocols.websockets.auto",
        "uvicorn.protocols.websockets.websockets_impl",
        "uvicorn.lifespan.on",
        "numpy",
        "cv2",
        "python_multipart",
        "multipart",
    }
    private = []
    for path in sorted((ROOT / "pathlab").glob("*.py")):
        shutil.copy2(path, stage / "pathlab" / path.name)
        hidden.add(f"pathlab.{path.stem}")
        if path.stem not in PUBLIC:
            private.append(path.stem)
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, ast.Import):
                hidden.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and not node.level and node.module:
                hidden.add(node.module)
    hidden.discard("__future__")
    hidden.discard("collections.abc")  # Alias supplied by the collections package.
    hidden.update(
        {
            "math",
            "statistics",
            "random",
            "heapq",
            "bisect",
            "itertools",
            "functools",
            "fractions",
        }
    )
    # Preserve Python annotations/signatures used by Pydantic and FastAPI.
    (stage / "compile.py").write_text(
        "from setuptools import setup, Extension\nfrom Cython.Build import cythonize\n"
        f"names = {private!r}\n"
        'setup(ext_modules=cythonize([Extension("pathlab." + name, ["pathlab/" + name + ".py"]) for name in names],\n'
        '    compiler_directives={"language_level": 3, "annotation_typing": False, "binding": True}, nthreads=2))\n',
        encoding="utf-8",
    )
    # Avoid debug symbols/source paths in shipped native extensions.
    compile_env = os.environ.copy()
    if os.name != "nt":
        compile_env["CFLAGS"] = "-O2 -g0"
    run(
        python,
        "compile.py",
        "build_ext",
        "--inplace",
        "--parallel",
        "2",
        cwd=stage,
        env=compile_env,
    )
    for name in private:
        (stage / "pathlab" / f"{name}.py").unlink()
    (stage / "entry.py").write_text(
        "from pathlab.cli import main\nmain()\n", encoding="utf-8"
    )
    command = [
        python,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--onedir",
        "--name",
        "PathLab",
        "--distpath",
        CACHE / "dist",
        "--workpath",
        CACHE / "freeze",
        "--specpath",
        stage,
        "--paths",
        stage,
        "--noupx",
    ]
    for module in sorted(hidden):
        command.extend(["--hidden-import", module])
    for name in ["numpy", "opencv-python-headless", "fastapi", "pydantic", "uvicorn"]:
        command.extend(["--copy-metadata", name])
    for source, destination in [
        ("frontend/dist", "frontend/dist"),
        ("student_template/algorithm.py", "student_template"),
        ("docs/student-guide.md", "docs"),
    ]:
        command.extend(["--add-data", f"{ROOT / source}{os.pathsep}{destination}"])
    command.append(stage / "entry.py")
    run(*command, cwd=stage)
    release = (
        ROOT
        / "release"
        / f"PathLab-{platform.system().lower()}-{platform.machine().lower()}"
    )
    release.parent.mkdir(exist_ok=True)
    if release.exists():
        shutil.rmtree(release)
    shutil.copytree(CACHE / "dist" / "PathLab", release)
    shutil.copy2(ROOT / "docs" / "student-local.md", release / "使用说明.md")
    shutil.copytree(
        ROOT / "student_template",
        release / "student_template",
        ignore=shutil.ignore_patterns("__pycache__", "stdio.py"),
    )
    sdk = release / "sdk" / "pathlab"
    sdk.mkdir(parents=True)
    for name in PUBLIC:
        shutil.copy2(ROOT / "pathlab" / f"{name}.py", sdk / f"{name}.py")
    for name in ["student-guide.md", "protocol.md", "evaluation.md"]:
        shutil.copy2(ROOT / "docs" / name, release / name)
    # Distribute required third-party attribution, including vendored wheels.
    notices = release / "licenses"
    notices.mkdir()
    for package in ENV.rglob("*.dist-info"):
        for path in package.rglob("*"):
            if path.is_file() and any(
                word in path.name.lower() for word in ["license", "copying", "notice"]
            ):
                dest = notices / package.name / path.relative_to(package)
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(path, dest)
    python_license = Path(sys.base_prefix) / "LICENSE.txt"
    if not python_license.is_file():
        python_license = (
            Path(sys.base_prefix)
            / "lib"
            / f"python{sys.version_info.major}.{sys.version_info.minor}"
            / "LICENSE.txt"
        )
    if not python_license.is_file():
        raise SystemExit(
            "请将当前 Python 发行版的 LICENSE.txt 放到解释器根目录后再打包"
        )
    shutil.copy2(python_license, notices / "python.txt")
    shutil.copy2(ROOT / "frontend" / "FONT-LICENSE.txt", notices / "font.txt")
    for name in ["react", "react-dom", "scheduler"]:
        path = ROOT / "frontend" / "node_modules" / name / "LICENSE"
        if path.exists():
            shutil.copy2(path, notices / f"{name}.txt")
    # Fail closed if a private module was frozen as recoverable Python bytecode.
    from PyInstaller.archive.readers import CArchiveReader

    executable = release / ("PathLab.exe" if os.name == "nt" else "PathLab")
    archive = CArchiveReader(str(executable))
    pyz_name = next(name for name in archive.toc if name.endswith(".pyz"))
    pyz = archive.open_embedded_archive(pyz_name)
    for name in private:
        if f"pathlab.{name}" in pyz.toc:
            raise RuntimeError(f"私有模块进入了 Python 字节码归档：{name}")
        if not any((release / "_internal" / "pathlab").glob(name + ".*")):
            raise RuntimeError(f"缺少编译模块：{name}")
    for path in (release / "_internal" / "pathlab").rglob("*"):
        if path.suffix in {".py", ".pyc", ".c", ".cpp"} and path.stem not in PUBLIC:
            raise RuntimeError(f"发行包意外包含后端源码：{path}")
    files = {
        str(p.relative_to(release)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(release.rglob("*"))
        if p.is_file()
    }
    (release / "manifest.json").write_text(
        json.dumps(
            {
                "platform": platform.platform(),
                "python": sys.version,
                "source_sha256": {
                    str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                    for p in sorted((ROOT / "pathlab").glob("*.py"))
                },
                "private_modules": private,
                "files": files,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    destination = release.with_suffix(".zip")
    with zipfile.ZipFile(destination, "w", zipfile.ZIP_DEFLATED) as bundle:
        for path in sorted(release.rglob("*")):
            if path.is_file():
                bundle.write(path, path.relative_to(release.parent))
    digest = hashlib.sha256(destination.read_bytes()).hexdigest()
    destination.with_suffix(".zip.sha256").write_text(
        f"{digest}  {destination.name}\n", encoding="utf-8"
    )
    print(f"学生发行包：{destination}\nSHA256: {digest}")


if __name__ == "__main__":
    # The reader used for the final archive audit lives in the isolated build env.
    target = ENV / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    if Path(sys.prefix).resolve() != ENV.resolve():
        if not target.exists():
            venv.EnvBuilder(with_pip=True).create(ENV)
        raise SystemExit(subprocess.call([str(target), str(Path(__file__).resolve())]))
    main()
