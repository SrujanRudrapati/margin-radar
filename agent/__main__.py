"""python -m agent brief --db PATH --as-of-week N [--purpose dev|final] [--out briefs]

Exit codes: 0 written, 2 failed the grounding check (fail closed), 3 API budget or replay problem.
Synthetic data — not Opendoor data.
"""
import argparse
import json
import logging
import sys
from collections.abc import Sequence
from pathlib import Path

from agent.brief import BriefFailed, make_brief
from agent.llm import BudgetExceeded, MissingKey, ReplayMiss
from common.banner import SYNTHETIC_BANNER

log = logging.getLogger("agent")


def main(argv: Sequence[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="agent", description=SYNTHETIC_BANNER)
    sub = p.add_subparsers(dest="command", required=True)
    brief = sub.add_parser("brief", help="write the weekly brief for one week")
    brief.add_argument("--db", type=Path, required=True, help="the injected run's database")
    brief.add_argument("--as-of-week", type=int, required=True)
    brief.add_argument("--purpose", choices=["dev", "final"], default="dev")
    brief.add_argument("--out", type=Path, default=Path("briefs"))
    dec = sub.add_parser("decisions", help="decision log: seed examples, list, or score against realized margin")
    dec.add_argument("action", choices=["seed", "list", "score"])
    dec.add_argument("--db", type=Path, required=True, help="the injected run's database")
    dec.add_argument("--log", type=Path, required=True, help="decision log database file")
    args = p.parse_args(argv)
    if args.command == "decisions":
        return _decisions(args)
    try:
        path = make_brief(args.db, args.as_of_week, args.purpose, args.out)
    except BriefFailed as exc:
        log.error("%s", exc)
        return 2
    except (BudgetExceeded, ReplayMiss, MissingKey) as exc:
        log.error("%s", exc)
        return 3
    except Exception as exc:  # API errors: report cleanly, never with the key
        if type(exc).__module__.startswith("anthropic"):
            log.error("Claude API error: %s", exc)
            return 3
        raise
    log.info("wrote %s", path)
    return 0


def _decisions(args) -> int:
    from agent.decisions import DecisionLog, score_decisions, seed_examples
    from detector.governed import GovernedStore
    log_db = DecisionLog(args.log)
    with GovernedStore(str(args.db), "injected") as store:
        if args.action == "seed":
            out = seed_examples(log_db, store)
        elif args.action == "list":
            out = log_db.list()
        else:
            out = score_decisions(log_db, store)
    print(json.dumps(out, default=str))
    return 0


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    sys.exit(main())
