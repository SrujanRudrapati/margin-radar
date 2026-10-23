Synthetic data — not Opendoor data.

# Margin Radar weekly brief — week 45 (week of 2025-11-17)

_Synthetic iBuyer portfolio (injected-scenario run). Every number cites a governed fact `[q:ID]`; see Citations at the end._

## Top actions

### M05 — renovation cost drift
- **What changed:** Renovation overrun in M05 rose to 21.6% [q:D428e0d48ae] in week 45. That is +19.3 pts [q:Dd3f684356b] above the peer median of 0.2% [q:D8c8772d4fa]. The uncalibrated drift score is 6.7 [q:D3c9318c172]. The step began in week 37, when M05 reached 13.1% [q:Da7cbf2ac84] against peers at 3.9% [q:D9af48c03e2].
- **Why it's not seasonality:** Peers moved together and fell, from 5.6% [q:Dc54b254388] in week 40 to 0.2% [q:D8c8772d4fa] in week 45. M05 kept climbing over the same weeks, from 18.1% [q:D9434035f07] to 21.6% [q:D428e0d48ae]. The gap has widened since onset and has not reverted.
- **Adverse-selection verdict:** Not applicable. This is a cost-estimate problem, not a conversion problem.
- **Impact:** The impact is measured from current leading-indicator data. It is not a resale-confirmed loss. It is $1.0M [q:D5880d9f239] sample-scale, which is 13 bps [q:D6dc2ff9952] of portfolio contribution margin. That is 84 bps [q:D22467f6e9b] on the M05 exposure of $124.7M [q:D09fc2d06fc]. Each 100 bps of erosion would cost $1.2M [q:Dddf841ee5f].
- **Action / owner:** Renovation should re-baseline M05 renovation estimates and require an in-person assessment.

### B2 — adverse selection
- **What changed:** The B2 contract rate is 40.4% [q:D0e7e7902cd] against a peer median of 38.2% [q:Da4b39f7815], a gap of +2.3 pts [q:D4c614083d2]. The share of contracts above the peer-expected rate is 5.7% [q:Da15ef17c74]. The uncalibrated drift score is only 0.5 [q:Dbc823172e4].
- **Why it's not seasonality:** B2 has run above peers since week 35, when the gap was +6.9 pts [q:D837717b7df]. It peaked at +14.2 pts [q:D10f014e7f3] in week 38. The peer median itself swings a lot week to week, so the gap is the useful read. The gap has narrowed sharply since the peak but has not closed.
- **Adverse-selection verdict:** Yes, as a scenario. Conversion rose while our spread did not change. B2 spread is 6.6% [q:D1b66f39508] against peers at 6.6% [q:D12753180e3], a gap of +0.0 pts [q:D42f631cea3]. That pattern fits sellers accepting offers because the homes are worth less than our model thinks.
- **Impact:** This is a scenario estimate, sample-scale. It is unconfirmed until resales, and it is ranked on its midpoint. The range is $164K [q:D69f095ffd0] to $492K [q:D1bfe4e7ed5], with a midpoint of $328K [q:Dc6e052072f]. In portfolio contribution margin that is 3 bps [q:D8859acb6f8] to 8 bps [q:D81644df68b], with a midpoint of 5 bps [q:D8f2e765ae8]. The assumed shortfall runs from 1.0% [q:D42af78a82e] to 3.0% [q:D39e338d6c0]. Each 100 bps of erosion would cost $2.9M [q:D0be2d1d569] on the $288.5M [q:Df908b6b18e] exposure.
- **Action / owner:** Pricing should widen the B2 spread or add in-person inspection, and audit the model valuation inputs.

## What we're not sure about
- **B2 is the weaker signal.** The latest drift score is low and the gap has shrunk from its peak. The dollar range is an assumption about shortfall, not an observed loss. We cannot say whether adverse selection is continuing or has faded. Resales from the affected purchases will settle it.
- **M05 is measured on leading indicators, not on resales.** We have not checked whether the cause is contractor pricing, scope or estimating error. The in-person assessment should answer that.
- **Sources and coverage.** We did not pull cohort bleed curves, so we cannot say how much margin has already shown up in sold homes. No watch items or abstentions were raised this week.

---
_Dollar figures are sample-scale ($ at the synthetic portfolio's ~$1.6B/yr). Drift scores are uncalibrated scores, not probabilities that an alert is real. Status: valid._

## Citations

| ref | what | value | source queries |
|---|---|---|---|
| `q:D428e0d48ae` | reno_overrun_pct M05 week 45 | 21.6% | Qca7a341d62, Qe83367e8ae |
| `q:Dd3f684356b` | reno_overrun_pct M05 gap vs peers week 45 | +19.3 pts | Qca7a341d62, Qe83367e8ae |
| `q:D8c8772d4fa` | reno_overrun_pct peers of M05 week 45 | 0.2% | Qca7a341d62, Qe83367e8ae |
| `q:D3c9318c172` | Ab238fd5c score | 6.7 | Qca7a341d62 |
| `q:Da7cbf2ac84` | reno_overrun_pct M05 week 37 | 13.1% | Qca7a341d62, Qe83367e8ae |
| `q:D9af48c03e2` | reno_overrun_pct peers of M05 week 37 | 3.9% | Qca7a341d62, Qe83367e8ae |
| `q:Dc54b254388` | reno_overrun_pct peers of M05 week 40 | 5.6% | Qca7a341d62, Qe83367e8ae |
| `q:D9434035f07` | reno_overrun_pct M05 week 40 | 18.1% | Qca7a341d62, Qe83367e8ae |
| `q:D5880d9f239` | Ab238fd5c usd_mid | $1.0M | Q3ce14038af, Q5df4ff3cc9, Q81a305fbf8, Q92c8a6f1ce, Qaa4209a6db, Qca7a341d62 |
| `q:D6dc2ff9952` | Ab238fd5c portfolio_cm_bps_mid | 13 bps | Q3ce14038af, Q5df4ff3cc9, Q81a305fbf8, Q92c8a6f1ce, Qaa4209a6db, Qca7a341d62 |
| `q:D22467f6e9b` | Ab238fd5c scope_bps_mid | 84 bps | Q3ce14038af, Q5df4ff3cc9, Q81a305fbf8, Q92c8a6f1ce, Qaa4209a6db, Qca7a341d62 |
| `q:D09fc2d06fc` | Ab238fd5c exposure_usd | $124.7M | Q3ce14038af, Q5df4ff3cc9, Q81a305fbf8, Q92c8a6f1ce, Qaa4209a6db, Qca7a341d62 |
| `q:Dddf841ee5f` | Ab238fd5c usd_per_100bps | $1.2M | Q3ce14038af, Q5df4ff3cc9, Q81a305fbf8, Q92c8a6f1ce, Qaa4209a6db, Qca7a341d62 |
| `q:D0e7e7902cd` | contract_rate B2 week 45 | 40.4% | Q3aa016583b, Qd448a13898 |
| `q:Da4b39f7815` | contract_rate peers of B2 week 45 | 38.2% | Q3aa016583b, Qd448a13898 |
| `q:D4c614083d2` | contract_rate B2 gap vs peers week 45 | +2.3 pts | Q3aa016583b, Qd448a13898 |
| `q:Da15ef17c74` | A2527e410 B2 excess_share | 5.7% | Q219dda118c, Q443997a8d9, Q4ed0eff2be, Q7699a5997d, Q79966a57df, Q92c8a6f1ce, Q9a919a43ba, Qc28f4cfc17, Qdfb0e29e20, Qf7383b66c0, Qfc26c433ff |
| `q:Dbc823172e4` | contract_rate B2 drift score week 45 | 0.5 | Q3aa016583b, Qd448a13898 |
| `q:D837717b7df` | contract_rate B2 gap vs peers week 35 | +6.9 pts | Q3aa016583b, Qd448a13898 |
| `q:D10f014e7f3` | contract_rate B2 gap vs peers week 38 | +14.2 pts | Q3aa016583b, Qd448a13898 |
| `q:D1b66f39508` | avg_spread_pct B2 week 45 | 6.6% | Qa4a2d4e43e, Qf4208c099e |
| `q:D12753180e3` | avg_spread_pct peers of B2 week 45 | 6.6% | Qa4a2d4e43e, Qf4208c099e |
| `q:D42f631cea3` | avg_spread_pct B2 gap vs peers week 45 | +0.0 pts | Qa4a2d4e43e, Qf4208c099e |
| `q:D69f095ffd0` | A2527e410 usd_low | $164K | Q219dda118c, Q3aa016583b, Q443997a8d9, Q4ed0eff2be, Q7699a5997d, Q79966a57df, Q92c8a6f1ce, Q9a919a43ba, Qc28f4cfc17, Qdfb0e29e20, Qf7383b66c0, Qfc26c433ff |
| `q:D1bfe4e7ed5` | A2527e410 usd_high | $492K | Q219dda118c, Q3aa016583b, Q443997a8d9, Q4ed0eff2be, Q7699a5997d, Q79966a57df, Q92c8a6f1ce, Q9a919a43ba, Qc28f4cfc17, Qdfb0e29e20, Qf7383b66c0, Qfc26c433ff |
| `q:Dc6e052072f` | A2527e410 usd_mid | $328K | Q219dda118c, Q3aa016583b, Q443997a8d9, Q4ed0eff2be, Q7699a5997d, Q79966a57df, Q92c8a6f1ce, Q9a919a43ba, Qc28f4cfc17, Qdfb0e29e20, Qf7383b66c0, Qfc26c433ff |
| `q:D8859acb6f8` | A2527e410 portfolio_cm_bps_low | 3 bps | Q219dda118c, Q3aa016583b, Q443997a8d9, Q4ed0eff2be, Q7699a5997d, Q79966a57df, Q92c8a6f1ce, Q9a919a43ba, Qc28f4cfc17, Qdfb0e29e20, Qf7383b66c0, Qfc26c433ff |
| `q:D81644df68b` | A2527e410 portfolio_cm_bps_high | 8 bps | Q219dda118c, Q3aa016583b, Q443997a8d9, Q4ed0eff2be, Q7699a5997d, Q79966a57df, Q92c8a6f1ce, Q9a919a43ba, Qc28f4cfc17, Qdfb0e29e20, Qf7383b66c0, Qfc26c433ff |
| `q:D8f2e765ae8` | A2527e410 portfolio_cm_bps_mid | 5 bps | Q219dda118c, Q3aa016583b, Q443997a8d9, Q4ed0eff2be, Q7699a5997d, Q79966a57df, Q92c8a6f1ce, Q9a919a43ba, Qc28f4cfc17, Qdfb0e29e20, Qf7383b66c0, Qfc26c433ff |
| `q:D42af78a82e` | planning shortfall low (user-given) | 1.0% | Q443997a8d9 |
| `q:D39e338d6c0` | planning shortfall high (user-given) | 3.0% | Q443997a8d9 |
| `q:D0be2d1d569` | A2527e410 usd_per_100bps | $2.9M | Q219dda118c, Q3aa016583b, Q443997a8d9, Q4ed0eff2be, Q7699a5997d, Q79966a57df, Q92c8a6f1ce, Q9a919a43ba, Qc28f4cfc17, Qdfb0e29e20, Qf7383b66c0, Qfc26c433ff |
| `q:Df908b6b18e` | A2527e410 exposure_usd | $288.5M | Q219dda118c, Q3aa016583b, Q443997a8d9, Q4ed0eff2be, Q7699a5997d, Q79966a57df, Q92c8a6f1ce, Q9a919a43ba, Qc28f4cfc17, Qdfb0e29e20, Qf7383b66c0, Qfc26c433ff |

