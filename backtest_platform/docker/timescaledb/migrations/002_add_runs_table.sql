-- Migration 002 — add the `runs` main table (8.G.1, Run single-source-of-truth).
--
-- For deployments created before the `runs` table existed in init.sql. Fresh
-- installs get the table from init.sql; this migration brings existing M1/M2
-- databases up to date. Idempotent (IF NOT EXISTS).
--
-- v0.1-min scope: table only. Retroactive FK constraints from the four
-- time-series tables (equity_snapshots / positions / signals / risk_metrics)
-- onto runs(run_id) are deferred to migration 003 (v0.2-full) — they require
-- every orphan run_id to first have a matching `runs` row, i.e. a backfill.

CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS runs (
    run_id            TEXT PRIMARY KEY,
    hypothesis        TEXT NOT NULL,
    preset            TEXT NOT NULL,
    engine            TEXT NOT NULL DEFAULT 'sim',
    stocks            JSONB NOT NULL,
    is_start          DATE NOT NULL,
    is_end            DATE NOT NULL,
    git_sha           TEXT,
    bundle_ref        TEXT,
    cost_assumptions  JSONB,
    params            JSONB,
    metrics           JSONB,
    status            TEXT NOT NULL DEFAULT 'created',
    trials_count      INTEGER NOT NULL DEFAULT 0,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT runs_window_ck CHECK (is_start < is_end),
    CONSTRAINT runs_status_ck CHECK (status IN ('created', 'running', 'done', 'failed'))
);
CREATE INDEX IF NOT EXISTS idx_runs_preset_created ON runs (preset, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_runs_status ON runs (status, created_at DESC);
