"""Zone routers smoke — every GET endpoint returns a valid envelope.

monitor/system/home/research-extra ship mostly as typed-empty stubs (ADR-021
§5.4); this asserts the *shape contract* holds (success envelope, no 500) for
the whole surface, so the frontend can build against stable shapes.
"""
from __future__ import annotations

import pytest


def _get_paths(client) -> list[str]:
    """GET endpoints without path params (path-param routes 404 on bogus ids by design)."""
    app = client.app
    builtins = {"/openapi.json", "/docs", "/redoc", "/docs/oauth2-redirect"}
    return [
        r.path
        for r in app.routes
        if "GET" in getattr(r, "methods", set()) and r.path not in builtins and "{" not in r.path
    ]


def test_all_get_endpoints_return_envelope(client):
    paths = _get_paths(client)
    assert len(paths) > 30  # 接線後的端點規模（無 path-param 的 GET）
    for path in paths:
        resp = client.get(path)
        assert resp.status_code == 200, f"{path} → {resp.status_code}"
        body = resp.json()
        assert set(body) >= {"success", "data", "error"}, f"{path} missing envelope keys"
        assert body["success"] is True, f"{path} success != True"


@pytest.mark.parametrize(
    "path",
    ["/monitor/fleet", "/monitor/risk/metrics", "/system/bundles", "/home/research-status"],
)
def test_pending_endpoints_tagged(client, path):
    """Deferred endpoints carry meta.data_source (pending) — 不假造資料。"""
    body = client.get(path).json()
    # home/research-status 為真聚合（無 data_source）；其餘 pending
    if path != "/home/research-status":
        assert body.get("meta", {}).get("data_source", "").startswith("pending")
