"""InfluxDB line-protocol metric writer (8.D.1).

System-health metrics (CPU/quota/scheduler/ETL state) are pushed to InfluxDB and
visualised in Grafana, per dev_docs/20_dashboard_specification.md §3. This module
provides two things:

1. ``format_line`` — a pure function that renders an InfluxDB **line protocol**
   record with correct escaping, deterministic tag/field ordering and the ``i``
   integer-field suffix.
2. ``InfluxWriter`` — a thin, *graceful* writer. Metrics are best-effort
   telemetry: if the ``influxdb-client`` library is missing, the broker is
   unreachable, or a write blows up, the writer logs a warning and returns
   ``False`` instead of letting the failure bubble into the trading hot path.

Design notes
------------
* **Strategy-agnostic.** Nothing here knows about any particular strategy; it is
  reusable infrastructure for emitting ``etl_run`` / ``api_quota`` /
  ``scheduler_run`` / ``api_health`` / ``system`` measurements.
* **Injectable client.** Tests (and callers who already hold a connection) can
  pass a ``client`` implementing the ``influxdb_client.InfluxDBClient`` contract
  (``write_api(...).write(bucket, org, record)`` + ``close()``). When omitted the
  writer tries to lazily import ``influxdb_client``; absence is not fatal.

Line protocol reference (InfluxDB 2.7):
    <measurement>[,<tag_key>=<tag_value>...] <field_key>=<field_value>[,...] [<ts>]
"""
from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from loguru import logger

__all__ = ["InfluxWriter", "format_line"]


# ---------------------------------------------------------------------------
# Line-protocol escaping
#
# The escaping rules differ per token type (InfluxDB line-protocol spec):
#   - measurement:           escape  comma, space          (NOT '=')
#   - tag key / tag value /
#     field key:             escape  comma, space, '='
#   - string field value:    wrap in double quotes; escape '"' and '\'
# ---------------------------------------------------------------------------


def _escape_measurement(value: str) -> str:
    return value.replace(",", "\\,").replace(" ", "\\ ")


def _escape_key(value: str) -> str:
    """Escape a tag key, tag value, or field key."""
    return value.replace(",", "\\,").replace("=", "\\=").replace(" ", "\\ ")


def _escape_str_field(value: str) -> str:
    """Escape a string field value (the inside of the surrounding quotes)."""
    return value.replace("\\", "\\\\").replace('"', '\\"')


def _format_field_value(value: Any) -> str:
    """Render a single field value with the correct line-protocol type marker.

    - ``bool``  -> ``true`` / ``false``  (checked *before* int: bool is an int)
    - ``int``   -> ``<n>i``              (integer-field suffix)
    - ``float`` -> ``<x>``               (no suffix)
    - other     -> quoted, escaped string
    """
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return f"{value}i"
    if isinstance(value, float):
        return _format_float(value)
    return f'"{_escape_str_field(str(value))}"'


def _format_float(value: float) -> str:
    """Render a float field value.

    Whole-valued floats (e.g. ``480.0``) collapse to their integer text
    (``"480"``) — InfluxDB still types them as floats because there is no ``i``
    suffix — while fractional values keep full ``repr`` precision (``"512.5"``).
    """
    if value == int(value):
        return str(int(value))
    return repr(value)


def format_line(
    measurement: str,
    tags: dict[str, Any],
    fields: dict[str, Any],
    timestamp: int | None = None,
) -> str:
    """Render one InfluxDB line-protocol record.

    Args:
        measurement: Measurement name (e.g. ``"etl_run"``). Commas/spaces escaped.
        tags: Tag set. Keys are sorted lexicographically so identical inputs
            always produce byte-identical output (deterministic, test-friendly).
            All values are coerced to ``str``.
        fields: Field set. At least one field is required by the protocol.
            ``int`` values get an ``i`` suffix; ``float`` values do not; ``bool``
            renders as ``true``/``false``; everything else is a quoted string.
        timestamp: Optional nanosecond epoch timestamp. Omitted when ``None`` so
            the server stamps arrival time.

    Returns:
        A single line-protocol string (no trailing newline).

    Raises:
        ValueError: if ``fields`` is empty (line protocol mandates >= 1 field).
    """
    if not fields:
        raise ValueError("line protocol requires at least one field")

    head = _escape_measurement(measurement)

    if tags:
        tag_str = ",".join(
            f"{_escape_key(str(k))}={_escape_key(str(v))}"
            for k, v in sorted(tags.items(), key=lambda kv: str(kv[0]))
        )
        head = f"{head},{tag_str}"

    field_str = ",".join(
        f"{_escape_key(str(k))}={_format_field_value(v)}"
        for k, v in sorted(fields.items(), key=lambda kv: str(kv[0]))
    )

    line = f"{head} {field_str}"
    if timestamp is not None:
        line = f"{line} {timestamp}"
    return line


# ---------------------------------------------------------------------------
# Writer
# ---------------------------------------------------------------------------


@runtime_checkable
class _WriteApi(Protocol):
    def write(self, bucket: str, org: str, record: str) -> None: ...


@runtime_checkable
class _InfluxClient(Protocol):
    def write_api(self, **kwargs: Any) -> _WriteApi: ...

    def close(self) -> None: ...


class InfluxWriter:
    """Best-effort InfluxDB metric writer with graceful degradation.

    The writer never raises from :meth:`write`. Any failure — missing library,
    unreachable broker, backend exception — is logged (once, to avoid spamming
    the log) and reported as a ``False`` return value, so emitting telemetry can
    never take down the caller.

    Args:
        url: InfluxDB base URL (e.g. ``http://localhost:8086``).
        token: API token.
        org: Organisation name.
        bucket: Target bucket / database.
        client: Optional pre-built client implementing the
            ``influxdb_client.InfluxDBClient`` contract. When provided it is used
            verbatim (the canonical path for tests and connection reuse). When
            ``None`` the writer lazily imports ``influxdb_client``; if that import
            fails the writer is permanently in degraded mode.
    """

    def __init__(
        self,
        *,
        url: str,
        token: str,
        org: str,
        bucket: str,
        client: _InfluxClient | None = None,
    ) -> None:
        self._url = url
        self._token = token
        self._org = org
        self._bucket = bucket
        self._client: _InfluxClient | None = client
        self._degraded_logged = False

        if self._client is None:
            self._client = self._try_build_client()

    def _try_build_client(self) -> _InfluxClient | None:
        """Attempt to construct a real InfluxDB client; return None if unavailable."""
        try:
            from influxdb_client import InfluxDBClient  # type: ignore[import-not-found]
        except ImportError:
            return None
        try:
            return InfluxDBClient(url=self._url, token=self._token, org=self._org)
        except Exception as exc:  # pragma: no cover - construction rarely fails offline
            logger.warning(
                "InfluxDBClient construction failed ({}); metrics disabled.", exc
            )
            return None

    def _warn_degraded_once(self, reason: str) -> None:
        if not self._degraded_logged:
            logger.warning(
                "InfluxWriter degraded ({}); metrics will be dropped silently.",
                reason,
            )
            self._degraded_logged = True

    def write(
        self,
        measurement: str,
        tags: dict[str, Any],
        fields: dict[str, Any],
        timestamp: int | None = None,
    ) -> bool:
        """Format and write a single metric point.

        Returns:
            ``True`` if the record was handed to a live client without error,
            ``False`` on any degraded condition (no client, write failure). Never
            raises — a metrics outage must not disturb the trading path.
        """
        if self._client is None:
            self._warn_degraded_once("influxdb-client not installed or client unavailable")
            return False

        try:
            record = format_line(measurement, tags, fields, timestamp)
        except ValueError as exc:
            # A malformed point is a programming error in the caller, but we still
            # refuse to crash the hot path — log and drop.
            logger.warning("Dropping malformed metric point: {}", exc)
            return False

        try:
            write_api = self._client.write_api()
            write_api.write(bucket=self._bucket, org=self._org, record=record)
            return True
        except Exception as exc:
            self._warn_degraded_once(f"write failed: {exc}")
            return False

    def close(self) -> None:
        """Close the underlying client if any. Safe to call repeatedly."""
        client = self._client
        if client is None:
            return
        try:
            client.close()
        except Exception as exc:  # pragma: no cover - close rarely fails
            logger.debug("InfluxWriter.close() ignored error: {}", exc)
