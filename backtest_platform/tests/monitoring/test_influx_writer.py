"""Unit tests for the InfluxDB line-protocol writer.

Fully hermetic: no real InfluxDB, no network, no UDP. The line-protocol
formatter is a pure function; the writer is exercised with an injected fake
client and with the real (degraded) path when no client/library is present.

Spec: dev_docs/20_dashboard_specification.md §3 (Grafana + InfluxDB, line
protocol, measurements etl_run / api_quota / scheduler_run / api_health / system).
"""
from __future__ import annotations

from typing import Any

import pytest

from backtest_platform.monitoring.influx_writer import (
    InfluxWriter,
    format_line,
)


# ---------------------------------------------------------------------------
# format_line — pure line-protocol formatting
# ---------------------------------------------------------------------------


def test_basic_line_no_tags() -> None:
    line = format_line("etl_run", {}, {"count": 1}, timestamp=None)
    assert line == "etl_run count=1i"


def test_float_field_has_no_i_suffix() -> None:
    line = format_line("api_quota", {}, {"remaining_mb": 512.5}, timestamp=None)
    assert line == "api_quota remaining_mb=512.5"


def test_int_field_gets_i_suffix() -> None:
    line = format_line("api_error", {}, {"count": 10}, timestamp=None)
    assert line == "api_error count=10i"


def test_bool_field_serialized_lowercase() -> None:
    line = format_line("api_health", {}, {"connected": True}, timestamp=None)
    assert line == "api_health connected=true"
    line2 = format_line("api_health", {}, {"connected": False}, timestamp=None)
    assert line2 == "api_health connected=false"


def test_string_field_is_quoted_and_escaped() -> None:
    line = format_line(
        "etl_run",
        {},
        {"status": 'FAIL "429"', "note": "back\\slash"},
        timestamp=None,
    )
    # string field values are wrapped in double quotes; inner " and \ escaped
    assert 'status="FAIL \\"429\\""' in line
    assert 'note="back\\\\slash"' in line


def test_tags_are_sorted_by_key() -> None:
    # Pass tags out of order; output must be lexicographically sorted by key
    line = format_line(
        "etl_run",
        {"status": "ok", "source": "finlab", "endpoint": "price"},
        {"count": 1},
        timestamp=None,
    )
    assert line == "etl_run,endpoint=price,source=finlab,status=ok count=1i"


def test_tag_special_chars_escaped() -> None:
    # In tag keys/values: spaces, commas and '=' must be backslash-escaped.
    line = format_line(
        "etl_run",
        {"region": "ap east", "k=v": "a,b"},
        {"count": 1},
        timestamp=None,
    )
    assert "region=ap\\ east" in line
    assert "k\\=v=a\\,b" in line


def test_measurement_special_chars_escaped() -> None:
    # In measurement: spaces and commas escaped, but NOT '='.
    line = format_line("weird name,x", {}, {"v": 1}, timestamp=None)
    assert line.startswith("weird\\ name\\,x ")


def test_field_key_special_chars_escaped() -> None:
    # Field keys escape space, comma and '=' (same as tag keys).
    line = format_line("m", {}, {"a b": 1}, timestamp=None)
    assert "a\\ b=1i" in line


def test_timestamp_appended_when_given() -> None:
    line = format_line("m", {"t": "x"}, {"v": 1}, timestamp=1700000000000000000)
    assert line == "m,t=x v=1i 1700000000000000000"


def test_multiple_fields_sorted_for_determinism() -> None:
    line = format_line("m", {}, {"b": 2, "a": 1}, timestamp=None)
    assert line == "m a=1i,b=2i"


def test_empty_fields_raises() -> None:
    with pytest.raises(ValueError, match="at least one field"):
        format_line("m", {}, {}, timestamp=None)


# ---------------------------------------------------------------------------
# InfluxWriter — graceful degradation (no client / no library)
# ---------------------------------------------------------------------------


def test_write_returns_false_when_no_client_and_no_library() -> None:
    # Default construction: influxdb-client is not installed in this env, so the
    # writer must degrade gracefully — log a warning and return False, never raise.
    writer = InfluxWriter(
        url="http://localhost:8086",
        token="tok",
        org="org",
        bucket="metrics",
    )
    result = writer.write("etl_run", {"source": "finlab"}, {"count": 1})
    assert result is False


def test_write_does_not_raise_on_degraded_path() -> None:
    writer = InfluxWriter(url="http://localhost:8086", token="t", org="o", bucket="b")
    # Should never propagate an exception even though nothing is wired up.
    assert writer.write("system", {"host": "h1"}, {"cpu": 0.5}) is False


def test_warning_logged_once_then_suppressed(caplog: pytest.LogCaptureFixture) -> None:
    """Degraded warning should fire on first write, then stay quiet to avoid log spam."""
    import logging

    from backtest_platform.monitoring import influx_writer as mod

    messages: list[str] = []
    monkeypatch_sink_id = mod.logger.add(
        lambda m: messages.append(str(m)), level="WARNING"
    )
    try:
        writer = InfluxWriter(url="u", token="t", org="o", bucket="b")
        writer.write("m", {}, {"v": 1})
        writer.write("m", {}, {"v": 2})
    finally:
        mod.logger.remove(monkeypatch_sink_id)

    warnings = [m for m in messages if "WARNING" in m]
    assert len(warnings) == 1


# ---------------------------------------------------------------------------
# InfluxWriter — injected fake client
# ---------------------------------------------------------------------------


class _FakeWriteApi:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def write(self, bucket: str, org: str, record: str) -> None:
        self.calls.append({"bucket": bucket, "org": org, "record": record})


class _FakeClient:
    """Mimics influxdb_client.InfluxDBClient.write_api() contract."""

    def __init__(self) -> None:
        self._api = _FakeWriteApi()
        self.closed = False

    def write_api(self, **kwargs: Any) -> _FakeWriteApi:
        return self._api

    def close(self) -> None:
        self.closed = True


def test_injected_client_receives_formatted_line() -> None:
    fake = _FakeClient()
    writer = InfluxWriter(
        url="http://x:8086", token="t", org="myorg", bucket="metrics", client=fake
    )

    ok = writer.write("etl_run", {"source": "finlab", "status": "ok"}, {"count": 3})

    assert ok is True
    assert len(fake._api.calls) == 1
    call = fake._api.calls[0]
    assert call["bucket"] == "metrics"
    assert call["org"] == "myorg"
    assert call["record"] == "etl_run,source=finlab,status=ok count=3i"


def test_injected_client_write_failure_degrades(caplog: pytest.LogCaptureFixture) -> None:
    class _BoomApi:
        def write(self, *a: Any, **k: Any) -> None:
            raise RuntimeError("connection refused")

    class _BoomClient:
        def write_api(self, **kwargs: Any) -> Any:
            return _BoomApi()

        def close(self) -> None:
            pass

    writer = InfluxWriter(
        url="u", token="t", org="o", bucket="b", client=_BoomClient()
    )
    # A live-but-failing backend must still not crash the caller.
    assert writer.write("m", {}, {"v": 1}) is False


def test_write_point_helper_matches_format_line() -> None:
    fake = _FakeClient()
    writer = InfluxWriter(url="u", token="t", org="o", bucket="b", client=fake)
    writer.write("api_quota", {"provider": "finlab"}, {"remaining_mb": 480.0})
    assert (
        fake._api.calls[0]["record"]
        == "api_quota,provider=finlab remaining_mb=480"
    )


def test_close_is_idempotent_and_safe() -> None:
    fake = _FakeClient()
    writer = InfluxWriter(url="u", token="t", org="o", bucket="b", client=fake)
    writer.close()
    assert fake.closed is True
    # second close must not raise
    writer.close()
