"""Strategy-runtime service — the daily/after-close pipeline cluster (W5.1c).

Landing zone for the load-bearing runtime orchestration extracted out of the
legacy ``orchestration`` and ``runtime`` packages:

* ``daily_flow``    — the fail-fast daily-pipeline flow engine (WBS 7.D).
* ``after_close``   — session-close use case + ``after-close`` exit-code mapping.
* ``timer_health``  — systemd/cron timer liveness derived from run markers.
* ``cli``           — the ``python -m ... cli`` entry point (systemd/cron drive it).
* ``paper_daemon``  — the paper-replay core the after-close runner shells out to.

Old import paths keep working via re-export shims during the migration window;
``orchestration/cli.py`` stays an *executable* shim so existing systemd units and
cron jobs pointing at the old module path do not break.
"""
