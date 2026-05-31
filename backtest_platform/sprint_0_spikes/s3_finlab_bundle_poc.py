"""Sprint 0 Spike S3 — FinLab bundle ingester POC.

Validates:
1. `finlab` package can login with FINLAB_API_TOKEN
2. Pull OHLCV for 10 stocks × 1 year
3. Write CSV files in Zipline csvdir bundle format
4. Print zipline ingest command for user to run separately

Requirements:
- FINLAB_API_TOKEN in .env
- pip install finlab zipline-tej

Pass criteria: `[S3] PASS` if all steps complete; user then runs:
    poetry run zipline ingest -b finlab_poc

Then verifies with s3_verify_bundle.py.
"""
from __future__ import annotations

import json
import os
import sys
import traceback
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

RESULTS = Path(__file__).parent / "results"
RESULTS.mkdir(exist_ok=True)
BUNDLE_CSV_DIR = ROOT / "data" / "zipline_bundles" / "finlab_poc"


TEST_STOCKS = ["2330", "2454", "2317", "1101", "3008", "2882", "1303", "2412", "2308", "2891"]


def check_finlab_login() -> dict:
    """Step 1: FinLab login + quota check."""
    try:
        from dotenv import load_dotenv

        load_dotenv(ROOT / ".env")
        token = os.environ.get("FINLAB_API_TOKEN")
        if not token:
            return {"ok": False, "error": "FINLAB_API_TOKEN not set in .env"}

        import finlab

        finlab.login(api_token=token)
        # finlab.get_token() or quota check — exact API varies by version
        return {"ok": True, "logged_in": True, "note": "Check usage at ai.finlab.tw"}
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}


def pull_finlab_ohlcv(stocks: list[str], start: str, end: str) -> dict:
    """Step 2: Pull OHLCV via finlab.data.get."""
    try:
        from finlab import data

        # FinLab returns wide DataFrames: index=date, columns=stock_id
        close = data.get("price:收盤價")
        open_ = data.get("price:開盤價")
        high = data.get("price:最高價")
        low = data.get("price:最低價")
        vol = data.get("price:成交股數")

        # Filter to test stocks + date range
        close = close.loc[start:end, [s for s in stocks if s in close.columns]]
        open_ = open_.loc[start:end, close.columns]
        high = high.loc[start:end, close.columns]
        low = low.loc[start:end, close.columns]
        vol = vol.loc[start:end, close.columns]

        return {
            "ok": True,
            "stocks_available": list(close.columns),
            "stocks_missing": [s for s in stocks if s not in close.columns],
            "date_range": f"{close.index[0]} to {close.index[-1]}",
            "bars_per_stock": len(close),
            "_dataframes": {  # held for next step, not serialized
                "open": open_,
                "high": high,
                "low": low,
                "close": close,
                "volume": vol,
            },
        }
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}


def write_csvdir_bundle(dfs: dict, output_dir: Path) -> dict:
    """Step 3: Write Zipline csvdir bundle format.

    csvdir layout:
        output_dir/
          daily/
            2330.csv     # columns: date, open, high, low, close, volume, dividend, split
            2454.csv
            ...
    """
    try:
        import pandas as pd

        daily_dir = output_dir / "daily"
        daily_dir.mkdir(parents=True, exist_ok=True)

        stocks = list(dfs["close"].columns)
        written = []
        for s in stocks:
            df = pd.DataFrame(
                {
                    "date": dfs["close"].index,
                    "open": dfs["open"][s].values,
                    "high": dfs["high"][s].values,
                    "low": dfs["low"][s].values,
                    "close": dfs["close"][s].values,
                    "volume": dfs["volume"][s].values,
                    "dividend": 0.0,
                    "split": 1.0,
                }
            ).dropna()
            if len(df) > 0:
                df.to_csv(daily_dir / f"{s}.csv", index=False)
                written.append(s)

        return {
            "ok": len(written) > 0,
            "output_dir": str(output_dir),
            "stocks_written": written,
            "file_count": len(written),
        }
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}


def print_extension_py_template(bundle_dir: Path) -> dict:
    """Step 4: Print Zipline extension.py template for user to drop into ~/.zipline/."""
    template = f'''
# ~/.zipline/extension.py (or set ZIPLINE_ROOT env var to project dir)
from zipline.data.bundles import register
from zipline.data.bundles.csvdir import csvdir_equities

register(
    "finlab_poc",
    csvdir_equities(
        ["daily"],
        r"{bundle_dir}",
    ),
    calendar_name="XTAI",
)
'''
    ext_file = RESULTS / "extension_py_template.py"
    ext_file.write_text(template)
    return {
        "ok": True,
        "extension_template": str(ext_file),
        "next_steps": [
            f"1. Copy contents of {ext_file} into ~/.zipline/extension.py",
            "2. Run: poetry run zipline ingest -b finlab_poc",
            "3. Run: poetry run python sprint_0_spikes/s3_verify_bundle.py",
        ],
    }


def main() -> int:
    print("=" * 60)
    print("Sprint 0 Spike S3 — FinLab bundle ingester POC")
    print("=" * 60)

    start = "2024-01-01"
    end = (date.today() - timedelta(days=1)).isoformat()

    checks: dict = {}

    checks["1_finlab_login"] = check_finlab_login()
    if not checks["1_finlab_login"].get("ok"):
        return _finalize(checks)

    pulled = pull_finlab_ohlcv(TEST_STOCKS, start, end)
    if not pulled.get("ok"):
        checks["2_pull_ohlcv"] = pulled
        return _finalize(checks)

    dfs = pulled.pop("_dataframes")
    checks["2_pull_ohlcv"] = pulled

    checks["3_write_csvdir"] = write_csvdir_bundle(dfs, BUNDLE_CSV_DIR)
    if not checks["3_write_csvdir"].get("ok"):
        return _finalize(checks)

    checks["4_extension_template"] = print_extension_py_template(BUNDLE_CSV_DIR)

    return _finalize(checks)


def _finalize(checks: dict) -> int:
    for name, result in checks.items():
        status = "OK" if result.get("ok") else "FAIL"
        print(f"\n[{status}] {name}")
        for k, v in result.items():
            if k != "ok":
                print(f"  {k}: {v}")

    all_ok = all(r.get("ok") for r in checks.values())
    output = {
        "spike": "S3",
        "date": date.today().isoformat(),
        "passed": all_ok,
        "checks": checks,
    }
    out_file = RESULTS / "s3_finlab_bundle_poc.json"
    out_file.write_text(json.dumps(output, indent=2, ensure_ascii=False, default=str))

    print(f"\nResults → {out_file}")
    print("=" * 60)
    print("[S3] PASS" if all_ok else "[S3] FAIL — see results JSON")
    return 0 if all_ok else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        traceback.print_exc()
        sys.exit(2)
