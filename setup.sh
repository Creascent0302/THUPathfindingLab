#!/usr/bin/env bash
# One entrypoint for Linux, WSL and macOS; no activation or global pip needed.
set -euo pipefail

project_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$project_dir"

case "$(uname -s)" in
    Linux|Darwin) ;;
    *) echo "请在 Linux、macOS 或 Windows 的 WSL Ubuntu 终端运行。" >&2; exit 1 ;;
esac

# Prefer an existing environment, then a supported Python on PATH. Explicit
# Homebrew paths also work before a newly installed brew is added to PATH.
for candidate in "$project_dir/.venv/bin/python" \
    python3.13 python3.12 python3.11 python3.10 python3 \
    /opt/homebrew/bin/python3.13 /usr/local/bin/python3.13; do
    if command -v "$candidate" >/dev/null 2>&1 && "$candidate" -I -c \
        'import sys, sysconfig; sys.exit(not (sys.implementation.name == "cpython" and (3, 10) <= sys.version_info[:2] <= (3, 13) and not sysconfig.get_config_var("Py_GIL_DISABLED")))' \
        >/dev/null 2>&1; then
        exec "$candidate" -I "$project_dir/scripts/setup.py" "$@"
    fi
done

cat >&2 <<'HELP'
未找到兼容的 Python 3.10～3.13（标准 CPython）。
Ubuntu / WSL：sudo apt update && sudo apt install -y python3 python3-venv python3-pip
macOS：安装 Python 3.13 的官方 universal2 安装包，或运行 brew install python@3.13。
安装后重新打开终端，再运行 bash setup.sh --run。
详细步骤见 docs/student-local.md。
HELP
exit 1
