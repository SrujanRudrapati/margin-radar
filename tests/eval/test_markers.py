import json

from eval.markers import write_lead_time


def test_lead_time_markers_for_seed42(built_runs, tmp_path):
    out = tmp_path / "lead_time.json"
    truth = built_runs["injected"].parent / "ground_truth.json"
    payload = write_lead_time(built_runs["injected"], truth, out)
    data = json.loads(out.read_text())
    assert data == payload and data["banner"].startswith("Synthetic data")
    rows = {r["scenario"]: r for r in data["scenarios"]}
    assert set(rows) == {"A", "B", "C"}
    b = rows["B"]
    assert (b["kind"], b["scope"], b["start_week"], b["cm_first_visible_week"]) == ("adverse_selection", "B2", 30, 45)
    assert b["first_alert_week"] == 38 and b["lead_weeks"] == 7
