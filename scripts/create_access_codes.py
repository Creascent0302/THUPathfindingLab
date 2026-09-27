"""Create individual classroom access codes; never print credentials to logs."""

import argparse
import json
import os
from pathlib import Path
import secrets


def main():
    parser = argparse.ArgumentParser(description="生成学生个人访问码，仅保存到指定文件")
    parser.add_argument("--count", type=int, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if not 1 <= args.count <= 1000:
        parser.error("count 必须在 1～1000")
    data = {
        f"student{i:03d}": secrets.token_urlsafe(24) for i in range(1, args.count + 1)
    }
    descriptor = os.open(args.output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w") as handle:
        json.dump(data, handle, indent=2)
        handle.write("\n")
    print(
        f"已创建 {args.count} 个访问码；请从 {args.output} 分别发给学生，不要公开该文件。"
    )


if __name__ == "__main__":
    main()
