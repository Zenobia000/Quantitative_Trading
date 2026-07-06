"""Portfolio gate（ADR-036）— pod/sleeve 制的組合級證據軸 + 規則式資本配置。

三塊純函式，全部長在既有機件上：

* ``combine_returns`` — 艙位日報酬按日期 inner-join 對齊後加權合成
* ``portfolio_gate_report`` — 候選 + 艦隊合成組合的 DSR（走 ADR-030 修正後的
  ``deflated_sharpe_from_returns`` 單一真相源）vs standalone DSR：分散紅利的
  **證據軸**，v1 不改寫 standalone verdict（ADR-036 §3.2）
* ``sleeve_weights`` / ``apply_stop_outs`` — 外圈資本配置政策：ADR-025
  ``compute_position_size`` 的首個生產呼叫者 + hysteresis（防止在策略層追高
  殺低）+ pod 式離散停損

判決語意警告：組合級 DSR 是「艦隊固定」的條件性統計，詮釋弱於 standalone —
它記錄進 metrics 供晉升決策參考，不是自動後門。
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

import pandas as pd

from quant_platform.services.research_validation.validation.dsr import deflated_sharpe_from_returns
from quant_platform.services.research_validation.validation.two_stage_gate import (
    SizingConfig,
    SizingInput,
    compute_position_size,
    fleet_correlation,
)


def combine_returns(
    sleeves: Mapping[str, pd.Series],
    weights: Mapping[str, float] | None = None,
) -> pd.Series:
    """Weighted blend of sleeve daily-return series, inner-joined on dates.

    ``weights`` omitted → equal weight；given → 必須與 ``sleeves`` 鍵完全一致
    （多給/漏給都是呼叫端 bug，fail fast），權重以總和歸一。只有共同交易日
    進入合成（inner join）——缺日補零會偽造零波動。
    """
    if not sleeves:
        raise ValueError("combine_returns needs at least one sleeve")
    if weights is not None:
        if set(weights) != set(sleeves):
            raise ValueError(
                f"weight keys {sorted(weights)} != sleeve keys {sorted(sleeves)}"
            )
        total = float(sum(weights.values()))
        if total <= 0.0:
            raise ValueError("weights must sum to a positive value")
        norm = {k: float(w) / total for k, w in weights.items()}
    else:
        norm = {k: 1.0 / len(sleeves) for k in sleeves}

    frame = pd.concat(dict(sleeves), axis=1, join="inner").dropna()
    combined = sum(frame[k] * norm[k] for k in sleeves)
    return pd.Series(combined, index=frame.index)


@dataclass(frozen=True)
class PortfolioGateReport:
    """組合級證據軸的完整快照（ADR-036 §3.2）— 記錄用，非 verdict。"""

    candidate_id: str
    standalone_dsr: float
    portfolio_dsr: float
    correlation_to_fleet: float
    n_obs: int
    sleeve_ids: tuple[str, ...]
    suggested_weight: float | None = None

    @property
    def diversification_premium(self) -> float:
        """組合 DSR 對 standalone 的增益 — 正值 = 正交紅利存在。"""
        return self.portfolio_dsr - self.standalone_dsr


def portfolio_gate_report(
    candidate_id: str,
    candidate_returns: pd.Series,
    fleet: Mapping[str, pd.Series],
    *,
    n_trials: int,
    weights: Mapping[str, float] | None = None,
    candidate_oos_sharpe: float | None = None,
    sizing_cfg: SizingConfig = SizingConfig(),
) -> PortfolioGateReport:
    """候選 + 既有艦隊的組合級評估。

    * standalone / portfolio DSR 走同一條 ``deflated_sharpe_from_returns``；
      ``n_trials`` 取候選的試驗數（艦隊成員已在各自判決中通縮過，合成組合的
      自由度來自候選——ADR-036 §3.2）。
    * 空艦隊 → 組合 == standalone、相關性 0.0（首艙位無分散懲罰，與
      ``fleet_correlation`` 語意一致）。
    * ``candidate_oos_sharpe`` 給定時附 ADR-025 sizing 建議權重。
    """
    if candidate_id in fleet:
        raise ValueError(f"candidate id {candidate_id!r} collides with a fleet sleeve")

    standalone = deflated_sharpe_from_returns(candidate_returns, n_trials=n_trials)
    corr = fleet_correlation(candidate_returns, list(fleet.values()))

    sleeves: dict[str, pd.Series] = {candidate_id: candidate_returns, **dict(fleet)}
    combined = combine_returns(sleeves, weights)
    portfolio = deflated_sharpe_from_returns(combined, n_trials=n_trials)

    suggested: float | None = None
    if candidate_oos_sharpe is not None:
        suggested = compute_position_size(
            SizingInput(oos_sharpe=candidate_oos_sharpe, correlation_to_fleet=corr),
            sizing_cfg,
        )

    return PortfolioGateReport(
        candidate_id=candidate_id,
        standalone_dsr=standalone,
        portfolio_dsr=portfolio,
        correlation_to_fleet=corr,
        n_obs=len(combined),
        sleeve_ids=tuple(sleeves),
        suggested_weight=suggested,
    )


def sleeve_weights(
    inputs: Mapping[str, SizingInput],
    cfg: SizingConfig = SizingConfig(),
    *,
    previous: Mapping[str, float] | None = None,
    hysteresis: float = 0.2,
) -> dict[str, float]:
    """外圈資本配置：每艙位權重 = ADR-025 ``compute_position_size``。

    Hysteresis（ADR-036 §3.3）：舊權重存在且相對變化 < ``hysteresis`` 時保留
    舊值——資本在策略層的搬動必須慢，追著近期 Sharpe 換倉 = 高買低賣。
    權重總和不歸一：餘額即現金（pod 語意）。
    """
    out: dict[str, float] = {}
    for sid, inp in inputs.items():
        raw = compute_position_size(inp, cfg)
        prev = (previous or {}).get(sid)
        if prev is not None and prev > 0.0 and abs(raw - prev) / prev < hysteresis:
            out[sid] = prev
        else:
            out[sid] = raw
    return out


def apply_stop_outs(
    weights: Mapping[str, float],
    *,
    drawdowns: Mapping[str, float],
    max_drawdown: float = 0.15,
) -> dict[str, float]:
    """Pod 式離散停損（ADR-036 §3.3）：live 回撤**超過**閾值的艙位配額歸零
    （退回審判庭重驗）。``drawdowns`` 為負值（-0.16 = 回撤 16%）；缺席艙位
    不動。輸入不可變——回傳新 dict。
    """
    return {
        sid: 0.0 if drawdowns.get(sid, 0.0) < -max_drawdown else w
        for sid, w in weights.items()
    }
