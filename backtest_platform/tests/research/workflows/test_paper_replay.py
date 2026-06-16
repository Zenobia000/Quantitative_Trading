from datetime import date
import pytest
from backtest_platform.research import runners as _runners  # noqa: F401
from backtest_platform.research.workflows.config import PaperReplayConfig
from backtest_platform.research.workflows.paper_replay import run_paper_replay_workflow, PaperReplayResult
from backtest_platform.strategies.conformance import synthetic_loader
from backtest_platform.strategies.momentum.strategy import MomentumConfig

def _cfg():
    return PaperReplayConfig(
        strategy="momentum",
        fixed_config=MomentumConfig(lookback_days=120),
        symbols=[f"SYN{i:04d}" for i in range(5)],
        as_of=date(2022, 1, 3),
        lookback_buffer_days=400,
    )

def test_paper_replay_returns_result():
    result = run_paper_replay_workflow(_cfg(), loader=synthetic_loader(n_bars=600))
    assert isinstance(result, PaperReplayResult)
    assert result.strategy == "momentum"

def test_paper_replay_has_run_id():
    result = run_paper_replay_workflow(_cfg(), loader=synthetic_loader(n_bars=600))
    assert result.run_id.startswith("paper_replay")

def test_paper_replay_has_metrics():
    result = run_paper_replay_workflow(_cfg(), loader=synthetic_loader(n_bars=600))
    assert "cagr" in result.metrics
    assert "sharpe" in result.metrics

def test_paper_replay_gate_status_is_string():
    result = run_paper_replay_workflow(_cfg(), loader=synthetic_loader(n_bars=600))
    assert result.gate_status in ("PASS", "FAIL", "INCOMPLETE")
