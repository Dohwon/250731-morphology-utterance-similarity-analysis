#!/usr/bin/env bash
set -euo pipefail
BASE_DIR="$(cd "$(dirname "$0")/.." && pwd)"
LOG_FILE="$BASE_DIR/project_memory/session_log.md"
NOW="$(date '+%Y-%m-%d %H:%M')"

echo -e "\n## ${NOW}\n\n- 세션 시작\n" >> "$LOG_FILE"
echo "updated: $LOG_FILE"
