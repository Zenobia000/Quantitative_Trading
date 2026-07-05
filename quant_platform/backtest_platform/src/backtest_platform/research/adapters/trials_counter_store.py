"""Persisted trials counter (8.H.5) — cumulative trial tally per param-space.

``validation.trials.TrialsCounter`` is an in-memory accumulator; the DSR
deflation guardrail (ADR-016) needs the count to *survive across requests/runs*
so "how many configs did I actually search" is auditable, not guessed. This
store persists a ``{param_space_hash: cumulative_count}`` map as JSON and exposes
an idempotent-per-call increment that returns the new cumulative total — feeding
``trials_deflated_criterion``.
"""
from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from backtest_platform.validation.trials import TrialsCounter

DEFAULT_TRIALS_PATH = Path("reports") / "trials.json"


def param_space_key(param_space: Mapping[str, Any] | str) -> str:
    """Deterministic key for a param-space (dict → sorted-json hash, str → as-is)."""
    if isinstance(param_space, str):
        raw = param_space
    else:
        raw = json.dumps(param_space, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha1(raw.encode()).hexdigest()[:12]


def _resolve(path: Path | str | None) -> Path:
    return Path(path) if path is not None else DEFAULT_TRIALS_PATH


def _read(path: Path) -> dict[str, int]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def increment(
    param_space: Mapping[str, Any] | str,
    count: int = 1,
    path: Path | str | None = None,
) -> int:
    """Add ``count`` trials for a param-space; return the new cumulative total.

    Uses :class:`TrialsCounter` for the (validated) accumulation so the +1 rule
    and ``count >= 1`` guard live in one place.
    """
    p = _resolve(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    key = param_space_key(param_space)
    store = _read(p)
    counter = TrialsCounter(store.get(key, 0))
    store[key] = counter.record(count)
    p.write_text(json.dumps(store, ensure_ascii=False), encoding="utf-8")
    return store[key]


def cumulative(
    param_space: Mapping[str, Any] | str, path: Path | str | None = None
) -> int:
    """Current cumulative trials for a param-space (0 if never incremented)."""
    return _read(_resolve(path)).get(param_space_key(param_space), 0)
