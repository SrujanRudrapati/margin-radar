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
    yield TestClient(app)
    app.state.services.close()


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


def test_startup_warms_alert_episodes_so_first_decision_view_is_fast(built_runs, tmp_path):
    # replaying the detector over every week takes ~20 s; the server does it once in the background at startup
    import time
    from api.main import create_app
    app = create_app(data_dir=built_runs["injected"].parent, briefs_dirs=[tmp_path], eval_dir=tmp_path,
                     decisions_db=tmp_path / "decisions.duckdb")
    with TestClient(app):
        services = app.state.services
        assert services.warmed.wait(timeout=300)
        assert set(services._episodes) == {"injected", "control"}
        start = time.monotonic()
        services.decisions_view()
        assert time.monotonic() - start < 5


@pytest.mark.slow
def test_warm_up_does_not_hold_the_request_lock_while_replaying(built_runs, tmp_path):
    # requests share one lock; warm-up must do its ~20 s replay on its own connection, taking the lock only to store
    import threading
    import time
    from api.main import create_app
    services = create_app(data_dir=built_runs["injected"].parent, briefs_dirs=[tmp_path], eval_dir=tmp_path,
                          decisions_db=tmp_path / "decisions.duckdb").state.services
    with services._lock:  # a long-running request
        worker = threading.Thread(target=services.warm, daemon=True)
        worker.start()
        time.sleep(60)  # long enough for the replay of both runs to finish if it is not waiting on the lock
        assert not services.warmed.is_set()
    start = time.monotonic()
    assert services.warmed.wait(timeout=300)
    assert time.monotonic() - start < 5, "the replay ran only after the lock was released"
    services.close()


def test_drilldown_shows_only_alerts_and_lead_time_for_its_own_metric(client):
    # M05's alert is renovation-cost drift; its contract-rate chart must not borrow that alert or its lead time
    other = client.get("/api/drilldown", params={"run": "injected", "metric": "contract_rate", "dimension": "market",
                                                  "scope": "M05"}).json()
    assert other["alerts"] == [] and other["truth"] is None
    own = client.get("/api/drilldown", params={"run": "injected", "metric": "reno_overrun_pct", "dimension": "market",
                                                "scope": "M05"}).json()
    assert own["alerts"] and all(e["kind"] == "reno_cost_drift" for e in own["alerts"])
    assert own["truth"]["kind"] == "reno_cost_drift"


def test_requests_during_warm_up_wait_for_it_instead_of_replaying_under_the_lock(built_runs, tmp_path):
    # a request that needs alert episodes while warm-up runs must not replay the detector itself while holding the
    # lock every endpoint shares (that froze the whole API for ~40 s right after `make demo` started)
    import threading
    from api.main import create_app
    services = create_app(data_dir=built_runs["injected"].parent, briefs_dirs=[tmp_path], eval_dir=tmp_path,
                          decisions_db=tmp_path / "decisions.duckdb").state.services
    services.warming.set()  # as if the startup thread were running
    calls = []
    import api.services as mod
    real = mod._detect_episodes
    mod._detect_episodes = lambda store: calls.append(1) or real(store)
    try:
        worker = threading.Thread(target=services.decisions_view, daemon=True)
        worker.start()
        worker.join(timeout=2)
        assert worker.is_alive() and calls == [], "request replayed instead of waiting for warm-up"
        services.warm()  # warm-up finishes
        worker.join(timeout=60)
        assert not worker.is_alive() and len(calls) == 2  # only warm-up's two runs were replayed
    finally:
        mod._detect_episodes = real
        services.close()


def test_close_releases_the_run_databases(built_runs, tmp_path):
    # open read-only connections block any writer (dbt, the generator) in another process until they are closed
    import subprocess
    import sys
    from api.main import create_app
    data = tmp_path / "data"  # private copies: other tests in this module hold the shared files open
    data.mkdir()
    for run in ("injected", "control"):
        shutil.copy(built_runs[run], data / f"radar_{run}.duckdb")
    services = create_app(data_dir=data, briefs_dirs=[tmp_path], eval_dir=tmp_path,
                          decisions_db=tmp_path / "decisions.duckdb").state.services
    services.meta()
    services.radar("control", 40)
    services.close()
    for run in ("injected", "control"):
        db = data / f"radar_{run}.duckdb"
        subprocess.run([sys.executable, "-c", f"import duckdb; duckdb.connect({str(db)!r}).close()"], check=True)
