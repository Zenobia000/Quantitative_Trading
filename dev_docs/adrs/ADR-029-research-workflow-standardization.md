# ADR-029: Research Workflow Standardization

**Date:** 2026-06-16
**Status:** Accepted
**Extends:** ADR-028 (strategy dispatch contract), ADR-025 (truth gate)

---

## Context

`backtest_platform/scripts/` contained 7 files (all `inst_flow_*.py`) that:
1. Called strategy backtest functions directly, bypassing the ADR-028 dispatch layer.
2. Were broken post ADR-028 (`get_preset`/`DEFAULT_CONFIG` removed).
3. Required copying 7 files per new strategy — zero reuse.

## Decisions

1. **Generic workflows** in `research/workflows/` call `get_strategy().run()` exclusively.
2. **Per-strategy `research_config.py`** declares `DOEConfig`/`GOGatesConfig`/`TruthGateConfig`/`PaperReplayConfig` — strategy author fills in params (universe, grid, fixed_config, dates), not workflow logic.
3. **Loader** uses the runner's `__class__.__module__` to find `research_config.py`, handling strategy name ↔ module folder mismatches (e.g. `"four_layer"` → `four_layer_resonance/`).
4. **CLI**: `doe`/`go-gates`/`truth-gate`/`paper-replay` commands extend `research.cli`; `--dry-run` flag for config inspection.
5. **HTTP**: `POST /research/workflows/{workflow}` (async via 8.H.6 jobs); `GET /research/workflows/{strategy}`.
6. **`backtest_platform/scripts/` deleted** entirely.

## Consequences

- Adding a new strategy requires ONLY `research_config.py` — zero new scripts, zero workflow logic.
- All research workflows go through ADR-028 dispatch (`params` validated by `config_model`).
- Dispatch invariant enforced by static import scan in `test_doe.py`.
- `inst_flow_revalidate_finlab.py` (FinLab survivorship universe building) and `inst_flow_daemon_replay.py` (forward live daemon) were deferred — handled in separate ADRs/tasks.
