"""python -m detector --db PATH --run-id LABEL (--as-of-week N | --all-weeks) [--out data/out]

Writes {out}/{run_id}/week_{N:02d}/alerts.json and queries.jsonl. The caller passes one database path.
Synthetic data — not Opendoor data.
"""
import argparse
import dataclasses
import json
import logging
import math
from collections.abc import Sequence
from pathlib import Path

from common.banner import SYNTHETIC_BANNER
from common.business import SAMPLE_SCALE_LABEL
from detector.governed import GovernedStore
from detector.impact import rank_actions
from detector.rules import detect

log = logging.getLogger("detector")


def _clean(value):
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if isinstance(value, dict):
        return {k: _clean(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_clean(v) for v in value]
    return value


def run_week(db: Path, run_id: str, week: int, out: Path) -> dict:
    week_dir = out / run_id / f"week_{week:02d}"
    week_dir.mkdir(parents=True, exist_ok=True)
    log_path = week_dir / "queries.jsonl"
    log_path.unlink(missing_ok=True)
    with GovernedStore(str(db), run_id, log_path=str(log_path)) as store:
        result = detect(store, week)
        ranked = rank_actions(result, store)
    payload = _clean({
        "banner": SYNTHETIC_BANNER,
        "sample_scale_label": SAMPLE_SCALE_LABEL,
        "run_id": run_id,
        "as_of_week": week,
        "alerts": [dataclasses.asdict(a) for a in result.alerts],
        "watch": [dataclasses.asdict(w) for w in result.watch],
        "abstentions": [dataclasses.asdict(a) for a in result.abstentions],
        "ranked_actions": [dataclasses.asdict(r) for r in ranked],
    })
    (week_dir / "alerts.json").write_text(json.dumps(payload, indent=2) + "\n")
    return payload


def main(argv: Sequence[str] | None = None) -> None:
    p = argparse.ArgumentParser(prog="detector", description=SYNTHETIC_BANNER)
    p.add_argument("--db", type=Path, required=True)
    p.add_argument("--run-id", required=True)
    group = p.add_mutually_exclusive_group(required=True)
    group.add_argument("--as-of-week", type=int)
    group.add_argument("--all-weeks", action="store_true")
    p.add_argument("--out", type=Path, default=Path("data/out"))
    args = p.parse_args(argv)
    if not args.db.exists():
        p.error(f"database not found: {args.db}")
    if args.all_weeks:
        with GovernedStore(str(args.db), args.run_id) as store:
            weeks = range(0, store.max_week + 1)
    else:
        weeks = [args.as_of_week]
    for week in weeks:
        payload = run_week(args.db, args.run_id, week, args.out)
        log.info("%s week %02d: %d alerts, %d watch", args.run_id, week, len(payload["alerts"]), len(payload["watch"]))


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    main()
