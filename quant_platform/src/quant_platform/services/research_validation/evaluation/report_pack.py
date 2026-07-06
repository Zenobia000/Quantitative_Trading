"""Re-export shim (W4.1b) — moved to ``research.adapters.report_pack``."""
from __future__ import annotations

from quant_platform.packages.adapters.report_pack import (
    DEFAULT_PACK_ROOT,
    write_report_pack,
)

__all__ = [
    "DEFAULT_PACK_ROOT",
    "write_report_pack",
]
