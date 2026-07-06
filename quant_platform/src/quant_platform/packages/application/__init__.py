"""research.application — orchestration / use-case layer (W4.1d).

The application layer composes the pure ``research.domain`` logic and the
``research.adapters`` IO seam into end-to-end use cases: the IS harness
(``run_is``/``run_and_judge``), parameter sweeps, batch fan-out, the evaluation
orchestrator, and the per-strategy ``research_config.py`` loader. Old
``research.*`` module paths are kept as re-export shims so external consumers
(api/, cli, tests) need no change (ADR-R05: maintain ``quant_platform``
import paths during the clean-arch split).
"""
