"""Scrum board 本地伺服器 — 零依賴（Python 標準庫 http.server）。

用途：提供拖拉式 Scrum 看板 UI，並把使用者在瀏覽器的變更**雙向同步**回 repo 檔案，
讓 AI 讀檔即知最新 sprint 狀態。

路由：
    GET  /                靜態看板頁 (index.html)
    GET  /app.js          前端邏輯
    GET  /styles.css      樣式
    GET  /api/board       回傳 dev_docs/scrum_board.json（真相源）
    POST /api/board       寫回整份看板 JSON → 同步 16_wbs §7 表格

啟動：
    python tools/scrum_board/server.py            # 預設綁 0.0.0.0:8765（區網可達）
    python tools/scrum_board/server.py --port 9000
    python tools/scrum_board/server.py --host 127.0.0.1   # 僅本機

預設綁 0.0.0.0 方便遠端 / 容器外瀏覽器存取；此 server 無認證，**請只在可信任的內網使用**，
不要暴露到公網。要鎖回本機請加 --host 127.0.0.1。
"""
from __future__ import annotations

import argparse
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from sync_wbs import BOARD_PATH, save_board, sync

HERE = Path(__file__).resolve().parent

_STATIC = {
    "/": ("index.html", "text/html; charset=utf-8"),
    "/index.html": ("index.html", "text/html; charset=utf-8"),
    "/app.js": ("app.js", "application/javascript; charset=utf-8"),
    "/styles.css": ("styles.css", "text/css; charset=utf-8"),
}


class Handler(BaseHTTPRequestHandler):
    server_version = "ScrumBoard/1.0"

    # ── helpers ────────────────────────────────────────────────────────────
    def _send(self, status: int, body: bytes, content_type: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _send_json(self, status: int, obj: object) -> None:
        self._send(status, json.dumps(obj, ensure_ascii=False).encode("utf-8"),
                   "application/json; charset=utf-8")

    # ── GET ────────────────────────────────────────────────────────────────
    def do_GET(self) -> None:  # noqa: N802 (stdlib naming)
        if self.path == "/api/board":
            try:
                self._send_json(200, json.loads(BOARD_PATH.read_text(encoding="utf-8")))
            except FileNotFoundError:
                self._send_json(404, {"error": "scrum_board.json not found"})
            return

        static = _STATIC.get(self.path)
        if static:
            filename, ctype = static
            path = HERE / filename
            if path.exists():
                self._send(200, path.read_bytes(), ctype)
            else:
                self._send_json(404, {"error": f"{filename} missing"})
            return

        self._send_json(404, {"error": "not found"})

    # ── POST ───────────────────────────────────────────────────────────────
    def do_POST(self) -> None:  # noqa: N802
        if self.path != "/api/board":
            self._send_json(404, {"error": "not found"})
            return
        try:
            length = int(self.headers.get("Content-Length", 0))
            board = json.loads(self.rfile.read(length).decode("utf-8"))
        except (ValueError, json.JSONDecodeError) as exc:
            self._send_json(400, {"error": f"invalid JSON: {exc}"})
            return

        # 真相源寫回（含 updatedAt 時戳）→ 同步 WBS §7
        save_board(board)
        try:
            table = sync()
            synced = True
        except ValueError as exc:
            # WBS 缺 marker 不致命 — JSON 仍已存檔
            table = str(exc)
            synced = False
        self._send_json(200, {"ok": True, "syncedWbs": synced, "table": table})

    # 安靜一點的 log
    def log_message(self, fmt: str, *args: object) -> None:  # noqa: A003
        print(f"[scrum_board] {self.address_string()} {fmt % args}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Scrum board 本地伺服器")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--host", default="0.0.0.0")
    args = parser.parse_args()

    httpd = ThreadingHTTPServer((args.host, args.port), Handler)
    shown = "127.0.0.1" if args.host in ("0.0.0.0", "") else args.host
    print(f"[scrum_board] 看板已啟動：http://{shown}:{args.port}/")
    if args.host in ("0.0.0.0", ""):
        print(f"[scrum_board] ⚠️ 綁 0.0.0.0：區網其他機器可透過 http://<本機IP>:{args.port}/ 連入")
        print("[scrum_board]    此 server 無認證，請只在可信任內網使用；鎖回本機加 --host 127.0.0.1")
    print(f"[scrum_board] 真相源：{BOARD_PATH}")
    print("[scrum_board] Ctrl-C 結束")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n[scrum_board] 已停止")
        httpd.shutdown()


if __name__ == "__main__":
    main()
