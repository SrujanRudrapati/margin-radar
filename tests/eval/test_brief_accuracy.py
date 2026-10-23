from eval.brief_accuracy import brief_accuracy

ACTIONS = [{"scope": "B2", "kind": "adverse_selection", "direction": "+", "metric": "contract_rate"},
           {"scope": "M02", "kind": "demand_softening", "direction": "-", "metric": "first_offer_rate"}]


def body(b2_change="rose", m02_change="slowed", m02_extra=""):
    return (f"## Top actions\n### B2 — adverse selection\n- **What changed:** Conversion {b2_change} to 46.6% [q:D1].\n"
            f"### M02 — demand softening\n- **What changed:** First offers {m02_change} {m02_extra}[q:D2].\n"
            "## What we're not sure about\nx")


def test_all_sections_accurate():
    acc = brief_accuracy(body(), ACTIONS)
    assert acc.section_accuracy == 1.0 and acc.direction_errors == 0


def test_one_wrong_direction_of_two():
    acc = brief_accuracy(body(b2_change="fell"), ACTIONS)
    assert acc.section_accuracy == 0.5 and acc.direction_errors == 1


def test_other_scope_in_section_is_inaccurate_but_not_direction_error():
    acc = brief_accuracy(body(m02_extra="unlike B2 "), ACTIONS)
    assert acc.section_accuracy == 0.5 and acc.direction_errors == 0


def test_missing_section_counts_against_accuracy():
    text = "## Top actions\n### B2 — x\n- **What changed:** rose\n## What we're not sure about\n"
    assert brief_accuracy(text, ACTIONS).section_accuracy == 0.5


def test_uncertainty_section_naming_other_scopes_does_not_hurt_last_action():
    text = body() .replace("## What we're not sure about\nx", "## What we're not sure about\nB2 and M02 are both early.")
    assert brief_accuracy(text, ACTIONS).section_accuracy == 1.0


def test_above_in_definition_does_not_mask_wrong_verb():
    text = body(b2_change="fell (share of contracts above the peer-expected rate)")
    assert brief_accuracy(text, ACTIONS).direction_errors == 1


def test_missing_direction_word_is_inaccurate_not_a_direction_error():
    acc = brief_accuracy(body(b2_change="was"), ACTIONS)
    assert acc.section_accuracy == 0.5 and acc.direction_errors == 0


def test_no_actions_scores_zero():
    assert brief_accuracy("anything", []).section_accuracy == 0.0
