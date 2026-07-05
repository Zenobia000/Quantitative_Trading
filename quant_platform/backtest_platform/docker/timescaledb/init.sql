-- Schema for four-layer resonance backtest platform.
-- Runs once on first container startup (Postgres docker-entrypoint convention).
-- Source of truth: dev_docs/21_data_contract.md §4 (7 tables after ADR-038
-- schema convergence: 3 M1 market-data + runs + equity_snapshots + signals + fills).
--
-- Dev-mode schema policy (ADR-038): init.sql is the SINGLE source of truth.
-- Data is disposable — a schema change means edit this file + recreate the DB
-- with `docker compose down -v && docker compose up`. There is no migration
-- runner; migrations return only when there is production data to preserve.

CREATE EXTENSION IF NOT EXISTS timescaledb;
CREATE EXTENSION IF NOT EXISTS pgcrypto;  -- gen_random_uuid()

-- ============================================================
-- M1 §4.2 — daily_bars : OHLCV per stock per trading day.
-- ============================================================
CREATE TABLE IF NOT EXISTS daily_bars (
    stock_id    TEXT        NOT NULL,
    trade_date  DATE        NOT NULL,
    open        NUMERIC(12, 4) NOT NULL,
    high        NUMERIC(12, 4) NOT NULL,
    low         NUMERIC(12, 4) NOT NULL,
    close       NUMERIC(12, 4) NOT NULL,
    volume      BIGINT      NOT NULL,
    adj_factor  NUMERIC(12, 6) NOT NULL DEFAULT 1.0,
    PRIMARY KEY (stock_id, trade_date)
);
SELECT create_hypertable('daily_bars', 'trade_date', if_not_exists => TRUE);
CREATE INDEX IF NOT EXISTS idx_daily_bars_stock ON daily_bars (stock_id, trade_date DESC);

-- ============================================================
-- M1 — institutional_flows : daily net buy/sell by major institution.
-- foreign / trust / dealer = 外資 / 投信 / 自營商
-- ============================================================
CREATE TABLE IF NOT EXISTS institutional_flows (
    stock_id     TEXT NOT NULL,
    trade_date   DATE NOT NULL,
    foreign_buy  BIGINT NOT NULL DEFAULT 0,
    trust_buy    BIGINT NOT NULL DEFAULT 0,
    dealer_buy   BIGINT NOT NULL DEFAULT 0,
    PRIMARY KEY (stock_id, trade_date)
);
SELECT create_hypertable('institutional_flows', 'trade_date', if_not_exists => TRUE);

-- ============================================================
-- M1 — broker_chips : daily net buy/sell from grouped brokers.
-- Top10 / key / gov / geo = 前十大 / 關鍵 / 官股 / 地緣
-- day_trade & margin_offset volumes are subtracted to compute net_volume.
-- ============================================================
CREATE TABLE IF NOT EXISTS broker_chips (
    stock_id              TEXT NOT NULL,
    trade_date            DATE NOT NULL,
    top_broker_buy        BIGINT NOT NULL DEFAULT 0,
    key_broker_buy        BIGINT NOT NULL DEFAULT 0,
    gov_broker_buy        BIGINT NOT NULL DEFAULT 0,
    geo_broker_buy        BIGINT NOT NULL DEFAULT 0,
    day_trade_volume      BIGINT NOT NULL DEFAULT 0,
    margin_offset_volume  BIGINT NOT NULL DEFAULT 0,
    PRIMARY KEY (stock_id, trade_date)
);
SELECT create_hypertable('broker_chips', 'trade_date', if_not_exists => TRUE);

-- ============================================================
-- M3 §4.x — runs : the Run as a first-class object (single source of truth).
-- Collects what used to be scattered reports/perf__/summary__ orphan files and
-- the orphan run_id columns on the time-series tables into one lineage-bearing
-- table. run_id = deterministic 12-char RunConfig hash (research/run_config.py).
-- A plain table (not a hypertable), so app-level linkage from the telemetry
-- tables (run_id column) could become a real FK once every paper-chain run_id
-- has a runs parent row (21 §4.2b) — deferred, not done.
-- ============================================================
CREATE TABLE IF NOT EXISTS runs (
    run_id            TEXT PRIMARY KEY,        -- deterministic RunConfig hash
    hypothesis        TEXT NOT NULL,           -- pre-registered (anti-overfit)
    strategy          TEXT NOT NULL,           -- registered strategy name (ADR-028, replaces preset)
    engine            TEXT NOT NULL DEFAULT 'sim',  -- sim (zipline/vectorbt removed 2026-07-03, ADR-037)
    stocks            JSONB NOT NULL,          -- universe for this run
    is_start          DATE NOT NULL,
    is_end            DATE NOT NULL,
    git_sha           TEXT,                    -- code lineage
    bundle_ref        TEXT,                    -- data bundle lineage
    cost_assumptions  JSONB,                   -- fee / tax / slippage
    params            JSONB,                   -- entry / exit params
    metrics           JSONB,                   -- result summary (cagr / sharpe / ...)
    gate_status       TEXT,                    -- 審判庭 verdict (PASS|FAIL|INCOMPLETE|...; enum evolves, unconstrained)
    gate_summary      TEXT,                    -- human-readable gate check summary
    status            TEXT NOT NULL DEFAULT 'created',  -- created|running|done|failed
    trials_count      INTEGER NOT NULL DEFAULT 0,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT runs_window_ck CHECK (is_start < is_end),
    CONSTRAINT runs_status_ck CHECK (status IN ('created', 'running', 'done', 'failed'))
);
CREATE INDEX IF NOT EXISTS idx_runs_strategy_created ON runs (strategy, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_runs_status ON runs (status, created_at DESC);

-- ============================================================
-- M2 §4.3 — equity_snapshots : per-run portfolio equity curve.
-- Composite PK = (snapshot_time, strategy_id, run_id) lets backtest
-- + paper + live share table without collision.
-- ============================================================
CREATE TABLE IF NOT EXISTS equity_snapshots (
    snapshot_time     TIMESTAMPTZ NOT NULL,
    strategy_id       TEXT NOT NULL,
    mode              TEXT NOT NULL,  -- 'backtest' | 'paper' | 'live'
    run_id            TEXT NOT NULL,  -- UUID per run
    equity            NUMERIC(18, 4) NOT NULL,
    cash              NUMERIC(18, 4) NOT NULL,
    positions_value   NUMERIC(18, 4) NOT NULL,
    open_positions    INTEGER NOT NULL,
    portfolio_heat    NUMERIC(6, 4),
    drawdown          NUMERIC(6, 4),
    daily_return      NUMERIC(8, 6),
    cumulative_return NUMERIC(8, 6),
    PRIMARY KEY (snapshot_time, strategy_id, run_id)
);
SELECT create_hypertable('equity_snapshots', 'snapshot_time',
    chunk_time_interval => INTERVAL '1 month',
    if_not_exists => TRUE);
CREATE INDEX IF NOT EXISTS idx_equity_snapshots_strategy
    ON equity_snapshots (strategy_id, snapshot_time DESC);
-- Retention: live mode keep forever (handled via partition exclusion at query layer);
-- backtest 90 days per §4.3.
SELECT add_retention_policy('equity_snapshots',
    INTERVAL '90 days',
    if_not_exists => TRUE);

-- ============================================================
-- M2 §4.5 — signals : decision log (must precede fills that reference it).
-- reason_json holds {scores, prices, context, gates} for replay
-- and post-mortem; GIN index enables JSONB containment queries.
-- ============================================================
CREATE TABLE IF NOT EXISTS signals (
    signal_id        UUID NOT NULL DEFAULT gen_random_uuid(),
    signal_time      TIMESTAMPTZ NOT NULL,
    strategy_id      TEXT NOT NULL,
    run_id           TEXT NOT NULL,
    stock_id         TEXT NOT NULL,
    action           TEXT NOT NULL,  -- buy/add/reduce/exit/stoploss/takeprofit/hold
    priority         INTEGER NOT NULL,  -- 1=stoploss .. 7=hold
    reason_json      JSONB NOT NULL,
    submitted        BOOLEAN DEFAULT FALSE,
    submitted_at     TIMESTAMPTZ,
    PRIMARY KEY (signal_time, signal_id)
);
SELECT create_hypertable('signals', 'signal_time',
    chunk_time_interval => INTERVAL '7 days',
    if_not_exists => TRUE);
CREATE INDEX IF NOT EXISTS idx_signals_strategy
    ON signals (strategy_id, signal_time DESC);
CREATE INDEX IF NOT EXISTS idx_signals_stock
    ON signals (stock_id, signal_time DESC);
CREATE INDEX IF NOT EXISTS idx_signals_reason_gin
    ON signals USING GIN (reason_json);

-- ============================================================
-- M4 §4.7 — fills : the single execution store (ADR-038).
-- A fill IS the execution record and owns its own table — there is no separate
-- `orders` table until a real broker order lifecycle lands (returns at M5).
-- order_id stays as a client-minted (uuid4) logical event id linking a fill to
-- the order intent that produced it; signal_id links to signals by value (plain
-- column, NOT a SQL FK — TimescaleDB 2.x rejects FKs to a hypertable, and both
-- fills and signals are hypertables; the link is enforced in app code and stays
-- portable to plain managed Postgres). strategy_id enables per-sleeve P&L
-- attribution (ADR-036 §3.4). slippage_bps = (fill_price - expected)/expected * 10000.
-- ============================================================
CREATE TABLE IF NOT EXISTS fills (
    fill_id          UUID NOT NULL DEFAULT gen_random_uuid(),
    fill_time        TIMESTAMPTZ NOT NULL,
    order_id         UUID NOT NULL,              -- client-minted logical event id
    signal_id        UUID,
    strategy_id      TEXT NOT NULL,              -- per-sleeve P&L (ADR-036 §3.4)
    stock_id         TEXT NOT NULL,
    side             TEXT NOT NULL,
    fill_price       NUMERIC(12, 4) NOT NULL,
    fill_quantity    INTEGER NOT NULL,
    commission       NUMERIC(10, 4),
    tax              NUMERIC(10, 4),
    slippage_bps     NUMERIC(8, 2),
    broker           TEXT NOT NULL,
    broker_trade_id  TEXT,
    PRIMARY KEY (fill_time, fill_id)
);
SELECT create_hypertable('fills', 'fill_time',
    chunk_time_interval => INTERVAL '7 days',
    if_not_exists => TRUE);
CREATE INDEX IF NOT EXISTS idx_fills_order ON fills (order_id);
CREATE INDEX IF NOT EXISTS idx_fills_stock ON fills (stock_id, fill_time DESC);
CREATE INDEX IF NOT EXISTS idx_fills_strategy ON fills (strategy_id, fill_time DESC);
