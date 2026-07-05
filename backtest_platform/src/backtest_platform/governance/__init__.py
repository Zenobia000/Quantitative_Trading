"""Governance & Release (golden SAD Layer 3).

Owns the strategy release lifecycle — the draft→paper→live promotion ladder and
its immutable audit — extracted out of the Layer-2 research package per ADR-R02.
Governance depends *on* research outputs (StrategyDefinition/gate verdicts); the
reverse is forbidden (see import-linter contract: research ⊄ governance).
"""
