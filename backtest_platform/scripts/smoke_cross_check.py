"""Smoke test for cross_check_vectorbt — exercises both acceptance modes."""
from __future__ import annotations

from datetime import date

from backtest_platform.engines.zipline_adapter.validation.cross_check_vectorbt import (
    cross_check_vectorbt,
)


def _report(label: str, r) -> None:
    verdict = "PASS" if r.ok else "FAIL"
    print(f"--- {label} ---")
    print(
        f"  bars={r.n_bars}  trades self/vbt={r.n_trades_self}/{r.n_trades_vbt}  "
        f"ret self/vbt={r.self_total_return:.4%}/{r.vbt_total_return:.4%}  "
        f"diff abs={r.return_diff_abs:.6f} rel={r.return_diff_rel:.4%}  "
        f"sharpe self/vbt={r.self_sharpe!r}/{r.vbt_sharpe!r}  {verdict}"
    )


def main() -> None:
    print("=== Cross-Check vectorbt vs self-written PnL ===")
    _report("2330 2024 (near-zero ret)", cross_check_vectorbt("2330", date(2024, 1, 1), date(2024, 12, 31)))
    _report("2330 2022-2024 (multi-year)", cross_check_vectorbt("2330", date(2022, 1, 1), date(2024, 12, 31)))
    _report("2330 2020-2024 (5y trend)", cross_check_vectorbt("2330", date(2020, 1, 1), date(2024, 12, 31)))


if __name__ == "__main__":
    main()
