"""Deterministic multi-seed evaluation of the detector (docs/SPEC.md Phase 5).

For each seed: generate both runs into eval/runs/seed_N, build both dbt targets there, run detect() for every
week of both runs, and score against that seed's ground truth. Results are cached per seed, keyed by a hash of the
generator, dbt project and detector sources, so reruns are fast. /eval is the only package allowed to open both
databases and read ground truth. Synthetic data — not Opendoor data.
"""
import hashlib
import json
import logging
import os
import subprocess
import sys
from pathlib import Path

import numpy as np

from detector.governed import GovernedStore
from detector.rules import detect
from eval.kpis import false_alert_stats, scenario_kpis, true_pairs
from generator.config import BANDS, MARKETS

ROOT = Path(__file__).resolve().parents[1]
DBT_BIN = Path(sys.executable).parent / "dbt"
TUNING_SEEDS = tuple(range(1, 6))
HOLDOUT_SEEDS = tuple(range(6, 11))
# True holdout (DECISIONS D28): never used for tuning; scopes and onset weeks are drawn per seed.
TRUE_HOLDOUT_SEEDS = tuple(range(11, 21))
# Onsets after the first week the drift baseline can score (burn-in 8 + 12 history + 8 eval gap) and early enough
# for sold-home margin to show the problem before week 78.
ONSET_WEEK_RANGE = (28, 46)
MIN_RECALL = 8  # of 10 seeds, per scenario
MAX_WRONG = 2   # wrong-scope alert episodes across all injected runs
log = logging.getLogger("eval")


def source_hash() -> str:
    digest = hashlib.sha256()
    for folder in ("generator", "dbt_project/models", "dbt_project/macros", "detector"):
        for path in sorted((ROOT / folder).rglob("*")):
            if path.is_file() and path.suffix in {".py", ".sql", ".yml", ".yaml"}:
                digest.update(str(path.relative_to(ROOT)).encode())
                digest.update(path.read_bytes())
    return digest.hexdigest()[:16]


def scenario_args(seed: int) -> dict:
    """Seeds 1–10 keep the fixed design (M02, B2, M05, onset week 30). True-holdout seeds draw their own."""
    if seed not in TRUE_HOLDOUT_SEEDS:
        return {}
    rng = np.random.default_rng([seed, 20261023])
    a_market, c_market = (str(m) for m in rng.choice(MARKETS, size=2, replace=False))
    lo, hi = ONSET_WEEK_RANGE
    a_start, b_start, c_start = (int(w) for w in rng.integers(lo, hi + 1, size=3))
    return {"a_market": a_market, "a_start_week": a_start, "b_band": str(rng.choice(list(BANDS))),
            "b_start_week": b_start, "c_market": c_market, "c_start_week": c_start}


def generator_cli_args(args: dict) -> list[str]:
    return [item for name, value in args.items() for item in (f"--{name.replace('_', '-')}", str(value))]


def run_seed(seed: int, root: Path) -> dict:
    work = root / f"seed_{seed}"
    cache = work / "detections.json"
    key = source_hash()
    args = scenario_args(seed)
    if cache.exists():
        cached = json.loads(cache.read_text())
        if cached.get("source_hash") == key and cached.get("scenario_args", {}) == args:
            return cached
    work.mkdir(parents=True, exist_ok=True)
    truth_path = work / "ground_truth.json"
    _run([sys.executable, "-m", "generator", "--seed", str(seed), "--out-dir", str(work), "--truth-path", str(truth_path),
          *generator_cli_args(args)])
    runs = {}
    for run_id in ("injected", "control"):
        db = work / f"radar_{run_id}.duckdb"
        _dbt_build(db, run_id, work)
        runs[run_id] = _detect_all(db, run_id)
    result = {"seed": seed, "source_hash": key, "scenario_args": args, "truth": json.loads(truth_path.read_text())["scenarios"], "runs": runs}
    cache.write_text(json.dumps(result))
    return result


def _run(cmd: list[str], env: dict | None = None) -> None:
    done = subprocess.run(cmd, cwd=ROOT, env=env, capture_output=True, text=True)
    if done.returncode != 0:
        raise RuntimeError(f"command failed: {' '.join(cmd)}\n{done.stdout[-2000:]}\n{done.stderr[-2000:]}")


def _dbt_build(db: Path, target: str, work: Path) -> None:
    env = {**os.environ, "MR_DB_PATH": str(db), "MR_TARGET": target}
    _run([str(DBT_BIN), "build", "--project-dir", "dbt_project", "--profiles-dir", "dbt_project", "--target", target,
          "--target-path", str(work / f"target_{target}"), "--log-path", str(work / f"logs_{target}")], env)


def _detect_all(db: Path, run_id: str) -> dict:
    weekly, evaluable = {}, []
    with GovernedStore(str(db), run_id) as store:
        for week in range(0, store.max_week + 1):
            result = detect(store, week)
            if any(a.scope == "all" for a in result.abstentions):
                continue
            evaluable.append(week)
            weekly[str(week)] = [[a.alert_id, a.kind, a.scope] for a in result.alerts]
    return {"evaluable": evaluable, "alerts": weekly}


def summarize(seed_results: list[dict], seeds: list[int]) -> dict:
    rows = [r for r in seed_results if r["seed"] in seeds]
    scenarios: dict[str, list[dict]] = {}
    control_weeks = control_alert_weeks = wrong_eps = wrong_weeks = injected_weeks = 0
    true_eps = all_eps = 0
    per_seed_control = []
    for r in rows:
        pairs = true_pairs(r["truth"])
        inj = {int(w): [tuple(a) for a in v] for w, v in r["runs"]["injected"]["alerts"].items()}
        for s in r["truth"]:
            kind, scope = pairs[s["scenario"]]
            weeks = [w for w, alerts in inj.items() if any(a[1] == kind and a[2] == scope for a in alerts)]
            scenarios.setdefault(s["scenario"], []).append({"seed": r["seed"], **scenario_kpis(s, weeks)})
        wrong = false_alert_stats(inj, set(pairs.values()), r["runs"]["injected"]["evaluable"])
        wrong_eps += wrong["wrong_episodes"]
        wrong_weeks += wrong["wrong_alert_weeks"]
        injected_weeks += wrong["evaluable_weeks"]
        episodes = {a[0]: (a[1], a[2]) for alerts in inj.values() for a in alerts}
        all_eps += len(episodes)
        true_eps += sum(1 for pair in episodes.values() if pair in set(pairs.values()))
        ctl = {int(w): [tuple(a) for a in v] for w, v in r["runs"]["control"]["alerts"].items()}
        c = false_alert_stats(ctl, set(), r["runs"]["control"]["evaluable"])
        per_seed_control.append({"seed": r["seed"], "alert_weeks": c["wrong_alert_weeks"], "episodes": c["wrong_episodes"],
                                 "per_week": round(c["wrong_alert_weeks_per_week"], 3)})
        control_weeks += c["evaluable_weeks"]
        control_alert_weeks += c["wrong_alert_weeks"]
    per_scenario = {name: _scenario_summary(items) for name, items in sorted(scenarios.items())}
    n_scen = sum(len(v) for v in scenarios.values())
    detected = sum(1 for v in scenarios.values() for k in v if k["before_cm"])
    return {
        "seeds": list(seeds),
        "control_evaluable_weeks": control_weeks,
        "control_alert_weeks": control_alert_weeks,
        "control_false_alerts_per_week": control_alert_weeks / max(1, control_weeks),
        "wrong_episodes": wrong_eps,
        "wrong_alert_weeks_per_week": wrong_weeks / max(1, injected_weeks),
        "precision": true_eps / all_eps if all_eps else None,
        "recall_before_cm": detected / n_scen if n_scen else None,
        "scenarios": per_scenario,
        "control_per_seed": per_seed_control,
    }


def _scenario_summary(items: list[dict]) -> dict:
    leads = sorted(k["lead_weeks"] for k in items if k["lead_weeks"] is not None and k["before_cm"])
    delays = sorted(k["delay_weeks"] for k in items if k["delay_weeks"] is not None and k["before_cm"])
    med = lambda xs: (xs[len(xs) // 2] if len(xs) % 2 else (xs[len(xs) // 2 - 1] + xs[len(xs) // 2]) / 2) if xs else None  # noqa: E731
    return {"seeds": len(items), "detected_before_cm": sum(k["before_cm"] for k in items),
            "median_lead_weeks": med(leads), "min_lead_weeks": leads[0] if leads else None,
            "max_lead_weeks": leads[-1] if leads else None, "median_delay_weeks": med(delays), "per_seed": items}


def split_gates(s: dict, n_seeds: int, prefix: str) -> dict:
    min_recall = MIN_RECALL * n_seeds / 10
    max_wrong = MAX_WRONG * n_seeds / 10
    return {
        f"{prefix}_control_zero_alerts": {"pass": s["control_alert_weeks"] == 0, "value": s["control_alert_weeks"],
                                          "rule": f"0 control alert-weeks ({prefix} seeds)"},
        f"{prefix}_recall_before_cm": {"pass": all(v["detected_before_cm"] >= min_recall for v in s["scenarios"].values()),
                                       "value": {k: f"{v['detected_before_cm']}/{v['seeds']}" for k, v in s["scenarios"].items()},
                                       "rule": f">= {MIN_RECALL}/10 of {prefix} seeds per scenario alert on the true scope before margin shows it"},
        f"{prefix}_wrong_alerts": {"pass": s["wrong_episodes"] <= max_wrong, "value": s["wrong_episodes"],
                                   "rule": f"<= {max_wrong:g} wrong-scope alert episodes ({prefix} injected runs)"},
    }


def run_detector_eval(seeds=range(1, 11), root: Path = ROOT / "eval" / "runs", tuning_seeds=TUNING_SEEDS,
                      holdout_seeds=HOLDOUT_SEEDS) -> dict:
    root = Path(root)
    results = []
    for seed in seeds:
        log.info("seed %s ...", seed)
        results.append(run_seed(seed, root))
    by_split = {"tuning": summarize(results, list(tuning_seeds)), "holdout": summarize(results, list(holdout_seeds)),
                "all": summarize(results, list(seeds))}
    gates = {**split_gates(by_split["all"], len(list(seeds)), "all"), **split_gates(by_split["holdout"], len(list(holdout_seeds)), "holdout")}
    per_seed = [{"seed": r["seed"], "truth": r["truth"]} for r in results]
    return {"per_seed": per_seed, "by_split": by_split, "gates": gates}
