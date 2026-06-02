"""Scrum board <-> WBS 文件同步引擎。

真相源：``dev_docs/scrum_board.json``（看板讀寫此檔）。
本模組把該 JSON 重新渲染成 ``16_wbs_development_plan.md`` §7 的 Sprint 表格，
並寫入 ``<!-- SCRUM_BOARD:START -->`` / ``<!-- SCRUM_BOARD:END -->`` 兩個 marker 之間，
讓 AI 讀 WBS（人類可讀真相源）時看到的永遠是看板最新狀態。

純函式 (``render_table`` / ``replace_between_markers``) 與 IO (``sync``) 分離，方便測試。
無第三方依賴 — 只用標準庫。
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

# ── 路徑常數 ──────────────────────────────────────────────────────────────
REPO_ROOT = Path(__file__).resolve().parents[2]
BOARD_PATH = REPO_ROOT / "dev_docs" / "scrum_board.json"
WBS_PATH = REPO_ROOT / "dev_docs" / "16_wbs_development_plan.md"

MARKER_START = "<!-- SCRUM_BOARD:START (此區塊由 tools/scrum_board 自動生成，請勿手改) -->"
MARKER_END = "<!-- SCRUM_BOARD:END -->"

# column id -> 表格狀態 emoji（看板欄位 → WBS Sprint 前綴）
COLUMN_EMOJI = {
    "backlog": "",
    "todo": "⏳ ",
    "in_progress": "🚧 ",
    "review": "🔎 ",
    "done": "✅ ",
}


def load_board(path: Path = BOARD_PATH) -> dict:
    """讀取看板真相源 JSON。"""
    return json.loads(path.read_text(encoding="utf-8"))


def save_board(board: dict, path: Path = BOARD_PATH) -> None:
    """寫回看板真相源 JSON（含 ``updatedAt`` 時戳，2-space 縮排）。"""
    board = dict(board)
    board["updatedAt"] = datetime.now(timezone.utc).astimezone().replace(microsecond=0).isoformat()
    path.write_text(json.dumps(board, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _emoji_for(column_id: str) -> str:
    return COLUMN_EMOJI.get(column_id, "")


def render_table(board: dict) -> str:
    """把看板 cards 渲染成 WBS §7 的 markdown 表格字串（不含 marker）。

    僅渲染 ``kind == "sprint"`` 的卡片，依 ``order`` 排序。狀態 emoji 由所在欄位決定，
    因此使用者在看板拖拉卡片到不同欄位後，這裡的 ✅/🚧/⏳ 前綴會自動跟著變。
    """
    sprints = sorted(
        (c for c in board.get("cards", []) if c.get("kind") == "sprint"),
        key=lambda c: c.get("order", 0),
    )
    lines = [
        "| Sprint | 日期 | 重點 | 對應 WBS |",
        "|:--|:--|:--|:--|",
    ]
    for c in sprints:
        prefix = _emoji_for(c.get("column", "backlog"))
        title = f"{prefix}{c.get('title', '')}".strip()
        dates = c.get("dates", "")
        goal = c.get("goal", "")
        wbs = c.get("wbs", "")
        lines.append(f"| {title} | {dates} | {goal} | {wbs} |")
    return "\n".join(lines)


def replace_between_markers(text: str, payload: str) -> str:
    """把 ``text`` 中兩個 marker 之間的內容替換成 ``payload``（含 marker 自身保留）。

    若找不到 marker，丟出 ``ValueError`` — 呼叫端負責先在 WBS §7 放好 marker。
    """
    start = text.find(MARKER_START)
    end = text.find(MARKER_END)
    if start == -1 or end == -1 or end < start:
        raise ValueError(
            f"找不到 scrum board markers，請確認 {WBS_PATH.name} §7 內含 "
            f"{MARKER_START!r} 與 {MARKER_END!r}"
        )
    block = f"{MARKER_START}\n\n{payload}\n\n{MARKER_END}"
    return text[:start] + block + text[end + len(MARKER_END):]


def sync(board_path: Path = BOARD_PATH, wbs_path: Path = WBS_PATH) -> str:
    """讀看板 JSON → 渲染表格 → 寫回 WBS marker 區塊。回傳渲染後的表格字串。"""
    board = load_board(board_path)
    table = render_table(board)
    wbs_text = wbs_path.read_text(encoding="utf-8")
    updated = replace_between_markers(wbs_text, table)
    if updated != wbs_text:
        wbs_path.write_text(updated, encoding="utf-8")
    return table


if __name__ == "__main__":
    rendered = sync()
    print("[scrum_board] 已同步 16_wbs §7：")
    print(rendered)
