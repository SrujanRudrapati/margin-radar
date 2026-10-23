import json

import pytest

import eval.__main__ as M


def test_planned_calls_is_a_true_upper_bound():
    from agent.loop import MAX_TURNS_DEFAULT, REVISE_TURNS
    from eval.qa import MAX_TURNS, QUESTIONS, UNANSWERABLE
    expected = len(M.BRIEF_WEEKS) * (MAX_TURNS_DEFAULT + REVISE_TURNS) + 2 * (len(QUESTIONS) + len(UNANSWERABLE)) * MAX_TURNS
    assert M.planned_calls() == expected


def test_replay_is_the_default_and_live_abort_constructs_no_llm(monkeypatch):
    monkeypatch.setattr(M, "run_detector_eval", lambda: pytest.fail("aborted run must not evaluate"))
    monkeypatch.setattr(M, "LLM", lambda *a, **k: pytest.fail("aborted run must not construct an LLM"))
    monkeypatch.setattr("builtins.input", lambda _: "n")
    assert M.main(["--live"]) == 0


def test_llm_gates_fail_when_a_brief_is_not_valid():
    briefs = [{"week": 40, "status": "valid", "numbers_checked": 10, "final_errors": 0, "section_accuracy": 1.0,
               "direction_errors": 0, "top_scope_true": True, "sample_scale_labeled": True},
              {"week": 45, "status": "invalid", "numbers_checked": 0, "final_errors": 1, "section_accuracy": 0.0,
               "direction_errors": 0, "top_scope_true": False, "sample_scale_labeled": False}]
    qa = {m: {"accuracy": 1.0, "abstention_rate": 1.0, "false_abstentions": 0} for m in ("semantic", "raw_sql")}
    gates = M.llm_gates(briefs, qa)
    assert gates["all_briefs_valid"]["pass"] is False and gates["brief_accuracy"]["pass"] is False
