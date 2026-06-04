"""Structural validation of the provisioned Grafana dashboards (8.B / doc 20 §3).

Live Grafana import is reviewer-verified (no Grafana in this env); here we pin the
*structurally* checkable invariants: the 4 F/G/H/I dashboards exist, are valid
JSON with the required Grafana keys, have unique uids, and every panel binds the
provisioned ``influxdb-metrics`` datasource with a non-empty Flux query + a
threshold (the spec ties each panel to an alert threshold)."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

_GRAFANA = Path(__file__).resolve().parents[2] / "docker" / "grafana"
_DASH_DIR = _GRAFANA / "dashboards"
_DASHBOARDS = [
    "01_etl_health.json",
    "02_api_quota.json",
    "03_scheduler.json",
    "04_system_resources.json",
]
_DS_UID = "influxdb-metrics"


def _load(name: str) -> dict:
    return json.loads((_DASH_DIR / name).read_text(encoding="utf-8"))


def test_all_four_dashboards_present():
    assert sorted(p.name for p in _DASH_DIR.glob("*.json")) == sorted(_DASHBOARDS)


@pytest.mark.parametrize("name", _DASHBOARDS)
def test_dashboard_valid_json_required_keys(name):
    d = _load(name)
    for key in ("uid", "title", "schemaVersion", "version", "panels"):
        assert key in d, f"{name} missing top-level '{key}'"
    assert isinstance(d["panels"], list) and d["panels"], f"{name} has no panels"


def test_dashboard_uids_unique():
    uids = [_load(n)["uid"] for n in _DASHBOARDS]
    assert len(uids) == len(set(uids)), f"duplicate dashboard uids: {uids}"


@pytest.mark.parametrize("name", _DASHBOARDS)
def test_every_panel_binds_datasource_and_flux_query(name):
    for panel in _load(name)["panels"]:
        pid = panel.get("id")
        assert panel.get("datasource", {}).get("uid") == _DS_UID, \
            f"{name} panel {pid} not bound to provisioned datasource"
        targets = panel.get("targets", [])
        assert targets, f"{name} panel {pid} has no targets"
        for t in targets:
            q = t.get("query", "").strip()
            assert q, f"{name} panel {pid} empty query"
            assert "from(bucket:" in q, f"{name} panel {pid} target is not a Flux query"


@pytest.mark.parametrize("name", _DASHBOARDS)
def test_each_dashboard_has_threshold_alert_config(name):
    has = any(
        "thresholds" in p.get("fieldConfig", {}).get("defaults", {})
        for p in _load(name)["panels"]
    )
    assert has, f"{name} has no panel with a threshold/alert config"


def test_provisioning_files_reference_datasource_and_mount():
    ds = (_GRAFANA / "provisioning" / "datasources" / "influxdb.yaml").read_text(encoding="utf-8")
    assert _DS_UID in ds and "type: influxdb" in ds
    prov = (_GRAFANA / "provisioning" / "dashboards" / "dashboards.yaml").read_text(encoding="utf-8")
    assert "/etc/grafana/dashboards" in prov
