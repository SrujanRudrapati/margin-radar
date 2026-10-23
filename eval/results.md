Synthetic data — not Opendoor data.

# Margin Radar — evaluation results

_Dollar figures are sample-scale ($ at the synthetic portfolio's ~$1.6B/yr). Detector scores are uncalibrated._

## Gates

| gate | result | value | rule |
|---|---|---|---|
| holdout_control_zero_alerts | FAIL | 29 | 0 control alert-weeks (holdout seeds) |
| holdout_recall_before_cm | FAIL | {'A': '0/10', 'B': '8/10', 'C': '8/10'} | >= 8/10 of holdout seeds per scenario alert on the true scope before margin shows it |
| holdout_wrong_alerts | FAIL | 5 | <= 2 wrong-scope alert episodes (holdout injected runs) |
| all_briefs_valid | PASS | 4/4 | every eval brief published (a failed brief never counts as grounded) |
| grounding_100 | PASS | 107/107 | 100% of numbers in the briefs match their cited facts |
| brief_accuracy | PASS | min 1.00, 0 direction errors | >= 90% of sections accurate in every brief AND zero direction errors |
| top_action_true_scope | PASS | 4/4 | each brief's top-ranked action is on an injected scope |
| sample_scale_labeled | PASS | 4/4 | every action section labels its $ as sample-scale |
| abstention_100 | PASS | 1.0 | abstains on all 5 unanswerable questions (semantic-layer mode) |

## Detector — holdout seeds [11, 12, 13, 14, 15, 16, 17, 18, 19, 20]

- Control false alerts per week: 0.056 (29 alert-weeks over 510 evaluable control weeks)
- Wrong-scope alert episodes (injected runs): 5; per week 0.050
- Control alert-weeks per seed: s11: 8, s12: 0, s13: 0, s14: 0, s15: 14, s16: 6, s17: 0, s18: 1, s19: 0, s20: 0
- Precision (true alert episodes / all episodes): 0.814; recall before margin shows the problem: 0.533

| scenario | detected before margin | median lead (weeks) | min | max | median delay after onset (weeks) |
|---|---|---|---|---|---|
| A | 0/10 | n/a | n/a | n/a | n/a |
| B | 8/10 | 9.500 | 5 | 13 | 7.0 |
| C | 8/10 | 5.500 | 1 | 12 | 9.500 |

## Detector — tuning seeds [1, 2, 3, 4, 5]

- Control false alerts per week: 0.011 (3 alert-weeks over 255 evaluable control weeks)
- Wrong-scope alert episodes (injected runs): 2; per week 0.007
- Control alert-weeks per seed: s1: 0, s2: 0, s3: 3, s4: 0, s5: 0
- Precision (true alert episodes / all episodes): 0.750; recall before margin shows the problem: 0.400

| scenario | detected before margin | median lead (weeks) | min | max | median delay after onset (weeks) |
|---|---|---|---|---|---|
| A | 0/5 | n/a | n/a | n/a | n/a |
| B | 1/5 | 7 | 7 | 7 | 11 |
| C | 5/5 | 7 | 4 | 9 | 9 |

## Detector — seen seeds [6, 7, 8, 9, 10]

- Control false alerts per week: 0.058 (15 alert-weeks over 255 evaluable control weeks)
- Wrong-scope alert episodes (injected runs): 0; per week 0.000
- Control alert-weeks per seed: s6: 0, s7: 0, s8: 0, s9: 8, s10: 7
- Precision (true alert episodes / all episodes): 1.0; recall before margin shows the problem: 0.600

| scenario | detected before margin | median lead (weeks) | min | max | median delay after onset (weeks) |
|---|---|---|---|---|---|
| A | 0/5 | n/a | n/a | n/a | n/a |
| B | 4/5 | 9.0 | 8 | 13 | 6.0 |
| C | 5/5 | 7 | 3 | 10 | 8 |

## LLM evaluation (seed 42, final model)

- briefs: 4/4 valid (published) at weeks [40, 45, 50, 60]
- number_grounding_pct: 100.0
- numbers_checked: 107
- first_draft_errors_total: 4
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
| eval recording (committed) | 170 | 174985 | 38811 | 258553 | 0.6511 |
| this run, live | 0 |  |  |  | 0 |
| all logged calls on this machine | 195 | 270232 | 64337 | 318547 | 0.8367 |

## Known limitations

- Simultaneous all-segment shifts cancel in peer comparisons; the portfolio check only catches abrupt ones.
- Gates and quoted numbers use the true holdout, seeds 11–20 (DECISIONS D28, D30): scopes and onsets are drawn per seed and these seeds were never used for tuning. Seeds 1–5 tuned the thresholds and the D29 shrinkage; seeds 6–10 were seen in an earlier run. Both are shown for transparency only.
- The expanding-baseline design (DECISIONS D16) was chosen before the true holdout existed, on seeds 1–10.
- Demand-softening impact is a lower bound (holding cost only); adverse-selection impact is a scenario estimate until resales confirm it.
- Dollar figures are sample-scale; scores are uncalibrated, not probabilities.
