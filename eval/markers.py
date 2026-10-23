"""Lead-time markers for the dashboard: when each injected problem started, when the detector first alerted on its
true scope, and when sold-cohort margin first showed it (seed 42). /eval is the only reader of ground truth; the
dashboard reads this artifact instead. Synthetic data — not Opendoor data.

python -m eval.markers  →  eval/lead_time.json
"""
import json
from pathlib import Path

from common.banner import SYNTHETIC_BANNER
from detector.governed import GovernedStore
from detector.rules import detect
from eval.kpis import scenario_kpis, true_pairs

ROOT = Path(__file__).resolve().parents[1]


def write_lead_time(db: str | Path, truth_path: str | Path, out: str | Path) -> dict:
    scenarios = json.loads(Path(truth_path).read_text())["scenarios"]
    pairs = true_pairs(scenarios)
    weeks: dict[tuple[str, str], list[int]] = {}
    with GovernedStore(str(db), "injected") as store:
        for week in range(0, store.max_week + 1):
            for alert in detect(store, week).alerts:
                weeks.setdefault((alert.kind, alert.scope), []).append(week)
    rows = []
    for s in scenarios:
        kind, scope = pairs[s["scenario"]]
        k = scenario_kpis(s, weeks.get((kind, scope), []))
        rows.append({"scenario": s["scenario"], "kind": kind, "scope": scope, "scope_type": s["scope_type"], **k})
    payload = {"banner": SYNTHETIC_BANNER, "run_id": "injected", "scenarios": rows}
    Path(out).write_text(json.dumps(payload, indent=2) + "\n")
    return payload


if __name__ == "__main__":
    write_lead_time(ROOT / "data" / "radar_injected.duckdb", ROOT / "eval" / "ground_truth.json", ROOT / "eval" / "lead_time.json")
