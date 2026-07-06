"""``/runs/{id}/report`` (aggregate) + ``/runs/{id}/notebook`` (Open-in-notebook).

The report endpoint assembles everything the Run-Report page needs in one call:
verdict block, sealed-window segments, month×year heatmap, drawdown-event table,
and the cost-sensitivity Sharpe pair. Fields it cannot source honestly come back
``null`` (no fabrication — #169 in-flight-null convention). The notebook endpoint
returns a valid ``.ipynb`` attachment prefilled to load the run in repo Jupyter.
"""
from __future__ import annotations

import json

from quant_platform.apps.api.routers import runs_report

# A minimal sidecar series: 6 equity points with one recovered + one open drawdown.
_SERIES = {
    "run_id": "r1",
    "equity": [100.0, 90.0, 95.0, 100.0, 80.0, 85.0],
    "drawdown": [0.0, -0.10, -0.05, 0.0, -0.20, -0.15],
    "trades": [{"ret": 0.04, "hold": 8, "entry_structure": 2}],
}


def _run(**over):
    rec = {
        "run_id": "r1",
        "strategy": "four_layer",
        "hypothesis": "baseline reproduce",
        "gate_status": "FAIL",
        "gate_summary": "GATE: FAIL\n  [FAIL] K1 CAGR>18%",
        "metrics": {"cagr": 0.05, "sharpe": 0.40, "slippage_sharpe": 0.31},
        "is_start": "2015-01-01",
        "is_end": "2020-12-31",
    }
    rec.update(over)
    return rec


# --------------------------------------------------------------------------- #
# report — happy path shape                                                    #
# --------------------------------------------------------------------------- #
def test_report_happy_path_shape(client, write_runs, monkeypatch):
    write_runs([_run()])
    monkeypatch.setattr(runs_report.run_series_store, "read_series", lambda rid: dict(_SERIES))

    body = client.get("/runs/r1/report").json()
    assert body["success"] is True
    data = body["data"]
    assert data["run_id"] == "r1"

    # verdict block: gate status + summary from the record, criteria from the gate.
    v = data["verdict"]
    assert v["gate_status"] == "FAIL"
    assert v["gate_summary"].startswith("GATE: FAIL")
    assert isinstance(v["criteria"], list) and v["criteria"][0]["key"] == "cagr"
    # no persisted validation / watch berth in a hermetic test → honest null.
    assert v["validation"] is None
    assert v["truth_gate"] is None

    # segments: the run's own window is always present.
    seg = data["segments"]
    assert seg["run_window"]["is_start"] == "2015-01-01"
    assert seg["run_window"]["is_end"] == "2020-12-31"

    # monthly matrix + drawdown events computed from the sidecar.
    assert data["monthly_returns"] is not None
    assert "matrix" in data["monthly_returns"]
    assert data["drawdown_events"][0]["depth"] > 0

    # cost sensitivity: the sharpe vs slippage_sharpe pair straight from metrics.
    assert data["cost_sensitivity"]["sharpe"] == 0.40
    assert data["cost_sensitivity"]["slippage_sharpe"] == 0.31


def test_report_series_missing_nulls_with_note(client, write_runs, monkeypatch):
    write_runs([_run()])
    monkeypatch.setattr(runs_report.run_series_store, "read_series", lambda rid: None)

    data = client.get("/runs/r1/report").json()["data"]
    assert data["monthly_returns"] is None
    assert data["drawdown_events"] is None
    # a note field explains WHY it is null (sidecar absent), never a bare null.
    assert data["monthly_returns_note"]


def test_report_cost_sensitivity_null_when_metric_absent(client, write_runs, monkeypatch):
    write_runs([_run(metrics={"cagr": 0.05})])  # no sharpe / slippage_sharpe
    monkeypatch.setattr(runs_report.run_series_store, "read_series", lambda rid: None)
    cost = client.get("/runs/r1/report").json()["data"]["cost_sensitivity"]
    assert cost["sharpe"] is None
    assert cost["slippage_sharpe"] is None


def test_report_unknown_strategy_gate_criteria_null(client, write_runs, monkeypatch):
    write_runs([_run(strategy="nope_not_registered")])
    monkeypatch.setattr(runs_report.run_series_store, "read_series", lambda rid: None)
    v = client.get("/runs/r1/report").json()["data"]["verdict"]
    assert v["criteria"] is None  # unknown strategy → no gate to declare, honest null
    assert v["gate_status"] == "FAIL"  # record fields still surface


def test_report_truth_gate_window_from_research_config(client, write_runs, monkeypatch):
    # inst_flow declares a TRUTH_GATE with a sealed oos_start/is_end boundary.
    write_runs([_run(strategy="inst_flow")])
    monkeypatch.setattr(runs_report.run_series_store, "read_series", lambda rid: None)
    seg = client.get("/runs/r1/report").json()["data"]["segments"]
    tgw = seg["truth_gate_window"]
    assert tgw is not None
    assert tgw["oos_start"] == "2021-01-01"  # the sealed boundary front-end draws


def test_report_truth_gate_window_null_when_absent(client, write_runs, monkeypatch):
    write_runs([_run(strategy="four_layer")])
    monkeypatch.setattr(runs_report.run_series_store, "read_series", lambda rid: None)
    seg = client.get("/runs/r1/report").json()["data"]["segments"]
    # four_layer declares no TRUTH_GATE (or it fails to load) → honest null, no 500.
    assert seg["truth_gate_window"] is None or "oos_start" in seg["truth_gate_window"]


def test_report_verdict_watch_berth_from_registry(client, write_runs, monkeypatch, tmp_path):
    write_runs([_run(strategy="inst_flow")])
    monkeypatch.setattr(runs_report.run_series_store, "read_series", lambda rid: None)
    # Seed a raw watch_registry enroll event (Paper-Watch band DSR).
    reg = tmp_path / "watch.jsonl"
    reg.write_text(
        json.dumps(
            {
                "strategy": "inst_flow",
                "event": "enroll",
                "verdict_dsr": 0.92,
                "enrolled_on": "2024-01-02",
                "re_enroll_evidence": None,
                "at": "2024-01-02T09:00:00+08:00",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("WATCH_REGISTRY_PATH", str(reg))

    v = client.get("/runs/r1/report").json()["data"]["verdict"]
    assert v["truth_gate"] is not None
    assert v["truth_gate"]["verdict_dsr"] == 0.92
    assert v["truth_gate"]["band"] == "PAPER_WATCH"
    assert v["truth_gate"]["state"] == "active"


def test_report_unknown_run_404(client):
    resp = client.get("/runs/ghost/report")
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "NOT_FOUND"


# --------------------------------------------------------------------------- #
# notebook — valid ipynb attachment + 404                                      #
# --------------------------------------------------------------------------- #
def test_notebook_returns_valid_ipynb(client, write_runs):
    write_runs([_run()])
    resp = client.get("/runs/r1/notebook")
    assert resp.status_code == 200
    assert resp.headers["content-disposition"] == 'attachment; filename="run_r1.ipynb"'

    nb = resp.json()
    # nbformat 4.x required top-level fields.
    assert nb["nbformat"] == 4
    assert "nbformat_minor" in nb
    assert isinstance(nb["metadata"], dict)
    assert isinstance(nb["cells"], list) and len(nb["cells"]) >= 3

    for cell in nb["cells"]:
        assert cell["cell_type"] in {"markdown", "code"}
        assert isinstance(cell["source"], list)
        assert isinstance(cell["metadata"], dict)
        assert "id" in cell
        if cell["cell_type"] == "code":
            assert cell["outputs"] == []
            assert cell["execution_count"] is None

    # first cell is the markdown header carrying the run identity.
    header = "".join(nb["cells"][0]["source"])
    assert "r1" in header
    assert "four_layer" in header
    # a code cell imports the platform + loads the run (repo-venv Jupyter, not REST).
    code = "\n".join("".join(c["source"]) for c in nb["cells"] if c["cell_type"] == "code")
    assert "quant_platform" in code
    assert "read_series" in code


def test_notebook_unknown_run_404(client):
    resp = client.get("/runs/ghost/notebook")
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "NOT_FOUND"
