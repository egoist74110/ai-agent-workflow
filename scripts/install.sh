#!/usr/bin/env bash
# 薄壳：实际逻辑全在 installer.py（唯一实现，跨平台共用）。
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if command -v python3 >/dev/null 2>&1; then
  PY=python3
elif command -v python >/dev/null 2>&1; then
  PY=python
else
  echo "需要 python3 才能运行安装器，请先安装 Python 3。" >&2
  exit 1
fi

exec "$PY" "$DIR/installer.py" install
