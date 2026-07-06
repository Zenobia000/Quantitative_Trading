"""research.adapters — persistence / IO seam for the research layer (W4.1).

Clean-architecture adapters sub-package: file-backed stores and the
ledger→DB mirror mappers/writers live here, isolating IO and DDL-schema
knowledge from the pure research domain. Old ``research.*`` module paths are
kept as re-export shims so external consumers (api/, governance/, cli) need
no change (ADR-R05: maintain ``quant_platform`` import paths).
"""
