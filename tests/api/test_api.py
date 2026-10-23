"""API (always replay-only). Uses the tmp-built seed-42 databases."""
import json
import os
import shutil

import pytest
from fastapi.testclient import TestClient

from common.banner import SYNTHETIC_BANNER


@pytest.fixture(scope="module")
def client(built_runs, tmp_path_factory):
    from api.main import create_app
    from eval.markers import write_lead_time
    root = tmp_path_factory.mktemp("api")
    data = built_runs["injected"].parent
    (root / "eval").mkdir()
    write_lead_time(built_runs["injected"], data / "ground_truth.json", root / "eval" / "lead_time.json")
    (root / "eval" / "results.json").write_text(json.dumps({"detector": {"gates": {}}, "llm": {}, "cost": {}}))
    (root / "briefs").mkdir()
    for name in ("week_40.json", "week_40.md"):
        shutil.copy(os.path.join("briefs", name), root / "briefs" / name)
    app = create_app(data_dir=data, briefs_dirs=[root / "briefs"], eval_dir=root / "eval",
                     decisions_db=root / "decisions.duckdb")
    return TestClient(app)


def test_replay_forced(client):
    assert os.environ["REPLAY"] == "1"


def test_meta(client):
    meta = client.get("/api/meta").json()
    assert meta["banner"] == SYNTHETIC_BANNER and meta["runs"] == ["injected", "control"]
    assert meta["max_week"] == 77 and "sample-scale" in meta["sample_scale_label"]


def test_radar_injected_week40(client):
    r = client.get("/api/radar", params={"run": "injected", "week": 40}).json()
    assert r["banner"] == SYNTHETIC_BANNER
    assert [a["scope"] for a in r["actions"]][:2] == ["B2", "M05"]
    assert r["kpis"]["active_alerts"] == 2 and r["kpis"]["cm_pct"] is not None
    b2 = r["actions"][0]["impact"]
    assert b2["basis"] == "scenario_estimate" and b2["usd_low"] < b2["usd_mid"] < b2["usd_high"]


def test_radar_control_q3_has_no_actions(client):
    r = client.get("/api/radar", params={"run": "control", "week": 33}).json()
    assert r["actions"] == [] and r["kpis"]["active_alerts"] == 0


def test_heatmap(client):
    h = client.get("/api/heatmap", params={"run": "injected", "week": 45, "metric": "contract_rate"}).json()
    assert len(h["cells"]) == 36 and {"segment", "market", "band", "product", "score"} <= set(h["cells"][0])


def test_drilldown_with_markers(client):
    d = client.get("/api/drilldown", params={"run": "injected", "metric": "contract_rate", "dimension": "band",
                                             "scope": "B2"}).json()
    assert len(d["weeks"]) == len(d["value"]) == len(d["peer"]) == len(d["gap"]) == len(d["score"])
    assert any(a["kind"] == "adverse_selection" for a in d["alerts"])
    assert d["truth"]["first_alert_week"] == 38 and d["truth"]["cm_first_visible_week"] == 45
    control = client.get("/api/drilldown", params={"run": "control", "metric": "contract_rate", "dimension": "band",
                                                   "scope": "B2"}).json()
    assert control["truth"] is None


def test_cohort(client):
    c = client.get("/api/cohort", params={"run": "injected", "week": 77, "level": "band", "scope": "B2",
                                          "start": 30, "end": 33}).json()
    assert [p["sold_share"] for p in c["points"]] == [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8]


def test_briefs(client):
    listing = client.get("/api/briefs").json()
    assert {"week": 40, "status": "valid"} in [{k: b[k] for k in ("week", "status")} for b in listing["briefs"]]
    brief = client.get("/api/brief", params={"week": 40}).json()
    assert brief["citations"] and "sql" in brief["citations"][0]
    assert client.get("/api/brief", params={"week": 41}).status_code == 404


def test_decisions_post_list_score(client):
    payload = {"alert_id": "A2527e410", "decision": "acted", "reason": "widened spread", "decided_week": 40,
               "scope": "B2", "kind": "adverse_selection"}
    assert client.post("/api/decisions", json=payload).status_code == 200
    assert client.post("/api/decisions", json={**payload, "decision": "maybe"}).status_code == 422
    listing = client.get("/api/decisions", params={"decision": "acted"}).json()
    assert listing["decisions"][0]["alert_id"] == "A2527e410"
    assert listing["score"]["decisions_influenced"] >= 1


@pytest.mark.parametrize("path,params", [
    ("/api/radar", {"run": "both", "week": 40}),
    ("/api/radar", {"run": "injected", "week": 999}),
    ("/api/heatmap", {"run": "injected", "week": 40, "metric": "drop"}),
    ("/api/drilldown", {"run": "injected", "metric": "contract_rate", "dimension": "band", "scope": "B9"}),
])
def test_bad_params_are_422(client, path, params):
    assert client.get(path, params=params).status_code == 422


def test_eval_results(client):
    assert "detector" in client.get("/api/eval").json()


def test_export_writes_static_files(client, tmp_path):
    from api.export import export
    manifest = export(client.app.state.services, tmp_path, weeks=[40], runs=["injected"])
    assert (tmp_path / "manifest.json").exists() and manifest["files"]
    assert (tmp_path / "radar" / "injected" / "40.json").exists()
