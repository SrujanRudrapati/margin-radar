Synthetic data — not Opendoor data.

# Margin Radar — evaluation results

_Dollar figures are sample-scale ($ at the synthetic portfolio's ~$1.6B/yr). Detector scores are uncalibrated._

## Gates

| gate | result | value | rule |
|---|---|---|---|
| all_control_zero_alerts | FAIL | 78 | 0 control alert-weeks (all seeds) |
| all_recall_before_cm | FAIL | {'A': '0/10', 'B': '5/10', 'C': '9/10'} | >= 8/10 of all seeds per scenario alert on the true scope before margin shows it |
| all_wrong_alerts | FAIL | 8 | <= 2 wrong-scope alert episodes (all injected runs) |
| holdout_control_zero_alerts | FAIL | 62 | 0 control alert-weeks (holdout seeds) |
| holdout_recall_before_cm | FAIL | {'A': '0/5', 'B': '4/5', 'C': '5/5'} | >= 8/10 of holdout seeds per scenario alert on the true scope before margin shows it |
| holdout_wrong_alerts | FAIL | 5 | <= 1 wrong-scope alert episodes (holdout injected runs) |
| all_briefs_valid | PASS | 4/4 | every eval brief published (a failed brief never counts as grounded) |
| grounding_100 | PASS | 129/129 | 100% of numbers in the briefs match their cited facts |
| brief_accuracy | PASS | min 1.00, 0 direction errors | >= 90% of sections accurate in every brief AND zero direction errors |
| top_action_true_scope | PASS | 4/4 | each brief's top-ranked action is on an injected scope |
| sample_scale_labeled | PASS | 4/4 | every action section labels its $ as sample-scale |
| abstention_100 | PASS | 1.0 | abstains on all 5 unanswerable questions (semantic-layer mode) |

## Detector — tuning seeds [1, 2, 3, 4, 5]

- Control false alerts per week: 0.062 (16 alert-weeks over 255 evaluable control weeks)
- Wrong-scope alert episodes (injected runs): 3; per week 0.039
- Control alert-weeks per seed: s1: 5, s2: 0, s3: 11, s4: 0, s5: 0
- Precision (true alert episodes / all episodes): 0.625; recall before margin shows the problem: 0.333

| scenario | detected before margin | median lead (weeks) | min | max | median delay after onset (weeks) |
|---|---|---|---|---|---|
| A | 0/5 | n/a | n/a | n/a | n/a |
| B | 1/5 | 7 | 7 | 7 | 11 |
| C | 4/5 | 12.0 | 5 | 13 | 5.500 |

## Detector — holdout seeds [6, 7, 8, 9, 10]

- Control false alerts per week: 0.243 (62 alert-weeks over 255 evaluable control weeks)
- Wrong-scope alert episodes (injected runs): 5; per week 0.172
- Control alert-weeks per seed: s6: 16, s7: 18, s8: 0, s9: 18, s10: 10
- Precision (true alert episodes / all episodes): 0.666; recall before margin shows the problem: 0.600

| scenario | detected before margin | median lead (weeks) | min | max | median delay after onset (weeks) |
|---|---|---|---|---|---|
| A | 0/5 | n/a | n/a | n/a | n/a |
| B | 4/5 | 9.0 | 8 | 13 | 6.0 |
| C | 5/5 | 8 | 7 | 11 | 7 |

## Detector — all seeds [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]

- Control false alerts per week: 0.152 (78 alert-weeks over 510 evaluable control weeks)
- Wrong-scope alert episodes (injected runs): 8; per week 0.105
- Control alert-weeks per seed: s1: 5, s2: 0, s3: 11, s4: 0, s5: 0, s6: 16, s7: 18, s8: 0, s9: 18, s10: 10
- Precision (true alert episodes / all episodes): 0.652; recall before margin shows the problem: 0.466

| scenario | detected before margin | median lead (weeks) | min | max | median delay after onset (weeks) |
|---|---|---|---|---|---|
| A | 0/10 | n/a | n/a | n/a | n/a |
| B | 5/10 | 8 | 7 | 13 | 7 |
| C | 9/10 | 8 | 5 | 13 | 6 |

## LLM evaluation (seed 42, final model)

- briefs: 4/4 valid (published) at weeks [40, 45, 50, 60]
- number_grounding_pct: 100.0
- numbers_checked: 129
- first_draft_errors_total: 1
- brief_section_accuracy_min: 1.0
- brief_direction_errors: 0
- semantic_layer_accuracy: 1.0
- raw_sql_accuracy: 0.95
- abstention_rate_semantic: 1.0
- abstention_rate_raw_sql: 1.0
- false_abstentions: {'semantic': 0, 'raw_sql': 0}
- note: raw-SQL mode can read mart_segment_week, the semantic layer's own pre-aggregated input

## Tokens and estimated cost

| scope | live calls | input | output | cache read | est. cost (USD) |
|---|---|---|---|---|---|
| eval recording (committed) | 157 | 112871 | 26994 | 221701 | 0.3937 |
| this run, live | 0 |  |  |  | 0 |
| all logged calls on this machine | 182 | 208118 | 52520 | 281695 | 0.5793 |

## Known limitations

- Simultaneous all-segment shifts cancel in peer comparisons; the portfolio check only catches abrupt ones.
- Scenario scopes (M02, B2, M05) and onset (week 30) are the same in every seed; seeds vary only the noise.
- The detector configuration was chosen with pooled seed counts (DECISIONS D16), so the holdout split is not fully held out for that design decision.
- Demand-softening impact is a lower bound (holding cost only); adverse-selection impact is a scenario estimate until resales confirm it.
- Dollar figures are sample-scale; scores are uncalibrated, not probabilities.
