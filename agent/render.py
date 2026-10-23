"""Brief rendering: deterministic banner, header and footer around the model's body. Synthetic data — not Opendoor data."""
from agent.facts import Fact
from common.banner import SYNTHETIC_BANNER
from common.business import SAMPLE_SCALE_LABEL


def render(body: str, facts: dict[str, Fact], cited: list[str], as_of_week: int, week_start: str, status: str,
           model: str | None, purpose: str | None, provenance: dict[str, dict] | None = None,
           grounding: dict | None = None, actions: list[dict] | None = None) -> tuple[str, dict]:
    provenance = provenance or {}
    lines = [
        SYNTHETIC_BANNER, "",
        f"# Margin Radar weekly brief — week {as_of_week:02d} (week of {week_start})", "",
        "_Synthetic iBuyer portfolio (injected-scenario run). Every number cites a governed fact `[q:ID]`; "
        "see Citations at the end._", "",
        body.strip(), "", "---",
        f"_Dollar figures are {SAMPLE_SCALE_LABEL}. Drift scores are uncalibrated scores, not probabilities "
        f"that an alert is real. Status: {status}._", "",
    ]
    citations = []
    if cited:
        lines += ["## Citations", "", "| ref | what | value | source queries |", "|---|---|---|---|"]
        for ref in cited:
            fact = facts[ref]
            source = ", ".join(provenance.get(ref, {}).get("queries", []))
            lines.append(f"| `q:{ref}` | {fact.label} | {fact.display} | {source} |")
            citations.append({"ref": ref, "label": fact.label, "value": fact.value, "display": fact.display,
                              "kind": fact.kind, **provenance.get(ref, {})})
        lines.append("")
    payload = {"banner": SYNTHETIC_BANNER, "sample_scale_label": SAMPLE_SCALE_LABEL, "week": as_of_week,
               "week_start": week_start, "status": status, "model": model, "purpose": purpose, "body": body.strip(),
               "citations": citations, "grounding": grounding or {"numbers_checked": 0, "errors": []},
               "actions": actions or []}
    return "\n".join(lines), payload
