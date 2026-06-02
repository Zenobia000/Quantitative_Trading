#!/usr/bin/env bash
# 一鍵啟動 Scrum 看板伺服器。
#
#   ./tools/scrum_board/start.sh            # 綁 0.0.0.0:8765（區網可達）
#   ./tools/scrum_board/start.sh 9000       # 換 port
#   HOST=127.0.0.1 ./tools/scrum_board/start.sh   # 鎖回本機
#
# 自動定位 repo 內的 venv python，無需先 activate。
set -euo pipefail

PORT="${1:-8765}"
HOST="${HOST:-0.0.0.0}"

# 由腳本位置回推 repo 根目錄（tools/scrum_board/ → ../../）
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# 找可用的 python：優先 repo venv，否則系統 python3
PY="$REPO_ROOT/backtest_platform/.venv/bin/python"
if [[ ! -x "$PY" ]]; then
  PY="$(command -v python3 || command -v python)"
fi

# 顯示本機區網 IP（方便從別台機器連）
IP="$(hostname -I 2>/dev/null | awk '{print $1}' || true)"
echo "[start.sh] python : $PY"
echo "[start.sh] 看板    : http://127.0.0.1:$PORT/"
if [[ "$HOST" == "0.0.0.0" && -n "$IP" ]]; then
  echo "[start.sh] 區網    : http://$IP:$PORT/"
fi

exec "$PY" "$SCRIPT_DIR/server.py" --host "$HOST" --port "$PORT"
