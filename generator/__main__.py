"""python -m generator: write injected + control runs (same seed) to Parquet and one DuckDB file per run.

Outputs: data/radar_injected.duckdb, data/radar_control.duckdb, eval/ground_truth.json.
The runs share random draws, so they live in separate files and only /eval reads both.
"""
import argparse
import json
import logging
from collections.abc import Sequence
from pathlib import Path

from common.banner import SYNTHETIC_BANNER
from generator.config import BANDS, MARKETS, N_WEEKS, START_DATE
from generator.ground_truth import compute_ground_truth
from generator.io import load_duckdb, write_parquet
from generator.scenarios import default_scenarios
from generator.simulate import simulate

log = logging.getLogger("generator")


def _week(value: str) -> int:
    week = int(value)
    if not 0 <= week < N_WEEKS:
        raise argparse.ArgumentTypeError(f"week must be in [0, {N_WEEKS - 1}]")
    return week


def _injections(value: str) -> set[str]:
    names = {v.strip().upper() for v in value.split(",") if v.strip()}
    if not names or not names <= {"A", "B", "C"}:
        raise argparse.ArgumentTypeError("--inject takes a comma list of A, B, C")
    return names


def _parse(argv: Sequence[str] | None) -> argparse.Namespace:
    p = argparse.ArgumentParser(prog="generator", description=SYNTHETIC_BANNER)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--out-dir", type=Path, default=Path("data"))
    p.add_argument("--truth-path", type=Path, default=Path("eval/ground_truth.json"))
    p.add_argument("--inject", type=_injections, default={"A", "B", "C"})
    p.add_argument("--a-market", choices=MARKETS, default="M02")
    p.add_argument("--a-start-week", type=_week, default=30)
    p.add_argument("--b-band", choices=list(BANDS), default="B2")
    p.add_argument("--b-start-week", type=_week, default=30)
    p.add_argument("--c-market", choices=MARKETS, default="M05")
    p.add_argument("--c-start-week", type=_week, default=30)
    return p.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> None:
    args = _parse(argv)
    log.info(SYNTHETIC_BANNER)
    scenarios = tuple(
        s for s in default_scenarios(args.a_market, args.a_start_week, args.b_band, args.b_start_week,
                                     args.c_market, args.c_start_week)
        if s.name in args.inject
    )
    for run_id, run_scenarios in (("injected", scenarios), ("control", ())):
        run_dir = args.out_dir / "parquet" / run_id
        write_parquet(simulate(args.seed, run_scenarios), run_dir)
        load_duckdb(args.out_dir / f"radar_{run_id}.duckdb", run_dir)
    truth = {
        "banner": SYNTHETIC_BANNER,
        "seed": args.seed,
        "start_date": START_DATE.isoformat(),
        "n_weeks": N_WEEKS,
        "scenarios": compute_ground_truth(args.seed, scenarios),
    }
    args.truth_path.parent.mkdir(parents=True, exist_ok=True)
    args.truth_path.write_text(json.dumps(truth, indent=2) + "\n")
    for t in truth["scenarios"]:
        log.info("%s %s=%s start week %s, visible in sold-cohort CM at week %s (lag %s weeks; solo run: week %s)",
                 t["scenario"], t["scope_type"], t["scope"], t["start_week"],
                 t["cm_first_visible_week"], t["cm_lag_weeks"], t["cm_first_visible_week_solo"])


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    main()
