"""research.domain — pure research logic layer (W4.1a).

Framework/DB/IO-free building blocks: run identity + config, candidate lifecycle
state machine, run comparison, portfolio-space simulation, candle reshaping, and
notebook export. Old ``research.*`` module paths are kept as re-export shims so
external consumers (api/, strategies/, cli) need no change (ADR-R05: maintain
``quant_platform`` import paths during the clean-arch split).
"""
