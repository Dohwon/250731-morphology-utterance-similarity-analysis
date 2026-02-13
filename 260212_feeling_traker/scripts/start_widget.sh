#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

ARGS=("$@")

# WSL에서는 무테 창이 보이지 않는 경우가 있어 기본적으로 가시성 디버그 모드 사용
if [[ -n "${WSL_DISTRO_NAME:-}" ]]; then
  ARGS=(--debug-visible "${ARGS[@]}")
fi

python3 desktop_widget.py "${ARGS[@]}"
