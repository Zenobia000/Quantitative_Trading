"""orchestration.daily_flow — flow engine (fail-fast / capture / threading)
and canonical stages with injected stubs."""
from __future__ import annotations

from quant_platform.services.strategy_runtime.daily_flow import (
    FlowContext,
    StageResult,
    build_daily_stages,
    demo_stages,
    run_flow,
    stage_etl,
    stage_orders,
    stage_risk_gate,
    stage_signals,
)


def _ok(name):
    return lambda ctx: StageResult(name, ok=True, detail="ok", output=f"{name}-out")


def _fail(name):
    return lambda ctx: StageResult(name, ok=False, detail="nope")


def _boom(name):
    def _s(ctx):
        raise RuntimeError("kaboom")
    return _s


# --- engine ---------------------------------------------------------------

def test_run_flow_all_pass():
    run = run_flow([("a", _ok("a")), ("b", _ok("b"))])
    assert run.ok is True
    assert run.failed_stage is None
    assert [s.name for s in run.stages] == ["a", "b"]


def test_run_flow_fail_fast_halts():
    run = run_flow([("a", _ok("a")), ("b", _fail("b")), ("c", _ok("c"))])
    assert run.ok is False
    assert run.failed_stage == "b"
    # c never ran (fail-fast)
    assert [s.name for s in run.stages] == ["a", "b"]


def test_run_flow_captures_raise_without_crashing():
    run = run_flow([("a", _ok("a")), ("b", _boom("b")), ("c", _ok("c"))])
    assert run.ok is False
    assert run.failed_stage == "b"
    boom = next(s for s in run.stages if s.name == "b")
    assert "raised RuntimeError: kaboom" in boom.detail
    assert [s.name for s in run.stages] == ["a", "b"]


def test_run_flow_threads_outputs_into_context():
    seen = {}

    def reader(ctx):
        seen["a"] = ctx.outputs.get("a")
        return StageResult("b", ok=True, detail="read")

    run = run_flow([("a", _ok("a")), ("b", reader)])
    assert run.ok
    assert seen["a"] == "a-out"  # b saw a's output via the context


def test_empty_flow_is_not_ok():
    run = run_flow([])
    assert run.ok is False
    assert run.failed_stage is None


def test_summary_renders_marks():
    run = run_flow([("a", _ok("a")), ("b", _fail("b"))])
    s = run.summary()
    assert "FLOW: FAILED @ b" in s
    assert "✅ a" in s and "❌ b" in s


# --- canonical stages (injected collaborators) ----------------------------

def test_stage_etl_passes_when_all_symbols_ingest():
    ctx = FlowContext(config={"universe": ["2330", "1101"],
                              "ingest": lambda u: {s: True for s in u}})
    res = stage_etl(ctx)
    assert res.ok and "2/2" in res.detail


def test_stage_etl_fails_on_partial_ingest():
    ctx = FlowContext(config={"universe": ["2330", "1101"],
                              "ingest": lambda u: {"2330": True, "1101": False}})
    assert stage_etl(ctx).ok is False


def test_stage_missing_collaborator_fails_clean():
    res = stage_signals(FlowContext(config={}))
    assert res.ok is False
    assert "missing collaborator 'signal_fn'" in res.detail


def test_stage_risk_gate_rejection():
    ctx = FlowContext(config={"risk_check": lambda sigs: (False, "L3 breaker HALTED")})
    res = stage_risk_gate(ctx)
    assert res.ok is False and res.detail == "L3 breaker HALTED"


def test_canonical_pipeline_end_to_end_with_stubs():
    ctx = FlowContext(config={
        "universe": ["2330"],
        "ingest": lambda u: {s: True for s in u},
        "signal_fn": lambda ctx: [{"stock_id": "2330", "action": "buy"}],
        "risk_check": lambda sigs: (True, "within limits"),
        "place": lambda sigs: [{"order": "buy 2330"}],
        "sink": lambda ctx: "run-123",
    })
    run = run_flow(build_daily_stages(), ctx)
    assert run.ok, run.summary()
    assert ctx.outputs["orders"] == [{"order": "buy 2330"}]
    assert run.stages[-1].detail == "logged → run-123"


def test_risk_rejection_halts_before_orders():
    placed = []
    ctx = FlowContext(config={
        "universe": ["2330"],
        "ingest": lambda u: {s: True for s in u},
        "signal_fn": lambda ctx: [{"action": "buy"}],
        "risk_check": lambda sigs: (False, "drawdown breaker"),
        "place": lambda sigs: placed.append(sigs) or sigs,
        "sink": lambda ctx: "x",
    })
    run = run_flow(build_daily_stages(), ctx)
    assert run.failed_stage == "risk_gate"
    assert placed == []  # orders stage never reached


def test_stage_orders_with_stub():
    ctx = FlowContext(config={"place": lambda sigs: [1, 2, 3]})
    res = stage_orders(ctx)
    assert res.ok and "3 orders" in res.detail


# --- demo ----------------------------------------------------------------

def test_demo_stages_all_pass():
    run = run_flow(demo_stages())
    assert run.ok
    assert [s.name for s in run.stages] == ["etl", "signals", "risk_gate", "orders", "log"]
