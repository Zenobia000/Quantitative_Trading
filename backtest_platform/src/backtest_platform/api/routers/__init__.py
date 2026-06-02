"""API routers — one module per resource (presets / runs / gate / metrics).

Each router is a thin HTTP adapter over a pure backend module; ``app.create_app``
mounts them. Routers own only request validation + serialization, never logic.
"""
