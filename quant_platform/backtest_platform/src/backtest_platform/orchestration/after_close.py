"""Re-export shim (W5.1c) — moved to ``services.strategy_runtime.after_close``."""
from backtest_platform.services.strategy_runtime.after_close import (
    AFTER_CLOSE_TIME,
    DEFAULT_MARKER_PATH,
    AfterCloseResult,
    AfterCloseStatus,
    SessionSummary,
    already_done,
    build_session_runner,
    default_expire_watches,
    default_is_trading_day,
    default_watch_status,
    record_done,
    run_after_close,
    safe_discord_notify,
)

__all__ = [
    "AFTER_CLOSE_TIME",
    "DEFAULT_MARKER_PATH",
    "AfterCloseResult",
    "AfterCloseStatus",
    "SessionSummary",
    "already_done",
    "build_session_runner",
    "default_expire_watches",
    "default_is_trading_day",
    "default_watch_status",
    "record_done",
    "run_after_close",
    "safe_discord_notify",
]
