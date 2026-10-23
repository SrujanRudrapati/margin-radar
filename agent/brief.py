"""make_brief: deterministic detection → (LLM narrative only when there is something to explain) → grounding check.

Abstentions and alert-free weeks get deterministic briefs with no LLM call. A brief that fails grounding is retried
once with the errors fed back, then fails closed (week_XX.invalid.md, never published). Synthetic data — not Opendoor data.
"""
import json
from pathlib import Path

from agent.config import model_for
from agent.llm import LLM
from agent.loop import AgentDidNotFinish, revise, run_agent
from agent.render import render
from agent.tools import Toolbox
from agent.validate import CITE, check_detailed, check_structure
from detector.governed import DerivedFact, GovernedStore
from detector.rules import detect

RUN_ID = "injected"


class BriefFailed(RuntimeError):
    """The brief could not be produced; a week_XX.invalid.md record was written instead."""


class GroundingError(BriefFailed):
    def __init__(self, errors: list[str]):
        super().__init__("brief failed the grounding check:\n" + "\n".join(errors))
        self.errors = errors


ABSTAIN_BODY = ("## Top actions\nNone this week — we abstain. The detector does not yet have enough history "
                "or volume in any segment to separate drift from seasonality, so no action is ranked.\n\n"
                "## What we're not sure about\nEverything that depends on the peer baseline: it needs more weeks "
                "of data before a change can be called drift rather than noise or season.")
OUT_OF_RANGE_BODY = ("## Top actions\nNone — we abstain. Week {week} is outside the data range (weeks 0 to {last}), "
                     "so there is nothing to measure.\n\n## What we're not sure about\nEverything about week {week}.")
NO_ALERT_BODY = ("## Top actions\nNo active alerts this week. Every leading indicator is within its normal "
                 "range relative to peer segments in the same week, so seasonal moves (such as the spring "
                 "peak and the summer margin dip) are not flagged.\n\n"
                 "## What we're not sure about\nShifts that hit every segment at once cancel out in a peer "
                 "comparison; the portfolio check only catches abrupt ones.")


def make_brief(db: str | Path, as_of_week: int, purpose: str = "dev", out_dir: str | Path = "briefs",
               llm=None, max_turns: int = 8) -> Path:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = f"week_{as_of_week:02d}"
    log_path = out_dir / f"{stem}.queries.jsonl"
    log_path.unlink(missing_ok=True)  # one run, one log: reruns must not append
    with GovernedStore(str(db), RUN_ID, log_path=str(log_path)) as store:
        week_start = store.week_start(as_of_week)
        if not 0 <= as_of_week <= store.max_week:
            body = OUT_OF_RANGE_BODY.format(week=as_of_week, last=store.max_week)
            return _write(out_dir, stem, *render(body, {}, [], as_of_week, week_start, "abstain", None, purpose))
        result = detect(store, as_of_week)
        if any(a.scope == "all" for a in result.abstentions):
            return _write(out_dir, stem, *render(ABSTAIN_BODY, {}, [], as_of_week, week_start, "abstain", None, purpose))
        if not result.alerts:
            return _write(out_dir, stem, *render(NO_ALERT_BODY, {}, [], as_of_week, week_start, "no_alerts", None, purpose))
        toolbox = Toolbox(store, as_of_week)
        llm = llm or LLM(model_for(purpose), purpose, run_tag=f"brief-{stem}")
        model = getattr(llm, "model", None)
        transcript: list = []
        known = {item_id for item_id in _store_ids(store)}
        try:
            body = run_agent(llm, toolbox, as_of_week, week_start, max_turns=max_turns, transcript=transcript)
            errors, checked = _all_checks(body, toolbox, known)
            if errors:
                body = revise(llm, toolbox, transcript, body, errors[:25])
                errors, checked = _all_checks(body, toolbox, known | set(_store_ids(store)))
        except AgentDidNotFinish as exc:
            reason = f"model did not finish: {exc}"
            md, payload = render(f"_Brief not produced: {reason}._", {}, [], as_of_week, week_start, "invalid",
                                 model, purpose, grounding={"numbers_checked": 0, "errors": [reason]})
            _write_invalid(out_dir, stem, md, payload)
            raise BriefFailed(reason) from exc
        cited = list(dict.fromkeys(m.group(1) for m in CITE.finditer(body) if m.group(1) in toolbox.facts))
        status = "invalid" if errors else "valid"
        md, payload = render(body, toolbox.facts, cited, as_of_week, week_start, status, model, purpose,
                             _provenance(store, cited), {"numbers_checked": checked, "errors": errors})
        if errors:
            _write_invalid(out_dir, stem, md, payload)
            raise GroundingError(errors)
        return _write(out_dir, stem, md, payload)


def _all_checks(body: str, toolbox: Toolbox, known: set[str]) -> tuple[list[str], int]:
    errors, checked = check_detailed(body, toolbox.facts, known)
    if toolbox.last_alerts is None:
        errors.append("get_alerts was not called; the brief must report the ranked actions it returns")
    else:
        errors += check_structure(body, toolbox.last_alerts["actions"])
    return errors, checked


def _store_ids(store: GovernedStore) -> list[str]:
    return [getattr(item, "query_id", None) or getattr(item, "fact_id") for item in store.all()]


def _write_invalid(out_dir: Path, stem: str, md: str, payload: dict) -> None:
    for suffix in (".md", ".json"):  # never leave an older valid brief published next to a failure
        (out_dir / f"{stem}{suffix}").unlink(missing_ok=True)
    _write(out_dir, f"{stem}.invalid", md, payload)


def _provenance(store: GovernedStore, cited: list[str]) -> dict[str, dict]:
    out = {}
    for ref in cited:
        queries, stack, seen = {}, [ref], set()
        while stack:
            item_id = stack.pop()
            if item_id in seen:
                continue
            seen.add(item_id)
            item = store.get(item_id)
            if isinstance(item, DerivedFact):
                stack.extend(item.inputs)
            else:
                queries[item_id] = {"metric": item.metric, "level": item.level, "sql": item.sql}
        out[ref] = {"queries": sorted(queries), "sql": queries}
    return out


def _write(out_dir: Path, stem: str, md: str, payload: dict) -> Path:
    path = out_dir / f"{stem}.md"
    path.write_text(md + "\n")
    (out_dir / f"{stem}.json").write_text(json.dumps(payload, indent=2, default=str) + "\n")
    return path
