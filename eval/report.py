"""Eval report: eval/results.json + eval/results.md (docs/SPEC.md Phase 5). Synthetic data — not Opendoor data."""
import json
from pathlib import Path

from common.banner import SYNTHETIC_BANNER
from common.business import SAMPLE_SCALE_LABEL

LIVE_CALL_PROMPT_THRESHOLD = 20


def confirm_live(planned_calls: int, yes: bool, input_fn=input) -> bool:
    if planned_calls <= LIVE_CALL_PROMPT_THRESHOLD or yes:
        return True
    return input_fn(f"Planned live calls: {planned_calls}. Proceed? [y/N] ").strip().lower() == "y"


def token_totals(log_path: str | Path, prefix: str | None = None) -> dict:
    path = Path(log_path)
    rows = [json.loads(l) for l in path.read_text().splitlines() if l.strip()] if path.exists() else []
    rows = [r for r in rows if prefix is None or str(r.get("run_tag", "")).startswith(prefix)]
    live = [r for r in rows if not r.get("replay")]
    costs = [r.get("est_cost_usd") for r in live]
    return {
        "live_calls": len(live), "batch_calls": sum(1 for r in live if r.get("batch")),
        "replays": len(rows) - len(live),
        "input_tokens": sum(r.get("input_tokens", 0) for r in live),
        "output_tokens": sum(r.get("output_tokens", 0) for r in live),
        "cache_read_input_tokens": sum(r.get("cache_read_input_tokens", 0) or 0 for r in live),
        "cache_creation_input_tokens": sum(r.get("cache_creation_input_tokens", 0) or 0 for r in live),
        "est_cost_usd": "unknown" if any(c is None for c in costs) else round(sum(costs), 4),
    }


def _gate_rows(gates: dict) -> list[str]:
    return [f"| {name} | {'PASS' if g['pass'] else 'FAIL'} | {g['value']} | {g['rule']} |" for name, g in gates.items()]


def write_report(results: dict, md_path: str | Path, json_path: str | Path) -> str:
    Path(json_path).write_text(json.dumps(results, indent=2, default=str) + "\n")
    det, llm = results.get("detector", {}), results.get("llm", {})
    lines = [SYNTHETIC_BANNER, "", "# Margin Radar — evaluation results", "",
             f"_Dollar figures are {SAMPLE_SCALE_LABEL}. Detector scores are uncalibrated._", "",
             "## Gates", "", "| gate | result | value | rule |", "|---|---|---|---|"]
    lines += _gate_rows(det.get("gates", {})) + _gate_rows(llm.get("gates", {}))
    for split, s in det.get("by_split", {}).items():
        lines += ["", f"## Detector — {split} seeds {s.get('seeds')}", "",
                  f"- Control false alerts per week: {s['control_false_alerts_per_week']:.3f} "
                  f"({s['control_alert_weeks']} alert-weeks over {s['control_evaluable_weeks']} evaluable control weeks)",
                  f"- Wrong-scope alert episodes (injected runs): {s['wrong_episodes']}; per week "
                  f"{s['wrong_alert_weeks_per_week']:.3f}",
                  f"- Precision (true alert episodes / all episodes): {_fmt(s['precision'])}; "
                  f"recall before margin shows the problem: {_fmt(s['recall_before_cm'])}", "",
                  "| scenario | detected before margin | median lead (weeks) | min | max | median delay after onset (weeks) |",
                  "|---|---|---|---|---|---|"]
        for name, sc in s["scenarios"].items():
            lines.append(f"| {name} | {sc['detected_before_cm']}/{sc['seeds']} | {_fmt(sc['median_lead_weeks'])} | "
                         f"{_fmt(sc['min_lead_weeks'])} | {_fmt(sc['max_lead_weeks'])} | {_fmt(sc['median_delay_weeks'])} |")
    if llm:
        lines += ["", "## LLM evaluation (seed 42, final model)", ""] + [f"- {k}: {v}" for k, v in llm.get("summary", {}).items()]
    cost = results.get("cost", {})
    if cost:
        lines += ["", "## Tokens and estimated cost", "", "| scope | live calls | input | output | cache read | est. cost (USD) |",
                  "|---|---|---|---|---|---|"]
        for name, t in cost.items():
            lines.append(f"| {name} | {t.get('live_calls', '')} | {t.get('input_tokens', '')} | {t.get('output_tokens', '')} | "
                         f"{t.get('cache_read_input_tokens', '')} | {t.get('est_cost_usd')} |")
    md = "\n".join(lines) + "\n"
    Path(md_path).write_text(md)
    return md


def _fmt(value) -> str:
    if value is None:
        return "n/a"
    return f"{value:.3f}" if isinstance(value, float) and not float(value).is_integer() else str(value)
