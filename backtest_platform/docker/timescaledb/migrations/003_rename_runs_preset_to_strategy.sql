-- Migration 003 — rename runs.preset → runs.strategy (ADR-028 alignment).
--
-- ADR-028 renamed the strategy-identifier column from `preset` to `strategy`
-- in db_writer._RUNS_COLS, but the DDL layer (init.sql + migration 002) kept
-- `preset`. The result: upsert_runs() INSERTs an undefined `strategy` column,
-- so every write to the runs table fails (undefined column + NOT NULL). Fresh
-- installs now get `strategy` from the fixed init.sql; this migration brings
-- pre-existing M3 databases (that ran the old init.sql / migration 002) into
-- line. Fully idempotent — safe to re-run and safe on already-fixed installs.

-- Column rename, guarded so it runs at most once and never on a DB that has
-- already been fixed (fresh install where `strategy` exists and `preset` does not).
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'runs' AND column_name = 'preset'
    ) AND NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'runs' AND column_name = 'strategy'
    ) THEN
        ALTER TABLE runs RENAME COLUMN preset TO strategy;
    END IF;
END$$;

-- Normalise the lookup index name to the live column. Postgres keeps an index
-- pointing at the renamed column automatically, but under the old name; drop it
-- and recreate under the canonical name so schema dumps match init.sql.
DROP INDEX IF EXISTS idx_runs_preset_created;
CREATE INDEX IF NOT EXISTS idx_runs_strategy_created ON runs (strategy, created_at DESC);
