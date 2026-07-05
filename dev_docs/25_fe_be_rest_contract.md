# FE/BE REST Contract

> Canonical contract baseline for the current front-end and back-end REST surface.
> This file exists so `scripts/check_openapi_drift.py` can compare the live OpenAPI
> spec against a stable, human-readable inventory without chasing moving doc links.

## 1. Scope

This document is the thin contract bridge between:

- the live FastAPI/OpenAPI surface in `backtest_platform`
- the generated frontend snapshot in `frontend/openapi.json`
- the hand-written envelope and API usage notes in `frontend/src/types/domain.ts`
  and `frontend/src/services/http.ts`

It does not repeat the full API design rationale from
`dev_docs/product_repositioning/06_api_design_specification.md`.
That file remains the broader design reference; this document is the operational
contract baseline used by drift checks.

## 2. Contract Rules

- REST paths and methods listed here are the current canonical endpoint inventory.
- All client code must treat the OpenAPI snapshot as generated output.
- Any endpoint add/remove/rename must update this inventory in the same PR as the
  backend route change and the regenerated OpenAPI snapshot.
- If this table drifts from the live app, `scripts/check_openapi_drift.py` must fail.

## 3. Envelope Notes

- JSON payloads are UTF-8.
- Field names are `snake_case`.
- Timestamps are ISO 8601 UTC unless a domain object explicitly says otherwise.
- The frontend consumes an envelope layer and should not hand-roll API schemas that
  already exist in generated OpenAPI output.

## 4. OpenAPI Mapping

- The live OpenAPI document is the source for generated TS API types.
- `frontend/openapi.json` is the committed snapshot that should match the live app.
- `frontend/src/types/api.gen.ts` is regenerated from that snapshot.
- This doc only tracks the endpoint inventory needed for drift detection.

## 5. Drift Policy

If the live app and this document diverge:

1. update the backend route set
2. regenerate `frontend/openapi.json`
3. regenerate `frontend/src/types/api.gen.ts`
4. refresh the inventory table below

Do not move the canonical contract to another doc without also updating the drift
script and every reference that points here.

## 6. Endpoint Inventory

<!-- drift:endpoint-inventory:begin -->
| Method | Path | Zone | Note |
| :--- | :--- | :--- | :--- |
| GET | `/gate/spec` | Core | live OpenAPI operation |
| GET | `/health` | Core | live OpenAPI operation |
| GET | `/home/fleet` | Home | live OpenAPI operation |
| GET | `/home/recent` | Home | live OpenAPI operation |
| GET | `/home/research-status` | Home | live OpenAPI operation |
| GET | `/home/system-health` | Home | live OpenAPI operation |
| GET | `/monitor/board` | Monitor | live OpenAPI operation |
| GET | `/monitor/correlation` | Monitor | live OpenAPI operation |
| GET | `/monitor/fills` | Monitor | live OpenAPI operation |
| GET | `/monitor/fleet` | Monitor | live OpenAPI operation |
| GET | `/monitor/performance/benchmark` | Monitor | live OpenAPI operation |
| GET | `/monitor/performance/equity` | Monitor | live OpenAPI operation |
| GET | `/monitor/performance/kpi` | Monitor | live OpenAPI operation |
| GET | `/monitor/performance/monthly` | Monitor | live OpenAPI operation |
| GET | `/monitor/portfolio-summary` | Monitor | live OpenAPI operation |
| GET | `/monitor/positions/concentration` | Monitor | live OpenAPI operation |
| GET | `/monitor/positions/industry-allocation` | Monitor | live OpenAPI operation |
| GET | `/monitor/positions/kpi` | Monitor | live OpenAPI operation |
| GET | `/monitor/positions/prices` | Monitor | live OpenAPI operation |
| GET | `/monitor/positions/snapshot` | Monitor | live OpenAPI operation |
| GET | `/monitor/risk/events` | Monitor | live OpenAPI operation |
| GET | `/monitor/risk/events/{event_id}` | Monitor | live OpenAPI operation |
| GET | `/monitor/risk/mdd-trend` | Monitor | live OpenAPI operation |
| GET | `/monitor/risk/metrics` | Monitor | live OpenAPI operation |
| GET | `/monitor/signals` | Monitor | live OpenAPI operation |
| GET | `/monitor/signals/funnel` | Monitor | live OpenAPI operation |
| GET | `/monitor/signals/timeline` | Monitor | live OpenAPI operation |
| GET | `/monitor/strategies` | Monitor | live OpenAPI operation |
| GET | `/monitor/watch` | Monitor | live OpenAPI operation |
| GET | `/research/branches` | Research | live OpenAPI operation |
| GET | `/research/branches/{branch_id}` | Research | live OpenAPI operation |
| GET | `/research/branches/{branch_id}/compare` | Research | live OpenAPI operation |
| GET | `/research/candidates` | Research | live OpenAPI operation |
| GET | `/research/candidates/{candidate_id}` | Research | live OpenAPI operation |
| GET | `/research/evaluations/{evaluation_id}` | Research | live OpenAPI operation |
| GET | `/research/evaluations/{evaluation_id}/report` | Research | live OpenAPI operation |
| GET | `/research/live-oos/queue` | Research | live OpenAPI operation |
| GET | `/research/profiles` | Research | live OpenAPI operation |
| GET | `/research/profiles/{name}` | Research | live OpenAPI operation |
| GET | `/research/promote/{strategy_id}` | Research | live OpenAPI operation |
| GET | `/research/promote/{strategy_id}/audit` | Research | live OpenAPI operation |
| GET | `/research/saved-views` | Research | live OpenAPI operation |
| GET | `/research/strategies` | Research | live OpenAPI operation |
| GET | `/research/strategies/{strategy_id}/versions` | Research | live OpenAPI operation |
| GET | `/research/sweep/{job_id}/status` | Research | live OpenAPI operation |
| GET | `/research/universe-filters` | Research | live OpenAPI operation |
| GET | `/research/validate/{run_id}/gate-state` | Research | live OpenAPI operation |
| GET | `/research/validate/{run_id}/health` | Research | live OpenAPI operation |
| GET | `/research/validate/{run_id}/redline` | Research | live OpenAPI operation |
| GET | `/research/validate/{run_id}/wfa` | Research | live OpenAPI operation |
| GET | `/research/workflows/{strategy}` | Research | live OpenAPI operation |
| GET | `/runs` | Runs | live OpenAPI operation |
| GET | `/runs/compare` | Runs | live OpenAPI operation |
| GET | `/runs/estimate` | Runs | live OpenAPI operation |
| GET | `/runs/{job_id}/log` | Runs | live OpenAPI operation |
| GET | `/runs/{run_id}` | Runs | live OpenAPI operation |
| GET | `/runs/{run_id}/candles` | Runs | live OpenAPI operation |
| GET | `/runs/{run_id}/equity` | Runs | live OpenAPI operation |
| GET | `/runs/{run_id}/notebook` | Runs | live OpenAPI operation |
| GET | `/runs/{run_id}/report` | Runs | live OpenAPI operation |
| GET | `/runs/{run_id}/trades` | Runs | live OpenAPI operation |
| GET | `/strategies` | Strategies | live OpenAPI operation |
| GET | `/strategies/{strategy}/asset` | Strategies | live OpenAPI operation |
| GET | `/strategies/{strategy}/optimization-schema` | Strategies | live OpenAPI operation |
| GET | `/system/alerts/channels` | System | live OpenAPI operation |
| GET | `/system/alerts/history` | System | live OpenAPI operation |
| GET | `/system/alerts/rules` | System | live OpenAPI operation |
| GET | `/system/bundles` | System | live OpenAPI operation |
| GET | `/system/bundles/{bundle_id}/quality` | System | live OpenAPI operation |
| GET | `/system/datasets` | System | live OpenAPI operation |
| GET | `/system/ingest/{job_id}/status` | System | live OpenAPI operation |
| GET | `/system/risk/spec` | System | live OpenAPI operation |
| GET | `/system/universe/build/{job_id}/status` | System | live OpenAPI operation |
| GET | `/system/universes` | System | live OpenAPI operation |
| POST | `/gate/evaluate` | Core | live OpenAPI operation |
| POST | `/metrics/summary` | Core | live OpenAPI operation |
| POST | `/metrics/trades` | Core | live OpenAPI operation |
| POST | `/monitor/fleet/{strategy_id}/action` | Monitor | live OpenAPI operation |
| POST | `/monitor/watch/{strategy}/pause` | Monitor | live OpenAPI operation |
| POST | `/monitor/watch/{strategy}/resume` | Monitor | live OpenAPI operation |
| POST | `/research/branches` | Research | live OpenAPI operation |
| POST | `/research/branches/{branch_id}/evaluate` | Research | live OpenAPI operation |
| POST | `/research/candidates/{candidate_id}/decision` | Research | live OpenAPI operation |
| POST | `/research/candidates/{candidate_id}/select-live-oos` | Research | live OpenAPI operation |
| POST | `/research/promote/{strategy_id}` | Research | live OpenAPI operation |
| POST | `/research/saved-views` | Research | live OpenAPI operation |
| POST | `/research/simulate` | Research | live OpenAPI operation |
| POST | `/research/sweep` | Research | live OpenAPI operation |
| POST | `/research/trials/increment` | Research | live OpenAPI operation |
| POST | `/research/workflows/{workflow}` | Research | live OpenAPI operation |
| POST | `/runs` | Runs | live OpenAPI operation |
| POST | `/runs/async` | Runs | live OpenAPI operation |
| POST | `/runs/tag` | Runs | live OpenAPI operation |
| POST | `/system/alerts/history/{event_id}/ack` | System | live OpenAPI operation |
| POST | `/system/alerts/rules` | System | live OpenAPI operation |
| POST | `/system/alerts/test` | System | live OpenAPI operation |
| POST | `/system/ingest` | System | live OpenAPI operation |
| POST | `/system/risk/evaluate` | System | live OpenAPI operation |
| POST | `/system/universe/build` | System | live OpenAPI operation |
| PUT | `/system/alerts/channels` | System | live OpenAPI operation |
| PUT | `/system/alerts/rules` | System | live OpenAPI operation |
<!-- drift:endpoint-inventory:end -->

