"""Sprint 0 Spike S4 — Shioaji 沙箱範例跑通.

Validates:
1. shioaji.Shioaji(simulation=True) initializes
2. Login succeeds
3. Get quote for 2330
4. Place a simulated buy order (low price, won't fill)
5. Cancel the order
6. Logout

Requirements:
- SHIOAJI_* env vars set in .env (SHIOAJI_SIMULATION=true!)
- pip install shioaji

WARNING: Even in simulation mode, never run with SHIOAJI_SIMULATION=false
without explicit user confirmation. This script enforces simulation=True.

Pass criteria: all 6 steps OK → `[S4] PASS`
"""
from __future__ import annotations

import json
import os
import sys
import time
import traceback
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESULTS = Path(__file__).parent / "results"
RESULTS.mkdir(exist_ok=True)


def check_env() -> dict:
    """Step 0: env vars present + simulation enforced."""
    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env")

    required = ["SHIOAJI_API_KEY", "SHIOAJI_SECRET_KEY"]
    missing = [k for k in required if not os.environ.get(k)]
    if missing:
        return {"ok": False, "error": f"missing env: {missing}"}

    sim = os.environ.get("SHIOAJI_SIMULATION", "true").lower() == "true"
    if not sim:
        return {
            "ok": False,
            "error": "SHIOAJI_SIMULATION=false detected; spike refuses to run live",
        }
    return {"ok": True, "simulation": True}


def init_and_login() -> dict:
    """Step 1+2: initialize + login."""
    try:
        import shioaji as sj

        api = sj.Shioaji(simulation=True)
        accounts = api.login(
            api_key=os.environ["SHIOAJI_API_KEY"],
            secret_key=os.environ["SHIOAJI_SECRET_KEY"],
        )
        return {
            "ok": True,
            "_api": api,  # passed forward, not serialized
            "accounts": [
                {
                    "account_type": str(a.account_type),
                    "broker_id": a.broker_id,
                    "account_id": a.account_id,
                }
                for a in (accounts if isinstance(accounts, list) else [accounts])
            ],
        }
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}


def get_quote(api) -> dict:
    """Step 3: subscribe + get 2330 snapshot."""
    try:
        contract = api.Contracts.Stocks.TSE["2330"]
        snapshots = api.snapshots([contract])
        snap = snapshots[0] if snapshots else None
        if snap is None:
            return {"ok": False, "error": "no snapshot returned"}
        return {
            "ok": True,
            "stock": "2330",
            "close": float(snap.close),
            "volume": int(snap.volume),
            "ts": str(snap.ts),
        }
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}


def place_and_cancel_order(api) -> dict:
    """Step 4+5: place sim buy at unrealistic low + cancel."""
    try:
        import shioaji as sj

        contract = api.Contracts.Stocks.TSE["2330"]
        # Use very low price so it definitely won't fill
        snapshot = api.snapshots([contract])[0]
        unrealistic_price = float(snapshot.close) * 0.5  # half market

        order = sj.order.StockOrder(
            action=sj.constant.Action.Buy,
            price=unrealistic_price,
            quantity=1,
            price_type=sj.constant.StockPriceType.LMT,
            order_type=sj.constant.OrderType.ROD,
        )
        trade = api.place_order(contract, order)
        time.sleep(1)

        # Cancel
        api.cancel_order(trade)
        time.sleep(1)
        api.update_status(api.stock_account)

        return {
            "ok": True,
            "order_placed_at": unrealistic_price,
            "status_after_cancel": str(trade.status.status),
            "note": "Order placed and cancelled in simulation",
        }
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}


def logout(api) -> dict:
    try:
        api.logout()
        return {"ok": True}
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}


def main() -> int:
    print("=" * 60)
    print("Sprint 0 Spike S4 — Shioaji sandbox (simulation=true)")
    print("=" * 60)

    checks: dict = {}
    api = None

    checks["0_env"] = check_env()
    if not checks["0_env"].get("ok"):
        return _finalize(checks)

    login_result = init_and_login()
    if not login_result.get("ok"):
        checks["1_init_login"] = login_result
        return _finalize(checks)
    api = login_result.pop("_api")
    checks["1_init_login"] = login_result

    checks["2_get_quote"] = get_quote(api)
    if checks["2_get_quote"].get("ok"):
        checks["3_order_lifecycle"] = place_and_cancel_order(api)
    else:
        checks["3_order_lifecycle"] = {"ok": False, "skipped": "no quote"}

    checks["4_logout"] = logout(api)

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
        "spike": "S4",
        "date": date.today().isoformat(),
        "passed": all_ok,
        "checks": checks,
    }
    out_file = RESULTS / "s4_shioaji_sandbox.json"
    out_file.write_text(json.dumps(output, indent=2, ensure_ascii=False, default=str))

    print(f"\nResults → {out_file}")
    print("=" * 60)
    print("[S4] PASS" if all_ok else "[S4] FAIL — see results JSON")
    return 0 if all_ok else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        traceback.print_exc()
        sys.exit(2)
