"""Validation utilities — cross-check zipline_adapter output against
M1 baseline (純函式 ground truth) and a minimal hand-written vectorized
PnL (no framework dependency).

ADR-013 §J recovery plan: vectorbt with pandas<2 is incompatible with our
stack; M1 pipeline.py + self-written vectorized PnL together provide
sufficient cross-check for Sprint 2 M2 acceptance.
"""
