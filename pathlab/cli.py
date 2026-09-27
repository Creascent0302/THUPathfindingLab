"""One local service; the same launcher works in source and native releases."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from .registry import DATA_ROOT, ROOT, registry


def main():
    # Native releases reuse their bundled interpreter for isolated student workers.
    if len(sys.argv) == 3 and sys.argv[1] == "--worker":
        from .worker import serve_plugin

        sys.path.append(str(Path.cwd()))
        serve_plugin(sys.argv[2])
        return

    parser = argparse.ArgumentParser(description="智能交通创新实践 · 学生实验平台")
    sub = parser.add_subparsers(dest="command")
    serve = sub.add_parser("serve", help="启动本地或内网工作台")
    serve.add_argument("--port", type=int, default=8000)
    address = serve.add_mutually_exclusive_group()
    address.add_argument("--host", default="127.0.0.1")
    address.add_argument("--lan", action="store_true", help="允许同一可信内网访问")
    serve.add_argument("--data-dir", type=Path, default=DATA_ROOT, help="实验数据目录")
    sub.add_parser("doctor", help="显示运行环境")
    args = parser.parse_args()
    if args.command == "doctor":
        from .storage import environment

        print(
            json.dumps(
                {
                    **environment(),
                    "data_directory": str(DATA_ROOT),
                    "frontend_built": (ROOT / "frontend/dist/index.html").is_file(),
                    "algorithms": list(registry()),
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return

    import uvicorn
    from .api import create_app

    if not (ROOT / "frontend/dist/index.html").is_file():
        raise SystemExit("前端未构建，请先运行 python scripts/setup.py")
    port = getattr(args, "port", 8000)
    if not 1 <= port <= 65535:
        parser.error("端口须为 1～65535")
    host = (
        "0.0.0.0" if getattr(args, "lan", False) else getattr(args, "host", "127.0.0.1")
    )
    root = getattr(args, "data_dir", DATA_ROOT).expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)
    print(f"本机浏览器打开 http://127.0.0.1:{port}；数据保存到 {root}", flush=True)
    if host != "127.0.0.1":
        print(
            f"内网访问：http://本机内网IP:{port}（共享同一工作台，仅供可信同学使用）",
            flush=True,
        )
    uvicorn.run(create_app(root), host=host, port=port, log_level="info")


if __name__ == "__main__":
    main()
