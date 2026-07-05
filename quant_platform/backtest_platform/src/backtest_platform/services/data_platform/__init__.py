"""Data-platform service (W5.2) — bundle ingestion writer.

Groups the ETL-bundle persistence concern behind ``services.data_platform``:
the idempotent daily_bars / institutional_flows / broker_chips upsert extracted
out of ``data.db_writer`` (W5.2d). Builds on the connection kernel in
``data.db_kernel``; the legacy ``data.db_writer`` path keeps working via a
re-export shim during the migration window.
"""
