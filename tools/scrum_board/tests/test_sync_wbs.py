"""sync_wbs 純函式測試 — 渲染、marker 替換、status↔emoji 映射、idempotency。"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import sync_wbs  # noqa: E402


@pytest.fixture
def board() -> dict:
    return {
        "version": 1,
        "columns": sync_wbs.COLUMN_EMOJI,
        "cards": [
            {"id": "s1", "kind": "sprint", "title": "Sprint 1", "dates": "6/1",
             "goal": "do A", "wbs": "5.A", "column": "done", "order": 1},
            {"id": "s0", "kind": "sprint", "title": "Sprint 0", "dates": "5/30",
             "goal": "setup", "wbs": "0.1", "column": "done", "order": 0},
            {"id": "s2", "kind": "sprint", "title": "Sprint 2", "dates": "6/15",
             "goal": "wip", "wbs": "5.B", "column": "in_progress", "order": 2},
            {"id": "s3", "kind": "sprint", "title": "Sprint 3", "dates": "6/30",
             "goal": "later", "wbs": "6.*", "column": "backlog", "order": 3},
            {"id": "t1", "kind": "task", "title": "ad-hoc task", "column": "todo", "order": 9},
        ],
    }


def test_render_orders_by_order_field(board):
    table = sync_wbs.render_table(board)
    # 分隔列 |:--|... 不以 "| " 開頭，故此處只會抓到表頭 + 資料列
    rows = [ln for ln in table.splitlines() if ln.startswith("| ")]
    assert rows[0].startswith("| Sprint |")
    body = rows[1:]  # 去表頭，剩 4 sprint（task 不入表）
    assert len(body) == 4
    # order: s0, s1, s2, s3
    assert "Sprint 0" in body[0]
    assert "Sprint 1" in body[1]
    assert "Sprint 2" in body[2]
    assert "Sprint 3" in body[3]


def test_render_excludes_non_sprint_cards(board):
    table = sync_wbs.render_table(board)
    assert "ad-hoc task" not in table


def test_status_emoji_mapping(board):
    table = sync_wbs.render_table(board)
    assert "| ✅ Sprint 0 |" in table          # done
    assert "| 🚧 Sprint 2 |" in table          # in_progress
    assert "| Sprint 3 |" in table             # backlog → 無 emoji


def test_replace_between_markers_roundtrip():
    text = (
        "intro\n"
        f"{sync_wbs.MARKER_START}\nOLD CONTENT\n{sync_wbs.MARKER_END}\n"
        "outro\n"
    )
    out = sync_wbs.replace_between_markers(text, "NEW TABLE")
    assert "OLD CONTENT" not in out
    assert "NEW TABLE" in out
    assert out.startswith("intro\n")
    assert out.endswith("outro\n")
    assert sync_wbs.MARKER_START in out and sync_wbs.MARKER_END in out


def test_replace_is_idempotent():
    text = f"a\n{sync_wbs.MARKER_START}\nx\n{sync_wbs.MARKER_END}\nb\n"
    once = sync_wbs.replace_between_markers(text, "PAYLOAD")
    twice = sync_wbs.replace_between_markers(once, "PAYLOAD")
    assert once == twice


def test_replace_missing_marker_raises():
    with pytest.raises(ValueError):
        sync_wbs.replace_between_markers("no markers here", "x")


def test_sync_writes_wbs(tmp_path, board):
    board_path = tmp_path / "scrum_board.json"
    board_path.write_text(json.dumps(board, ensure_ascii=False), encoding="utf-8")
    wbs_path = tmp_path / "wbs.md"
    wbs_path.write_text(
        f"# WBS\n\n{sync_wbs.MARKER_START}\n(old)\n{sync_wbs.MARKER_END}\n\ntail\n",
        encoding="utf-8",
    )
    table = sync_wbs.sync(board_path, wbs_path)
    written = wbs_path.read_text(encoding="utf-8")
    assert "Sprint 0" in written
    assert "(old)" not in written
    assert table in written
    assert written.endswith("tail\n")


def test_save_board_adds_timestamp(tmp_path):
    board_path = tmp_path / "b.json"
    sync_wbs.save_board({"cards": []}, board_path)
    saved = json.loads(board_path.read_text(encoding="utf-8"))
    assert "updatedAt" in saved
