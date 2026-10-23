"""python -m eval [--live] [--yes] [--skip-llm]  →  eval/results.json + eval/results.md

Default is replay-only (REPLAY=1): the deterministic detector sweep (seeds 1–20: tuned on 1–5, 6–10 seen, gates on
the true holdout 11–20 with drawn scopes and onsets) plus
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
from agent.llm import LLM, Budget
from agent.loop import MAX_TURNS_DEFAULT, REVISE_TURNS
from common.banner import SYNTHETIC_BANNER
from eval.brief_accuracy import brief_accuracy
from eval.detector_eval import ROOT, run_detector_eval
from eval.kpis import true_pairs
from eval.qa import MAX_TURNS as QA_TURNS
from eval.qa import QUESTIONS, UNANSWERABLE, run_qa
from eval.report import confirm_live, token_totals, write_report

SEED42_DB = ROOT / "data" / "radar_injected.duckdb"
BRIEF_WEEKS = (40, 45, 50, 60)  # seed-42 weeks with active alerts (B2 weeks 38-52, M05 weeks 43-77)
EVAL_DIR = ROOT / "eval"
TOKEN_LOG = ROOT / "data" / "token_log.jsonl"
RECORDING_COST = EVAL_DIR / "recording_cost.json"  # committed: what recording the eval's LLM responses cost
TRUTH_42 = EVAL_DIR / "ground_truth.json"
log = logging.getLogger("eval")


def planned_calls() -> int:
    """True upper bound: every brief may use all its turns plus a full revision; every QA conversation all turns."""
    briefs = len(BRIEF_WEEKS) * (MAX_TURNS_DEFAULT + REVISE_TURNS)
    qa = 2 * (len(QUESTIONS) + len(UNANSWERABLE)) * QA_TURNS
    return briefs + qa


def llm_eval(budget: Budget) -> dict:
    model = model_for("final")
    truth = {pair[1] for pair in true_pairs(json.loads(TRUTH_42.read_text())["scenarios"]).values()}
    briefs = []
    for week in BRIEF_WEEKS:
        llm = LLM(model, "final", run_tag=f"eval-brief-week_{week:02d}", budget=budget)
        try:
            path = make_brief(SEED42_DB, week, "final", out_dir=EVAL_DIR / "briefs", llm=llm)
            payload = json.loads(path.with_suffix(".json").read_text())
        except BriefFailed as exc:
            payload = json.loads((EVAL_DIR / "briefs" / f"week_{week:02d}.invalid.json").read_text())
            payload["failure"] = str(exc)[:500]
        valid = payload["status"] == "valid"
        acc = brief_accuracy(payload["body"], payload.get("actions", []))
        g, actions = payload["grounding"], payload.get("actions", [])
        sections = [part for part in payload["body"].split("\n### ")[1:]]
        briefs.append({"week": week, "status": payload["status"], "numbers_checked": g["numbers_checked"],
                       "final_errors": len(g["errors"]), "first_draft": g.get("first_draft"),
                       "section_accuracy": acc.section_accuracy if valid else 0.0, "direction_errors": acc.direction_errors,
                       "top_scope_true": bool(actions) and actions[0]["scope"] in truth,
                       "sample_scale_labeled": valid and bool(sections) and all("sample-scale" in x.lower() for x in sections)})
    qa = {mode: run_qa(LLM(model, "final", run_tag=f"eval-qa-{mode}", budget=budget), SEED42_DB, mode)
          for mode in ("semantic", "raw_sql")}
    total = sum(b["numbers_checked"] for b in briefs)
    grounded = sum(b["numbers_checked"] for b in briefs if b["status"] == "valid" and b["final_errors"] == 0)
    summary = {
        "briefs": f"{sum(b['status'] == 'valid' for b in briefs)}/{len(briefs)} valid (published) at weeks {list(BRIEF_WEEKS)}",
        "number_grounding_pct": round(100 * grounded / total, 1) if total else None,
        "numbers_checked": total,
        "first_draft_errors_total": sum((b["first_draft"] or {}).get("errors", 0) for b in briefs),
        "brief_section_accuracy_min": min(b["section_accuracy"] for b in briefs),
        "brief_direction_errors": sum(b["direction_errors"] for b in briefs),
        "semantic_layer_accuracy": qa["semantic"]["accuracy"], "raw_sql_accuracy": qa["raw_sql"]["accuracy"],
        "abstention_rate_semantic": qa["semantic"]["abstention_rate"], "abstention_rate_raw_sql": qa["raw_sql"]["abstention_rate"],
        "false_abstentions": {m: qa[m]["false_abstentions"] for m in qa},
        "note": "raw-SQL mode can read mart_segment_week, the semantic layer's own pre-aggregated input",
    }
    return {"briefs": briefs, "qa": qa, "summary": summary, "gates": llm_gates(briefs, qa)}


def llm_gates(briefs: list[dict], qa: dict) -> dict:
    total = sum(b["numbers_checked"] for b in briefs)
    grounded = sum(b["numbers_checked"] for b in briefs if b["status"] == "valid" and b["final_errors"] == 0)
    return {
        "all_briefs_valid": {"pass": all(b["status"] == "valid" for b in briefs),
                             "value": f"{sum(b['status'] == 'valid' for b in briefs)}/{len(briefs)}",
                             "rule": "every eval brief published (a failed brief never counts as grounded)"},
        "grounding_100": {"pass": total > 0 and grounded == total, "value": f"{grounded}/{total}",
                          "rule": "100% of numbers in the briefs match their cited facts"},
        "brief_accuracy": {"pass": all(b["section_accuracy"] >= 0.9 for b in briefs)
                           and sum(b["direction_errors"] for b in briefs) == 0,
                           "value": f"min {min(b['section_accuracy'] for b in briefs):.2f}, "
                                    f"{sum(b['direction_errors'] for b in briefs)} direction errors",
                           "rule": ">= 90% of sections accurate in every brief AND zero direction errors"},
        "top_action_true_scope": {"pass": all(b["top_scope_true"] for b in briefs),
                                  "value": f"{sum(b['top_scope_true'] for b in briefs)}/{len(briefs)}",
                                  "rule": "each brief's top-ranked action is on an injected scope"},
        "sample_scale_labeled": {"pass": all(b["sample_scale_labeled"] for b in briefs),
                                 "value": f"{sum(b['sample_scale_labeled'] for b in briefs)}/{len(briefs)}",
                                 "rule": "every action section labels its $ as sample-scale"},
        "abstention_100": {"pass": qa["semantic"]["abstention_rate"] == 1.0, "value": qa["semantic"]["abstention_rate"],
                           "rule": "abstains on all 5 unanswerable questions (semantic-layer mode)"},
    }


def main(argv: Sequence[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="eval", description=SYNTHETIC_BANNER)
    p.add_argument("--live", action="store_true", help="record missing LLM responses (costs tokens)")
    p.add_argument("--yes", action="store_true", help="skip the >20-call confirmation")
    p.add_argument("--skip-llm", action="store_true")
    args = p.parse_args(argv)
    budget = Budget(0)
    if args.live and os.environ.get("REPLAY") == "1":
        log.error("REPLAY=1 forbids live calls; unset REPLAY to record with --live")
        return 2
    if args.live:
        planned = planned_calls()
        cap = min(planned, int(os.environ.get("MAX_API_CALLS", 50)))  # CLAUDE.md budget rule 7; reruns resume
        log.info("Planned live calls (upper bound): %d (model %s); hard cap for this run: %d", planned,
                 model_for("final"), cap)
        if not confirm_live(planned, args.yes):
            log.info("aborted")
            return 0
        os.environ["REPLAY"] = "0"
        budget = Budget(cap)
    else:
        os.environ["REPLAY"] = "1"
    results = {"detector": run_detector_eval()}
    if not args.skip_llm:
        results["llm"] = llm_eval(budget)
    if args.live:
        RECORDING_COST.write_text(json.dumps(token_totals(TOKEN_LOG, prefix="eval"), indent=2) + "\n")
    recorded = json.loads(RECORDING_COST.read_text()) if RECORDING_COST.exists() else {}
    results["cost"] = {"eval recording (committed)": recorded,
                       "this run, live": {"live_calls": budget.used, "est_cost_usd": "see recording" if budget.used else 0},
                       "all logged calls on this machine": token_totals(TOKEN_LOG)}
    write_report(results, EVAL_DIR / "results.md", EVAL_DIR / "results.json")
    log.info("wrote eval/results.md and eval/results.json")
    return 0


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    sys.exit(main())
