-- Migration 004 — add runs.gate_status + runs.gate_summary (A0 run persistence).
--
-- A0 wires the research ledger's DB mirror (`research/run_persist.py` →
-- `db_writer.upsert_runs`), and the ledger record carries the 審判庭 verdict
-- (`gate_status` / `gate_summary`) that the runs DDL had no columns for.
-- Folding the verdict into `metrics` JSONB would conflate measurements with
-- judgement, so the verdict gets its own nullable TEXT columns. gate_status is
-- deliberately unconstrained: the verdict enum evolves (PAPER_WATCH was added
-- in ADR-033) and a CHECK would turn every new tier into a migration.
--
-- Fresh installs get the columns from the fixed init.sql; this migration brings
-- pre-existing databases into line. Fully idempotent — safe to re-run.

ALTER TABLE runs ADD COLUMN IF NOT EXISTS gate_status  TEXT;
ALTER TABLE runs ADD COLUMN IF NOT EXISTS gate_summary TEXT;
