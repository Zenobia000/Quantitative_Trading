-- Schema for four-layer resonance backtest platform.
-- Runs once on first container startup (Postgres docker-entrypoint convention).

CREATE EXTENSION IF NOT EXISTS timescaledb;

-- ============================================================
-- daily_bars : OHLCV per stock per trading day.
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
-- institutional_flows : daily net buy/sell by major institution.
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
-- broker_chips : daily net buy/sell from grouped brokers.
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
-- universe : tracked stock pool (versioned per quarter).
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
-- trades : audit trail per v2.md 5.6.
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
-- equity_snapshots : daily portfolio equity for monitoring.
-- ============================================================
CREATE TABLE IF NOT EXISTS equity_snapshots (
    snapshot_time   TIMESTAMPTZ NOT NULL,
    strategy_id     TEXT NOT NULL,
    equity          NUMERIC(20, 2) NOT NULL,
    cash            NUMERIC(20, 2) NOT NULL,
    positions_value NUMERIC(20, 2) NOT NULL,
    open_positions  INTEGER NOT NULL,
    portfolio_heat  NUMERIC(6, 4) NOT NULL,
    drawdown        NUMERIC(6, 4) NOT NULL,
    PRIMARY KEY (strategy_id, snapshot_time)
);
SELECT create_hypertable('equity_snapshots', 'snapshot_time', if_not_exists => TRUE);

-- ============================================================
-- data_quality_log : per v2.md 5.2 monitoring.
-- ============================================================
CREATE TABLE IF NOT EXISTS data_quality_log (
    check_time   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    check_name   TEXT NOT NULL,
    target_date  DATE,
    passed       BOOLEAN NOT NULL,
    detail       JSONB,
    PRIMARY KEY (check_time, check_name)
);
