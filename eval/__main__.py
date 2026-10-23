"""python -m eval [--live] [--yes] [--skip-llm]  →  eval/results.json + eval/results.md

Default is replay-only (REPLAY=1): the deterministic detector sweep (seeds 1–10, tuned on 1–5, holdout 6–10) plus
the seed-42 LLM evaluations from recorded responses. --live records missing LLM responses with CLAUDE_MODEL_FINAL,
printing the planned call count first (more than 20 needs --yes or a "y"). Synthetic data — not Opendoor data.
"""
import argparse
import json
import logging
import os
import sys
from collections.abc import Sequence
from pathlib import Path

from agent.brief import BriefFailed, make_brief
from agent.config import model_for
from agent.llm import LLM
from common.banner import SYNTHETIC_BANNER
from eval.brief_accuracy import brief_accuracy
from eval.detector_eval import ROOT, run_detector_eval
from eval.qa import QUESTIONS, UNANSWERABLE, run_qa
from eval.report import confirm_live, token_totals, write_report

SEED42_DB = ROOT / "data" / "radar_injected.duckdb"
BRIEF_WEEKS = (40, 45, 50, 60)  # seed-42 weeks with active alerts (B2 weeks 38-52, M05 weeks 40-77)
EVAL_DIR = ROOT / "eval"
TOKEN_LOG = ROOT / "data" / "token_log.jsonl"
log = logging.getLogger("eval")


def planned_calls() -> int:
    briefs = len(BRIEF_WEEKS) * 8  # up to 6 tool turns + final + one revision each
    qa = 2 * (len(QUESTIONS) + len(UNANSWERABLE)) * 3
    return briefs + qa


def llm_eval() -> dict:
    model = model_for("final")
    briefs = []
    for week in BRIEF_WEEKS:
        llm = LLM(model, "final", run_tag=f"eval-brief-week_{week:02d}")
        try:
            path = make_brief(SEED42_DB, week, "final", out_dir=EVAL_DIR / "briefs", llm=llm)
            payload = json.loads(path.with_suffix(".json").read_text())
        except BriefFailed as exc:
            payload = json.loads((EVAL_DIR / "briefs" / f"week_{week:02d}.invalid.json").read_text())
            payload["failure"] = str(exc)[:500]
        acc = brief_accuracy(payload["body"], payload.get("actions", []))
        g = payload["grounding"]
        briefs.append({"week": week, "status": payload["status"], "numbers_checked": g["numbers_checked"],
                       "final_errors": len(g["errors"]), "first_draft": g.get("first_draft"),
                       "section_accuracy": acc.section_accuracy, "direction_errors": acc.direction_errors})
    qa = {mode: run_qa(LLM(model, "final", run_tag=f"eval-qa-{mode}"), SEED42_DB, mode) for mode in ("semantic", "raw_sql")}
    checked = sum(b["numbers_checked"] for b in briefs if b["status"] == "valid")
    grounded = sum(b["numbers_checked"] for b in briefs if b["status"] == "valid" and b["final_errors"] == 0)
    total_checked = sum(b["numbers_checked"] for b in briefs)
    first_errors = sum((b["first_draft"] or {}).get("errors", 0) for b in briefs)
    sections = [b["section_accuracy"] for b in briefs]
    summary = {
        "briefs": f"{sum(b['status'] == 'valid' for b in briefs)}/{len(briefs)} valid (published) at weeks {list(BRIEF_WEEKS)}",
        "number_grounding_pct": round(100 * grounded / total_checked, 1) if total_checked else None,
        "first_draft_errors_total": first_errors,
        "brief_section_accuracy_mean": round(sum(sections) / len(sections), 3) if sections else None,
        "brief_direction_errors": sum(b["direction_errors"] for b in briefs),
        "semantic_layer_accuracy": qa["semantic"]["accuracy"], "raw_sql_accuracy": qa["raw_sql"]["accuracy"],
        "abstention_rate_semantic": qa["semantic"]["abstention_rate"], "abstention_rate_raw_sql": qa["raw_sql"]["abstention_rate"],
        "false_abstentions": {m: qa[m]["false_abstentions"] for m in qa},
    }
    gates = {
        "grounding_100": {"pass": total_checked > 0 and grounded == total_checked, "value": summary["number_grounding_pct"],
                          "rule": "100% of numbers in published briefs match their cited facts"},
        "brief_accuracy": {"pass": all(s >= 0.9 for s in sections) and summary["brief_direction_errors"] == 0,
                           "value": f"{summary['brief_section_accuracy_mean']} mean, {summary['brief_direction_errors']} direction errors",
                           "rule": ">= 90% of sections accurate in every brief AND zero direction errors"},
        "abstention_100": {"pass": summary["abstention_rate_semantic"] == 1.0,
                           "value": summary["abstention_rate_semantic"],
                           "rule": "abstains on all 5 unanswerable questions (semantic-layer mode)"},
    }
    return {"briefs": briefs, "qa": qa, "summary": summary, "gates": gates, "checked_numbers": checked}


def main(argv: Sequence[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="eval", description=SYNTHETIC_BANNER)
    p.add_argument("--live", action="store_true", help="record missing LLM responses (costs tokens)")
    p.add_argument("--yes", action="store_true", help="skip the >20-call confirmation")
    p.add_argument("--skip-llm", action="store_true")
    args = p.parse_args(argv)
    if args.live:
        planned = planned_calls()
        log.info("Planned live calls (upper bound): %d (model %s)", planned, model_for("final"))
        if not confirm_live(planned, args.yes):
            log.info("aborted")
            return 0
        os.environ["REPLAY"] = "0"
        os.environ.setdefault("MAX_API_CALLS", str(planned))
    else:
        os.environ["REPLAY"] = "1"
    results = {"detector": run_detector_eval()}
    if not args.skip_llm:
        results["llm"] = llm_eval()
    results["cost"] = {"eval": token_totals(TOKEN_LOG, prefix="eval"), "night (all calls)": token_totals(TOKEN_LOG)}
    write_report(results, EVAL_DIR / "results.md", EVAL_DIR / "results.json")
    log.info("wrote eval/results.md and eval/results.json")
    return 0


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    sys.exit(main())
