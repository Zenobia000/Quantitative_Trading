"""Universe registry — project ``universe_manifest.json`` into a named artifact.

The read model behind ``GET /system/universes`` (SPEC-01 Slice 1, ADR-007): a
*named* survivorship-clean universe a strategy can **reference** and the New Run
form can **select**, rather than everyone re-typing a raw symbol list. It is a thin
projection over :func:`data.bundle_registry.iter_manifests` (the shared defensive
scan), filtered to universe builds.

ADR-007 N:1 read-compat: a manifest may carry the legacy singular ``strategy`` (one
strategy) or the new plural ``strategies`` (many strategies share one factor-agnostic
universe). Both normalise to the immutable :attr:`UniverseRef.strategies` tuple, so
the caller never branches on manifest age. Pure filesystem + JSON, never raises — a
missing root / corrupt manifest simply yields fewer rows (typed-empty contract).
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from quant_platform.services.data_platform.bundle_registry import iter_manifests

_KIND_UNIVERSE = "universe"


@dataclass(frozen=True, slots=True)
class UniverseRef:
    """One named, selectable universe — the ``GET /system/universes`` row shape.

    Answers "which reproducible stock population is this": identity (``id``/``name``),
    size (``symbols_count``), the point-in-time span, the build knobs, the referencing
    strategies (N:1), and where it materialised (``cache_dir``).
    """

    id: str
    name: str
    symbols_count: int
    span_start: str | None
    span_end: str | None
    top_n: int | None
    min_turnover: float | None
    strategies: tuple[str, ...]
    cache_dir: str
    generated_at: str | None


def _strategies_of(manifest: dict) -> tuple[str, ...]:
    """Normalise legacy ``strategy: str`` / new ``strategies: [str]`` → a tuple."""
    plural = manifest.get("strategies")
    if isinstance(plural, list):
        return tuple(str(s) for s in plural)
    single = manifest.get("strategy")
    return (str(single),) if single else ()


def _to_universe_ref(cache_dir: Path, manifest: dict) -> UniverseRef:
    """Project one universe manifest into a :class:`UniverseRef`."""
    params = manifest.get("params") or {}
    symbols = manifest.get("symbols") or []
    return UniverseRef(
        id=cache_dir.name,
        name=str(manifest.get("name") or cache_dir.name),
        symbols_count=int(manifest.get("n_symbols", len(symbols))),
        span_start=params.get("span_start"),
        span_end=params.get("span_end"),
        top_n=params.get("top_n"),
        min_turnover=params.get("min_turnover"),
        strategies=_strategies_of(manifest),
        cache_dir=params.get("cache_dir") or str(cache_dir),
        generated_at=manifest.get("generated_at"),
    )


def symbols_for(universe_id: str, data_root: Path | None = None) -> tuple[str, ...] | None:
    """Resolve a named universe's full symbol list from its manifest.

    Returns the symbols tuple, or ``None`` if no universe with that id exists (the
    caller maps ``None`` to a 422 — selecting a non-existent pool is an error). A
    universe whose manifest carries no ``symbols`` yields an empty tuple. This is the
    server-side resolver behind the New Run pool picker (SPEC-01 Slice 2): the
    survivorship-clean symbol set travels with the *selection*, never re-typed."""
    for cache_dir, kind, manifest in iter_manifests(data_root):
        if kind == _KIND_UNIVERSE and cache_dir.name == universe_id:
            syms = manifest.get("symbols")
            return tuple(str(s) for s in syms) if isinstance(syms, list) else ()
    return None


def list_universes(data_root: Path | None = None) -> list[UniverseRef]:
    """Discover every named universe under ``data_root`` (default ``data/``).

    One :class:`UniverseRef` per ``parquet*`` cache carrying a readable
    ``universe_manifest.json``, sorted by id (``iter_manifests`` yields sorted).
    Default (non-universe) ETL caches are excluded. Never raises: a malformed
    manifest field skips that cache so the endpoint serves a typed-empty envelope.
    """
    universes: list[UniverseRef] = []
    for cache_dir, kind, manifest in iter_manifests(data_root):
        if kind != _KIND_UNIVERSE:
            continue
        try:
            universes.append(_to_universe_ref(cache_dir, manifest))
        except (TypeError, ValueError):
            continue  # malformed manifest field — skip this cache, never abort
    return universes
