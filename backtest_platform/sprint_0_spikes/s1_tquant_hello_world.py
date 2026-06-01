"""Sprint 0 Spike S1 — TQuant-Lab + XTAI calendar hello world.

Validates:
1. `zipline-tej` package importable
2. XTAI (Taiwan Stock Exchange) calendar available via `exchange-calendars`
3. Calendar sessions count for 2024 ≈ 245 (Taiwan trading days)
4. Minimal Zipline algorithm initialization succeeds

Requirements:
- uv sync --extra mainframe (or `pip install zipline-tej exchange-calendars`)

No external API token required.

Pass criteria printed at end as `[S1] PASS` or `[S1] FAIL: <reason>`.
"""
from __future__ import annotations

import json
import sys
import traceback
from datetime import date
from pathlib import Path

RESULTS = Path(__file__).parent / "results"
RESULTS.mkdir(exist_ok=True)


def check_zipline_import() -> dict:
    """Step 1: zipline package importable."""
    try:
        import zipline  # noqa: F401

        return {"ok": True, "version": getattr(zipline, "__version__", "unknown")}
    except ImportError as e:
        return {"ok": False, "error": f"zipline import failed: {e}"}


def check_xtai_calendar() -> dict:
    """Step 2: XTAI calendar available with correct session count."""
    try:
        import exchange_calendars as xcals

        cal = xcals.get_calendar("XTAI")
        sessions_2024 = cal.sessions_in_range("2024-01-01", "2024-12-31")
        count = len(sessions_2024)
        # Taiwan has ~245 trading days/year (252 minus typical holidays)
        in_range = 235 <= count <= 255
        return {
            "ok": in_range,
            "calendar_name": cal.name,
            "sessions_2024_count": count,
            "first_session": str(sessions_2024[0].date()),
            "last_session": str(sessions_2024[-1].date()),
            "expected_range": "235-255",
        }
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}


def check_minimal_algorithm() -> dict:
    """Step 3: Zipline minimal algorithm can be instantiated.

    We do NOT run a full backtest here (would need a bundle).
    We just verify the API surface is reachable.
    """
    try:
        from zipline.api import order, record, symbol  # noqa: F401
        from zipline.algorithm import TradingAlgorithm  # noqa: F401

        return {
            "ok": True,
            "note": "TradingAlgorithm + order/record/symbol API importable",
        }
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}


def main() -> int:
    print("=" * 60)
    print("Sprint 0 Spike S1 — TQuant-Lab + XTAI hello world")
    print("=" * 60)

    checks = {
        "1_zipline_import": check_zipline_import(),
        "2_xtai_calendar": check_xtai_calendar(),
        "3_minimal_algorithm": check_minimal_algorithm(),
    }

    for name, result in checks.items():
        status = "OK" if result.get("ok") else "FAIL"
        print(f"\n[{status}] {name}")
        for k, v in result.items():
            if k != "ok":
                print(f"  {k}: {v}")

    all_ok = all(r.get("ok") for r in checks.values())
    output = {
        "spike": "S1",
        "date": date.today().isoformat(),
        "passed": all_ok,
        "checks": checks,
    }
    out_file = RESULTS / "s1_tquant_hello_world.json"
    out_file.write_text(json.dumps(output, indent=2, ensure_ascii=False))

    print(f"\nResults → {out_file}")
    print("=" * 60)
    if all_ok:
        print("[S1] PASS")
        return 0
    else:
        print("[S1] FAIL — see results JSON for details")
        return 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        traceback.print_exc()
        sys.exit(2)
