"""Taiwan trading-day helper — the after-close scheduler's calendar gate.

The scheduler must not run the daily flow on a day the TWSE was closed (a weekend
or a public / lunar holiday). Accuracy comes on a ladder so the platform degrades
gracefully instead of hard-failing when an optional dependency is absent:

1. **Injected ``calendar``** (tests / callers) — authoritative; used verbatim.
2. **``exchange_calendars`` XTAI** (the ``mainframe`` extra, already the TWSE
   session source for the zipline bundle) — full holiday accuracy including the
   shifting lunar-new-year / tomb-sweeping dates.
3. **Weekday fallback** (Mon–Fri) — an APPROXIMATION used only when the extra is
   not installed. LIMITATION: it treats Taiwan public / lunar holidays that fall
   on a weekday as trading days, so it can over-fire on ~10–15 days/year. Install
   the extra (``uv sync --extra mainframe``) for exact sessions; the scheduler's
   idempotency + risk gate still bound the blast radius of a false positive.

The XTAI import is lazy and defensively wrapped so importing this module never
requires ``exchange_calendars`` and a calendar-lookup error can never crash the
scheduler — it simply falls back to the weekday approximation (logged once).
"""
from __future__ import annotations

from datetime import date
from typing import Any

from loguru import logger


def _xtai_calendar() -> Any | None:
    """Return the ``exchange_calendars`` XTAI calendar, or None if unavailable.

    Absence of the optional extra (ImportError) or any construction error is
    swallowed to None so the caller transparently uses the weekday fallback.
    """
    try:
        import exchange_calendars as xc  # type: ignore[import-not-found]

        return xc.get_calendar("XTAI")
    except Exception:  # noqa: BLE001 — optional extra / lookup issue → fallback path
        return None


def is_taiwan_trading_day(d: date, *, calendar: Any | None = None) -> bool:
    """True if ``d`` is a TWSE trading session.

    ``calendar`` (any object exposing ``is_session(pd.Timestamp) -> bool``, e.g. an
    ``exchange_calendars`` calendar) overrides both auto-detection paths — this is
    the injection seam the tests drive. When omitted, XTAI is tried, then the
    weekday approximation (see module docstring for its documented limitation).
    """
    cal = calendar if calendar is not None else _xtai_calendar()
    if cal is not None:
        try:
            import pandas as pd

            return bool(cal.is_session(pd.Timestamp(d)))
        except Exception:  # noqa: BLE001 — a calendar hiccup must not crash the gate
            logger.warning(
                "XTAI calendar lookup failed for {d}; using weekday fallback", d=d
            )
    return d.weekday() < 5  # Mon=0 .. Fri=4 are business days
