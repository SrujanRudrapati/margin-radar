import json

import pytest

from eval.report import confirm_live, token_totals, write_report


def test_confirm_live_prompts_over_20():
    assert confirm_live(10, yes=False, input_fn=lambda _: "n") is True       # small: no prompt needed
    assert confirm_live(40, yes=False, input_fn=lambda _: "n") is False
    assert confirm_live(40, yes=False, input_fn=lambda _: "y") is True
    assert confirm_live(40, yes=True, input_fn=lambda _: pytest.fail("must not prompt")) is True


def test_token_totals_filters_by_tag(tmp_path):
    log = tmp_path / "t.jsonl"
    rows = [{"run_tag": "eval-qa", "model": "claude-sonnet-5-5", "replay": False, "input_tokens": 100, "output_tokens": 10,
             "cache_read_input_tokens": 5, "cache_creation_input_tokens": 0, "est_cost_usd": 0.001, "batch": True},
            {"run_tag": "brief-week_40", "model": "claude-haiku-5-5", "replay": False, "input_tokens": 7,
             "output_tokens": 1, "cache_read_input_tokens": 0, "cache_creation_input_tokens": 0, "est_cost_usd": None}]
    log.write_text("\n".join(json.dumps(r) for r in rows))
    t = token_totals(log, prefix="eval")
    assert t["live_calls"] == 1 and t["input_tokens"] == 100 and t["est_cost_usd"] == pytest.approx(0.001)
    assert token_totals(log)["est_cost_usd"] == "unknown"  # an unpriced call makes the total unknown


def test_report_has_banner_gates_and_cost(tmp_path):
    results = {"detector": {"gates": {"control_zero_alerts": {"pass": False, "value": 3, "rule": "0"}},
                            "by_split": {}},
               "llm": {"gates": {"grounding_100": {"pass": True, "value": 1.0, "rule": "100%"}}},
               "cost": {"eval": {"est_cost_usd": "unknown"}, "night": {"est_cost_usd": 0.5}}}
    md = write_report(results, tmp_path / "results.md", tmp_path / "results.json")
    assert md.startswith("Synthetic data — not Opendoor data.")
    assert "FAIL" in md and "PASS" in md and "unknown" in md
    assert json.loads((tmp_path / "results.json").read_text())["detector"]["gates"]["control_zero_alerts"]["pass"] is False
