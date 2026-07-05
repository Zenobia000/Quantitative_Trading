"""Invariants pinned by the dependency-untangle refactor.

These lock the three seams the refactor established so a future edit that
re-introduces the coupling fails loudly:

1. A strategy's ``research_config`` declares its universe from ``config.universe``
   and MUST NOT drag in the zipline engine (previously it imported the zipline
   ``finmind_bundle`` just for ``DEFAULT_UNIVERSE``, pulling zipline + triggering
   its global bundle-registry side-effect).
2. ``import backtest_platform.strategies`` is the single registration seam — after
   it, every built-in strategy resolves via ``get_strategy(name)``.
3. ``inst_flow`` truth-gate ``n_trials`` equals the actual ``_GRID`` cardinality
   (the comment/value had drifted to 24 while the grid is 2×2×2×2 = 16).
"""
from __future__ import annotations

import math
import subprocess
import sys


def test_research_config_import_does_not_pull_zipline() -> None:
    """Importing a strategy research_config must not load zipline (subprocess-isolated).

    Runs in a fresh interpreter so the assertion is about *that import's* transitive
    closure, not modules other tests happened to load. zipline is importable in this
    environment, so a leak would genuinely show up — proving the decoupling holds.
    """
    code = (
        "import sys\n"
        "import backtest_platform.strategies.inst_flow.research_config  # noqa: F401\n"
        "leaked = sorted(m for m in sys.modules "
        "if m == 'zipline' or m.startswith('zipline.'))\n"
        "sys.stdout.write('LEAKED:' + ','.join(leaked))\n"
        "sys.exit(1 if leaked else 0)\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", code],
        env={"PYTHONPATH": __import__("os").pathsep.join(sys.path)},
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        "importing strategies.inst_flow.research_config pulled zipline "
        f"(stdout={result.stdout!r} stderr={result.stderr!r})"
    )


def test_importing_strategies_package_registers_all_builtins() -> None:
    """``import backtest_platform.strategies`` populates the strategy registry."""
    import backtest_platform.strategies  # noqa: F401 — the registration seam
    from backtest_platform.strategies.protocol import list_strategies

    assert {"four_layer", "inst_flow", "momentum", "template"}.issubset(
        set(list_strategies())
    )


def test_inst_flow_n_trials_matches_grid_cardinality() -> None:
    """Truth-gate ``n_trials`` must equal the number of ``_GRID`` combinations."""
    from backtest_platform.strategies.inst_flow import research_config as rc

    expected = math.prod(len(values) for values in rc._GRID.values())
    assert expected == 16  # 2×2×2×2 — guards against silent grid growth
    assert rc.TRUTH_GATE.n_trials == expected
