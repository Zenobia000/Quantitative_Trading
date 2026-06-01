"""zipline data bundle ingesters.

Each module registers a named bundle with zipline at import time via
`zipline.data.bundles.register()`. The bundle name becomes available to
`zipline ingest -b <name>` and `zipline run -b <name>`.
"""
