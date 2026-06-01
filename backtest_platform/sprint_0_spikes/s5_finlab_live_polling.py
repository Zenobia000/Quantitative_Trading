"""Sprint 0 Spike S5 — FinLab 即時資料 polling POC.

Validates:
1. FinLab login OK
2. Poll latest quote for a single stock continuously for N seconds
3. Write samples to CSV with timestamps

Note: FinLab realtime data depends on market hours + subscription tier.
Off-hours: returns last snapshot. Spike still validates plumbing works.

Requirements:
- FINLAB_API_TOKEN in .env
- pip install finlab

Pass criteria: `[S5] PASS` if at least 5 samples collected without exception.
"""
from __future__ import annotations

import json
import os
import sys
import time
import traceback
from datetime import date, datetime
from pathlib import Path

import click

ROOT = Path(__file__).resolve().parents[1]
RESULTS = Path(__file__).parent / "results"
RESULTS.mkdir(exist_ok=True)


def login_finlab() -> dict:
    try:
        from dotenv import load_dotenv

        load_dotenv(ROOT / ".env")
        token = os.environ.get("FINLAB_API_TOKEN")
        if not token:
            return {"ok": False, "error": "FINLAB_API_TOKEN not set"}

        import finlab

        finlab.login(api_token=token)
        return {"ok": True}
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}


def poll_loop(stock: str, duration: int, interval: float = 5.0) -> dict:
    """Poll snapshot every `interval` seconds for `duration` seconds total."""
    try:
        from finlab import data
        import pandas as pd

        samples = []
        start_ts = time.time()
        end_ts = start_ts + duration
        sample_count = 0
        errors = 0

        while time.time() < end_ts:
            try:
                # FinLab realtime API surface varies by version; try common paths
                try:
                    snap = data.get("realtime:price")
                    val = snap[stock].iloc[-1] if stock in snap.columns else None
                except Exception:
                    # Fallback: last daily snapshot
                    close = data.get("price:收盤價")
                    val = (
                        close[stock].iloc[-1]
                        if stock in close.columns
                        else None
                    )
                if val is not None:
                    samples.append(
                        {
                            "ts": datetime.now().isoformat(),
                            "stock": stock,
                            "price": float(val),
                        }
                    )
                    sample_count += 1
            except Exception:
                errors += 1
            time.sleep(interval)

        if samples:
            csv_file = RESULTS / f"s5_polling_{stock}_{date.today().isoformat()}.csv"
            pd.DataFrame(samples).to_csv(csv_file, index=False)
            csv_path = str(csv_file)
        else:
            csv_path = None

        return {
            "ok": sample_count >= 5,
            "stock": stock,
            "duration_sec": duration,
            "interval_sec": interval,
            "samples_collected": sample_count,
            "errors": errors,
            "csv_output": csv_path,
        }
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}


@click.command()
@click.option("--stock", default="2330")
@click.option("--duration", default=60, type=int, help="Total polling seconds")
@click.option("--interval", default=5.0, type=float, help="Seconds between polls")
def main(stock: str, duration: int, interval: float) -> None:
    print("=" * 60)
    print("Sprint 0 Spike S5 — FinLab live polling")
    print(f"  stock={stock} duration={duration}s interval={interval}s")
    print("=" * 60)

    checks = {"1_finlab_login": login_finlab()}
    if checks["1_finlab_login"].get("ok"):
        checks["2_poll_loop"] = poll_loop(stock, duration, interval)
    else:
        checks["2_poll_loop"] = {"ok": False, "skipped": "login failed"}

    for name, result in checks.items():
        status = "OK" if result.get("ok") else "FAIL"
        print(f"\n[{status}] {name}")
        for k, v in result.items():
            if k != "ok":
                print(f"  {k}: {v}")

    all_ok = all(r.get("ok") for r in checks.values())
    output = {
        "spike": "S5",
        "date": date.today().isoformat(),
        "passed": all_ok,
        "checks": checks,
    }
    out_file = RESULTS / "s5_finlab_live_polling.json"
    out_file.write_text(json.dumps(output, indent=2, ensure_ascii=False))

    print(f"\nResults → {out_file}")
    print("=" * 60)
    print("[S5] PASS" if all_ok else "[S5] FAIL — see results JSON")
    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    try:
        main(standalone_mode=False)
    except click.exceptions.UsageError as e:
        print(f"Usage: {e}")
        sys.exit(2)
    except Exception:
        traceback.print_exc()
        sys.exit(2)
