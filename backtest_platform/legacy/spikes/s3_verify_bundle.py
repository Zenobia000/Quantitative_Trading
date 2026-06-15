"""Sprint 0 Spike S3 — Verify FinLab bundle is ingested and readable.

Run AFTER `zipline ingest -b finlab_poc`.
Verifies Zipline can read the bundle and access historical bars.

Pass criteria: `[S3-verify] PASS` printed.
"""
from __future__ import annotations

import json
import sys
import traceback
from datetime import date
from pathlib import Path

RESULTS = Path(__file__).parent / "results"
RESULTS.mkdir(exist_ok=True)


def check_bundle_readable() -> dict:
    try:
        from zipline.data import bundles

        bundle_data = bundles.load("finlab_poc")
        equity_minute_reader = bundle_data.equity_minute_bar_reader
        equity_daily_reader = bundle_data.equity_daily_bar_reader
        asset_finder = bundle_data.asset_finder

        all_equities = asset_finder.equities_sids
        sample_assets = [asset_finder.retrieve_asset(s) for s in list(all_equities)[:5]]

        return {
            "ok": True,
            "bundle": "finlab_poc",
            "asset_count": len(all_equities),
            "sample_symbols": [str(a.symbol) for a in sample_assets],
            "daily_reader_first_session": str(equity_daily_reader.first_trading_day.date()),
            "daily_reader_last_session": str(equity_daily_reader.last_available_dt.date()),
        }
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}


def main() -> int:
    print("=" * 60)
    print("Sprint 0 Spike S3 verify — read FinLab bundle from Zipline")
    print("=" * 60)

    result = check_bundle_readable()
    status = "OK" if result.get("ok") else "FAIL"
    print(f"\n[{status}] bundle_readable")
    for k, v in result.items():
        if k != "ok":
            print(f"  {k}: {v}")

    output = {
        "spike": "S3-verify",
        "date": date.today().isoformat(),
        "passed": result.get("ok", False),
        "result": result,
    }
    out_file = RESULTS / "s3_verify_bundle.json"
    out_file.write_text(json.dumps(output, indent=2, ensure_ascii=False, default=str))

    print(f"\nResults → {out_file}")
    print("=" * 60)
    print("[S3-verify] PASS" if result.get("ok") else "[S3-verify] FAIL")
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        traceback.print_exc()
        sys.exit(2)
