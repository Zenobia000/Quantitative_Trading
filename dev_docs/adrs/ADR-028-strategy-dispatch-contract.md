# ADR-028: Strategy Dispatch Contract & Preset Removal

**Date:** 2026-06-16
**Status:** Accepted
**Author:** Sunny + Claude
**Supersedes:** The `preset`/`get_preset` dispatch path introduced before ADR-027.
**Extends:** ADR-027 (strategy contract + registry)

---

## Context

ADR-027 introduced `StrategyRunner` + the registry, but dispatch (`is_harness._run_is_core`)
still hardwired `FourLayerRunner` via a preset bundle (`PRESETS`/`get_preset`).
AI-authored strategies registered in the registry could not be reached via the HTTP API
or CLI — the whole point of ADR-027's registry was unreachable from the outside.

Additionally, an architecture audit found 18 contract violations across all 4 built-in runners:
- V1 (8×): missing `config_model`/`title` ClassVar
- V2 (4×): `isinstance` guard silently discarded caller's validated config
- V3 (4×): empty-result `StrategyRun` missing required metric keys
- V4 (2×): `StrategyConfig` missing `with_extra_slippage()`; `FourLayerRunner` used raw `model_copy`

`StrategyConfig` also lived in the central `config/` package, making four_layer a
privileged citizen inconsistent with momentum/inst_flow (whose configs live with them).

---

## Decisions

| # | Decision | Rationale |
| :--- | :--- | :--- |
| D1 | `RunConfig` carries `strategy: str` + `params: dict`; params validated at dispatch by `config_model(**params)` | AI-friendly; keeps `RunConfig` decoupled from concrete strategy configs (no upward import — ADR-027); validation still strict via `frozen`+`extra="forbid"`. |
| D2 | `StrategyRunner` Protocol gains `config_model: ClassVar[type[BaseModel]]` + `title: ClassVar[str]` | One place to resolve name→Config for dispatch validation, schema (`GET /strategies`), and conformance gate. |
| D3 | Generic conformance gate (`check_strategy`) validates any runner on synthetic data | Required edge keys = `{cagr, sharpe, slippage_sharpe, maxdd, trades, bars}`. Used by CI (parametrized pytest over all registered strategies) and `validate-strategy` CLI. Sub-project ② reuses as load-time gate. |
| D4 | HTTP: `POST /runs` accepts `strategy`+`params`; `GET /strategies` exposes JSON-schema per strategy | ① is end-to-end demonstrable via curl; React frontend is a consumer (sub-project ③). |
| D5 | `preset` fully removed — no back-compat | `four_layer` is just a citizen; `preset` was a pre-contract privileged path. Mixed-state aliases rejected. |
| D6 | `StrategyConfig` relocated from `config/strategy_config.py` → `strategies/four_layer_resonance/config.py` | four_layer's config now lives with it (same as momentum/inst_flow), completing de-privileging. |

---

## V1-V4 Fixes (runner contract enforcement)

All 18 violations fixed in this ADR:
- V1: Every runner declares `config_model` + `title` ClassVar.
- V2: Runners use `cfg = config` (caller already validated via `config_model(**params)`) — no isinstance guard.
- V3: Empty-result `StrategyRun` carries all 6 required keys with 0.0 defaults.
- V4: `StrategyConfig.with_extra_slippage(slip)` added; `FourLayerRunner` uses it instead of raw `model_copy`.

---

## Consequences

**Positive:**
- Any AI-authored strategy that follows `_template` is: auto-covered by conformance pytest, reachable via `POST /runs {strategy, params}`, self-described by `GET /strategies`.
- `validate-strategy <name>` CLI lets an author self-check before push.
- Sub-project ② can reuse `check_strategy` as load-time gate for dynamic modules.
- `run_id` now hashes over `(strategy, sorted params, engine, sorted stocks, window)` — deterministic and strategy-aware.

**Accepted cost:**
- React frontend preset pages break until sub-project ③ rewires them to `GET /strategies`.
- `PRESETS`/`get_preset`/`DEFAULT_CONFIG_V3*` removed — callers pass raw `StrategyConfig(...)` with explicit fields.

---

## Blast Radius

- ~25 src files (preset removal + StrategyConfig relocation)
- 17 test files (mechanical rename)
- 8 additional test files (StrategyConfig import path update)
- `api/routers/presets.py` deleted; `api/routers/strategies.py` created
- React frontend 5 files: accepted breakage until ③
