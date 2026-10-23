"""Grounding checker, rendering, and brief generation (fake LLMs only)."""
import json
import re

import pytest

from agent.brief import GroundingError, make_brief
from agent.facts import Fact
from agent.render import render
from agent.validate import check
from common.banner import SYNTHETIC_BANNER
from common.business import SAMPLE_SCALE_LABEL

FACTS = {
    "D0000000001": Fact("D0000000001", "b2 contract rate", 0.4658, "pct", "46.6%"),
    "D0000000002": Fact("D0000000002", "b2 gap", 0.0815, "pct_points", "+8.2 pts"),
    "D0000000003": Fact("D0000000003", "usd mid", 888_123.0, "usd", "$888K"),
    "D0000000004": Fact("D0000000004", "usd high", 1_332_000.0, "usd", "$1.3M"),
    "D0000000005": Fact("D0000000005", "bps", 16.2, "bps", "16 bps"),
    "D0000000006": Fact("D0000000006", "score", 4.27, "score", "4.3"),
}


def test_correct_citations_pass():
    body = ("B2 conversion rose to 46.6% [q:D0000000001], +8.2 pts [q:D0000000002] above peers in week 40 "
            "(2025-10-13). Scenario estimate, sample-scale: $888K [q:D0000000003] mid, up to $1.3M [q:D0000000004]; "
            "16 bps [q:D0000000005] of portfolio CM. Uncalibrated score 4.3 [q:D0000000006] for M02-B2-cash.")
    assert check(body, FACTS) == []


def test_hallucinated_number_rejected():
    errors = check("Acceptance rose 12% in B2.", FACTS)
    assert errors and "12%" in errors[0]


def test_wrong_value_rejected():
    errors = check("B2 conversion was 45.0% [q:D0000000001].", FACTS)
    assert errors and "45.0%" in errors[0]


def test_unknown_fact_id_rejected():
    errors = check("Gap +8.2 pts [q:D9999999999].", FACTS)
    assert errors and "D9999999999" in errors[0]


def test_unit_mismatch_rejected():
    assert check("B2 conversion was 46.6 [q:D0000000001].", FACTS)


def test_panel_reference_is_not_a_number_citation():
    assert check("B2 conversion was 46.6% [q:Q0123456789].", FACTS)


def test_context_numbers_need_no_citation():
    assert check("Week 38 to week 40, from 2025-09-29; scopes M02, B2, M05-B3-CNML.", FACTS) == []


def test_render_banner_first_line_and_footer():
    md, payload = render("## Top actions\nbody", FACTS, cited=["D0000000003"], as_of_week=40,
                         week_start="2025-10-13", status="valid", model="m", purpose="dev")
    assert md.splitlines()[0] == SYNTHETIC_BANNER
    assert SAMPLE_SCALE_LABEL in md and "uncalibrated" in md
    assert "D0000000003" in md and payload["banner"] == SYNTHETIC_BANNER and payload["status"] == "valid"


# --- make_brief -----------------------------------------------------------------------------------------

class FactAwareLLM:
    """Calls get_alerts, then writes a body citing the top action's mid $ (valid) or a made-up number (bad)."""

    def __init__(self, good=True):
        self.good, self.calls = good, 0

    def create(self, *, system, messages, tools, max_tokens):
        self.calls += 1
        last = messages[-1]["content"]
        self.last_user_text = last if isinstance(last, str) else ""
        if isinstance(last, str) and len(messages) == 1:
            return {"stop_reason": "tool_use", "usage": {},
                    "content": [{"type": "tool_use", "id": f"t{self.calls}", "name": "get_alerts", "input": {}}]}
        tool_result = next(m["content"][0] for m in messages if isinstance(m["content"], list)
                           and m["content"] and m["content"][0].get("type") == "tool_result")
        alerts = json.loads(tool_result["content"])
        sections = []
        for action in alerts["actions"]:
            impact = action["impact"]
            line = f"### {action['scope']} — {action['kind']}\n- **Impact:** sample-scale"
            if impact["basis"] == "scenario_estimate":
                cites = " to ".join(f"{impact[k]['value']} [{impact[k]['ref']}]" for k in ("usd_low", "usd_high"))
                mid = impact["usd_mid"]
                line += (f" scenario estimate, unconfirmed until resales, ranked on its midpoint {mid['value']} "
                         f"[{mid['ref']}]: {cites}.")
            sections.append(line)
        text = ("## Top actions\n" + "\n".join(sections) + "\n\n## What we're not sure about\nNothing more.") \
            if self.good else "## Top actions\nMargin fell 7.3% everywhere."
        return {"stop_reason": "end_turn", "usage": {}, "content": [{"type": "text", "text": text}]}


def test_valid_brief_written(built_runs, tmp_path):
    llm = FactAwareLLM(good=True)
    path = make_brief(built_runs["injected"], 40, "dev", out_dir=tmp_path, llm=llm)
    md = path.read_text()
    assert path.name == "week_40.md" and md.splitlines()[0] == SYNTHETIC_BANNER
    payload = json.loads((tmp_path / "week_40.json").read_text())
    assert payload["status"] == "valid" and payload["grounding"]["errors"] == []
    assert payload["actions"] and {"scope", "kind", "direction", "metric"} <= set(payload["actions"][0])
    assert payload["grounding"]["first_draft"]["numbers_checked"] >= 1
    assert payload["grounding"]["numbers_checked"] >= 1 and re.search(r"\[q:D[0-9a-f]{10}\]", md)


def test_fails_closed_after_one_retry(built_runs, tmp_path):
    llm = FactAwareLLM(good=False)
    with pytest.raises(GroundingError):
        make_brief(built_runs["injected"], 40, "dev", out_dir=tmp_path, llm=llm)
    assert llm.calls == 3  # tool turn + draft + one revision turn in the same conversation
    assert "grounding check" in llm.last_user_text
    assert (tmp_path / "week_40.invalid.md").exists() and not (tmp_path / "week_40.md").exists()


class ExplodingLLM:
    def create(self, **kwargs):
        raise AssertionError("no LLM call expected")


def test_abstain_brief_makes_no_llm_call(built_runs, tmp_path):
    path = make_brief(built_runs["injected"], 6, "dev", out_dir=tmp_path, llm=ExplodingLLM())
    md = path.read_text()
    assert md.splitlines()[0] == SYNTHETIC_BANNER and "abstain" in md.lower()
    assert json.loads((tmp_path / "week_06.json").read_text())["status"] == "abstain"


def test_no_alert_brief_makes_no_llm_call(built_runs, tmp_path):
    path = make_brief(built_runs["injected"], 33, "dev", out_dir=tmp_path, llm=ExplodingLLM())
    assert "no active alerts" in path.read_text().lower()
    assert json.loads((tmp_path / "week_33.json").read_text())["status"] == "no_alerts"


def test_week_range_pattern_does_not_eat_following_figure():
    # Seen live: "week 35 to 46.6%" must not mask the "46" of the cited figure.
    body = "Contract rate rose in week 35 to 46.6% [q:D0000000001] in week 40; weeks 30 to 40 covered."
    assert check(body, FACTS) == []


# --- Phase 4 final-review holes (each confirmed by the reviewer) ------------------------------------------

@pytest.mark.parametrize("body", [
    "Up to $1M [q:D0000000004].",          # fact is $1.3M: coarse rounding must not pass
    "Mid $0M [q:D0000000003].",
    "Score 4 [q:D0000000006].",             # fact displays 4.3
])
def test_coarse_rounding_rejected(body):
    assert check(body, FACTS), body


def test_plus_sign_optional_on_points():
    assert check("A gap of 8.2 pts [q:D0000000002].", FACTS) == []


@pytest.mark.parametrize("body", [
    "In week 40 and 300 homes were affected.",
    "From week 38 to 500 offers.",
])
def test_week_exemption_does_not_hide_numbers(body):
    assert check(body, FACTS), body


def test_week_ranges_still_exempt():
    assert check("Weeks 30–40 and week 35 to week 40 were covered.", FACTS) == []


@pytest.mark.parametrize("body", [
    "Conversion doubled in B2.", "Losses near twelve million dollars.", "Three times the peer rate.",
    "About half of contracts.",
])
def test_number_words_rejected(body):
    assert check(body, FACTS), body


def test_per_hundred_bps_sensitivity_phrase_allowed():
    assert check("Each 100 bps of erosion would cost $888K [q:D0000000003].", FACTS) == []


def test_fabricated_query_reference_rejected():
    errors = check("Confirmed by resales [q:Qdeadbeef00].", FACTS, known_refs=set())
    assert errors and "Qdeadbeef00" in errors[0]


def test_known_query_reference_allowed_without_numbers():
    assert check("Source: [q:Q0123456789].", FACTS, known_refs={"Q0123456789"}) == []


def test_structure_requires_ranked_actions_in_order_and_scenario_labels():
    from agent.validate import check_structure
    actions = [{"scope": "B2", "impact": {"basis": "scenario_estimate",
                                          "usd_low": {"ref": "q:D0000000003"}, "usd_mid": {"ref": "q:D0000000003"},
                                          "usd_high": {"ref": "q:D0000000004"}}},
               {"scope": "M05", "impact": {"basis": "measured"}}]
    good = ("## Top actions\n### B2 — adverse selection\nScenario estimate, unconfirmed until resales, ranked on its "
            "midpoint: $888K [q:D0000000003] to $1.3M [q:D0000000004].\n### M05 — renovation\nx\n"
            "## What we're not sure about\ny")
    assert check_structure(good, actions) == []
    assert check_structure(good.replace("### M05", "### Other"), actions)                 # missing action
    assert check_structure(good.replace("unconfirmed until resales", "pending"), actions)  # missing label
    swapped = good.replace("### B2 — adverse selection", "### TMP").replace("### M05 — renovation", "### B2 — x")
    assert check_structure(swapped.replace("### TMP", "### M05 —"), actions)               # wrong order
    assert check_structure(good.replace("## What we're not sure about", "## Notes"), actions)


def test_out_of_range_week_writes_abstain_brief(built_runs, tmp_path):
    for week in (999, -1):
        path = make_brief(built_runs["injected"], week, "dev", out_dir=tmp_path, llm=ExplodingLLM())
        payload = json.loads(path.with_suffix(".json").read_text())
        assert payload["status"] == "abstain" and "range" in path.read_text().lower()


def test_query_log_is_rewritten_not_appended(built_runs, tmp_path):
    make_brief(built_runs["injected"], 33, "dev", out_dir=tmp_path, llm=ExplodingLLM())
    first = (tmp_path / "week_33.queries.jsonl").read_text()
    make_brief(built_runs["injected"], 33, "dev", out_dir=tmp_path, llm=ExplodingLLM())
    assert (tmp_path / "week_33.queries.jsonl").read_text() == first


class StopsEarlyLLM:
    def create(self, **kwargs):
        return {"stop_reason": "max_tokens", "content": [{"type": "text", "text": "## Top"}], "usage": {}}


def test_model_stop_fails_closed_with_record(built_runs, tmp_path):
    from agent.brief import BriefFailed
    with pytest.raises(BriefFailed):
        make_brief(built_runs["injected"], 40, "dev", out_dir=tmp_path, llm=StopsEarlyLLM())
    assert (tmp_path / "week_40.invalid.md").exists() and not (tmp_path / "week_40.md").exists()
