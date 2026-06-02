-- Schema for four-layer resonance backtest platform.
-- Runs once on first container startup (Postgres docker-entrypoint convention).
-- Source of truth: dev_docs/21_data_contract.md §4 (13 tables: M1 4 + M2-5 new 9).

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
-- M1 — universe : tracked stock pool (versioned per quarter).
-- v2.md 2.2 Universe definition.
-- ============================================================
CREATE TABLE IF NOT EXISTS universe (
    stock_id      TEXT NOT NULL,
    snapshot_date DATE NOT NULL,
    market_cap    NUMERIC(20, 0),
    industry      TEXT,
    listed_date   DATE,
    is_active     BOOLEAN NOT NULL DEFAULT TRUE,
    excluded_reason TEXT,
    PRIMARY KEY (stock_id, snapshot_date)
);

-- ============================================================
-- M1 legacy — trades : audit trail per v2.md 5.6.
-- Superseded by signals / orders / fills triple (M2/M4) but kept
-- for back-compat with existing dashboards until M4 cutover.
-- ============================================================
CREATE TABLE IF NOT EXISTS trades (
    trade_id        TEXT PRIMARY KEY,
    stock_id        TEXT NOT NULL,
    signal_type     TEXT NOT NULL,
    signal_time     TIMESTAMPTZ NOT NULL,
    execution_time  TIMESTAMPTZ,
    scores          JSONB NOT NULL,
    prices          JSONB NOT NULL,
    position        JSONB NOT NULL,
    strategy_version TEXT NOT NULL,
    notes           TEXT
);
CREATE INDEX IF NOT EXISTS idx_trades_stock_time ON trades (stock_id, signal_time DESC);
CREATE INDEX IF NOT EXISTS idx_trades_signal_type ON trades (signal_type, signal_time DESC);

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
-- M2 §4.4 — positions : current open + historical closed positions.
-- Regular table (not hypertable): row count bounded by Universe × time;
-- UPDATE-on-close pattern conflicts with hypertable's append optimisation.
-- ============================================================
CREATE TABLE IF NOT EXISTS positions (
    position_id      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    strategy_id      TEXT NOT NULL,
    run_id           TEXT NOT NULL,
    stock_id         TEXT NOT NULL,
    opened_at        TIMESTAMPTZ NOT NULL,
    closed_at        TIMESTAMPTZ,  -- NULL = open
    entry_price      NUMERIC(12, 4) NOT NULL,
    exit_price       NUMERIC(12, 4),
    quantity         INTEGER NOT NULL,
    stop_loss        NUMERIC(12, 4),
    take_profit      NUMERIC(12, 4),
    realized_pnl     NUMERIC(18, 4),
    unrealized_pnl   NUMERIC(18, 4),
    status           TEXT NOT NULL DEFAULT 'OPEN',  -- OPEN | CLOSED | LIQUIDATED
    UNIQUE (strategy_id, run_id, stock_id, opened_at)
);
CREATE INDEX IF NOT EXISTS idx_positions_open
    ON positions (strategy_id, status) WHERE status = 'OPEN';
CREATE INDEX IF NOT EXISTS idx_positions_stock
    ON positions (stock_id, opened_at DESC);

-- ============================================================
-- M2 §4.5 — signals : decision log (must precede orders/fills FK).
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
-- M4 §4.6 — orders : broker order records. FK to signals.
-- Note: hypertables don't support cross-chunk FK to non-hypertables;
-- since signals is also hypertable, FK on signal_id is best-effort
-- (TimescaleDB 2.x allows it but doesn't enforce across chunks fully).
-- ============================================================
CREATE TABLE IF NOT EXISTS orders (
    order_id         UUID NOT NULL DEFAULT gen_random_uuid(),
    created_at       TIMESTAMPTZ NOT NULL,
    signal_id        UUID REFERENCES signals(signal_id),
    broker           TEXT NOT NULL,  -- paper | shioaji
    stock_id         TEXT NOT NULL,
    side             TEXT NOT NULL,  -- Buy | Sell
    order_type       TEXT NOT NULL,  -- Market | Limit | MOC | LOC
    quantity         INTEGER NOT NULL,
    limit_price      NUMERIC(12, 4),  -- NULL for Market
    status           TEXT NOT NULL,
    broker_order_id  TEXT,
    submitted_at     TIMESTAMPTZ,
    completed_at     TIMESTAMPTZ,
    error_msg        TEXT,
    PRIMARY KEY (created_at, order_id)
);
SELECT create_hypertable('orders', 'created_at',
    chunk_time_interval => INTERVAL '7 days',
    if_not_exists => TRUE);
CREATE INDEX IF NOT EXISTS idx_orders_active
    ON orders (status) WHERE status IN ('PENDING', 'SUBMITTED', 'PARTIAL');
CREATE INDEX IF NOT EXISTS idx_orders_signal ON orders (signal_id);

-- ============================================================
-- M4 §4.7 — fills : execution reports.
-- slippage_bps = (fill_price - expected) / expected * 10000.
-- ============================================================
CREATE TABLE IF NOT EXISTS fills (
    fill_id          UUID NOT NULL DEFAULT gen_random_uuid(),
    fill_time        TIMESTAMPTZ NOT NULL,
    order_id         UUID NOT NULL,
    signal_id        UUID,
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

-- ============================================================
-- M3 §4.8 — risk_metrics : per-tick portfolio risk snapshot.
-- event_type NULL = normal; otherwise circuit-breaker level.
-- ============================================================
CREATE TABLE IF NOT EXISTS risk_metrics (
    metric_time        TIMESTAMPTZ NOT NULL,
    strategy_id        TEXT NOT NULL,
    run_id             TEXT NOT NULL,
    current_dd         NUMERIC(6, 4),
    var_95             NUMERIC(8, 4),
    cvar_95            NUMERIC(8, 4),
    portfolio_heat     NUMERIC(6, 4),
    concentration_top1 NUMERIC(5, 4),
    concentration_top3 NUMERIC(5, 4),
    hhi                NUMERIC(6, 5),
    sharpe_30d         NUMERIC(6, 3),
    sortino_30d        NUMERIC(6, 3),
    event_type         TEXT,  -- NULL | HEAT_WARN | CONCENT | L1_PAUSE | L2_CUT | L3_HALT
    event_context      JSONB,
    PRIMARY KEY (metric_time, strategy_id, run_id)
);
SELECT create_hypertable('risk_metrics', 'metric_time',
    chunk_time_interval => INTERVAL '1 month',
    if_not_exists => TRUE);
CREATE INDEX IF NOT EXISTS idx_risk_metrics_strategy
    ON risk_metrics (strategy_id, metric_time DESC);
CREATE INDEX IF NOT EXISTS idx_risk_metrics_events
    ON risk_metrics (event_type, metric_time DESC) WHERE event_type IS NOT NULL;

-- ============================================================
-- M3 §4.9 — validation_runs : PBO / DSR / WFA / CPCV / MC results.
-- Regular table: append-only at low rate, no hypertable benefit.
-- ============================================================
CREATE TABLE IF NOT EXISTS validation_runs (
    run_id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_time         TIMESTAMPTZ NOT NULL,
    method           TEXT NOT NULL,  -- PBO | DSR | WFA | CPCV | MC
    strategy_id      TEXT NOT NULL,
    params_json      JSONB NOT NULL,
    result_json      JSONB NOT NULL,
    summary_metric   NUMERIC(10, 6),
    pass_threshold   BOOLEAN
);
CREATE INDEX IF NOT EXISTS idx_validation_runs_strategy_method
    ON validation_runs (strategy_id, method, run_time DESC);
CREATE INDEX IF NOT EXISTS idx_validation_runs_result_gin
    ON validation_runs USING GIN (result_json);

-- ============================================================
-- §4.10 — data_quality_log : DQ check trail (enhanced from M1).
-- Migration note: if M1 deployment exists with old (check_time,
-- check_name) PK, run a migration script — fresh installs use this.
-- ============================================================
CREATE TABLE IF NOT EXISTS data_quality_log (
    check_id         BIGSERIAL PRIMARY KEY,
    check_time       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    source           TEXT NOT NULL,
    check_type       TEXT NOT NULL,
    stock_id         TEXT,
    trade_date       DATE,
    severity         TEXT NOT NULL,
    detail_json      JSONB NOT NULL,
    resolved         BOOLEAN DEFAULT FALSE,
    resolved_at      TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_dq_log_time
    ON data_quality_log (check_time DESC);
CREATE INDEX IF NOT EXISTS idx_dq_log_unresolved
    ON data_quality_log (resolved, severity) WHERE resolved = FALSE;

-- ============================================================
-- M4 §4.11 — alerts : Discord-bound alert queue.
-- sent_to_discord=FALSE rows are pending dispatch (drained by worker).
-- ============================================================
CREATE TABLE IF NOT EXISTS alerts (
    alert_id         UUID NOT NULL DEFAULT gen_random_uuid(),
    alert_time       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    rule_id          TEXT NOT NULL,
    level            TEXT NOT NULL,  -- critical | high | info
    title            TEXT NOT NULL,
    message          TEXT NOT NULL,
    context_json     JSONB,
    sent_to_discord  BOOLEAN DEFAULT FALSE,
    sent_at          TIMESTAMPTZ,
    PRIMARY KEY (alert_time, alert_id)
);
SELECT create_hypertable('alerts', 'alert_time',
    chunk_time_interval => INTERVAL '7 days',
    if_not_exists => TRUE);
CREATE INDEX IF NOT EXISTS idx_alerts_pending
    ON alerts (sent_to_discord, alert_time DESC) WHERE sent_to_discord = FALSE;
CREATE INDEX IF NOT EXISTS idx_alerts_rule
    ON alerts (rule_id, alert_time DESC);
