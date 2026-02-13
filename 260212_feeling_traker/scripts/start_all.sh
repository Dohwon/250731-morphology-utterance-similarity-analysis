#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
python3 server.py &
SERVER_PID=$!
sleep 1
python3 desktop_widget.py || true
kill $SERVER_PID 2>/dev/null || true
