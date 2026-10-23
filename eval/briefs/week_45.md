Synthetic data — not Opendoor data.

# Margin Radar weekly brief — week 45 (week of 2025-11-17)

_Synthetic iBuyer portfolio (injected-scenario run). Every number cites a governed fact `[q:ID]`; see Citations at the end._

## Top actions

### B2 — adverse selection
- **What changed:** The contract rate in B2 ran above peers from week 35. The gap was +13.7 pts [q:D9b7cca71ce] in week 37 and +14.2 pts [q:D10f014e7f3] in week 38. In week 45 the contract rate was 40.4% [q:D0e7e7902cd] against a peer median of 38.2% [q:Da4b39f7815], a gap of +2.3 pts [q:D4c614083d2]. The gap has narrowed a lot since its peak. The uncalibrated score is only 0.5 [q:Dbc823172e4].
- **Why it's not seasonality:** Peer bands move together with the season. B2 moved apart from them. The gap was +6.9 pts [q:D837717b7df] in week 35 and has stayed positive in every week since.
- **Adverse-selection verdict:** Yes, as a pattern. The contract rate rose while our spread did not move. B2 spread was 6.6% [q:D1b66f39508] in week 45 against a peer median of 6.6% [q:D12753180e3], a gap of +0.0 pts [q:D42f631cea3]. Sellers appear to accept more because the homes are worth less than our model thinks. About 5.7% [q:Da15ef17c74] of contracts sit above the peer-expected rate.
- **Impact:** This is a scenario estimate, sample-scale. It runs from $164K [q:D69f095ffd0] to $492K [q:D1bfe4e7ed5], with a midpoint of $328K [q:Dc6e052072f]. That is 3 bps [q:D8859acb6f8] to 8 bps [q:D81644df68b] of portfolio contribution margin, with a midpoint of 5 bps [q:D8f2e765ae8]. It is unconfirmed until resales and is ranked on its midpoint. The exposure is $288.5M [q:Df908b6b18e]. Each 100 bps of erosion would cost $2.9M [q:D0be2d1d569].
- **Action / owner:** Pricing should widen the spread or add in-person inspection for B2, and audit the model valuation inputs.

### M05 — renovation cost drift
- **What changed:** Renovation overrun in M05 reached 21.6% [q:D428e0d48ae] in week 45. The peer median was 0.2% [q:D8c8772d4fa], and the gap to peers was +5.8 pts [q:Dd3f684356b]. The overrun began to climb around week 37, when it was 13.1% [q:Da7cbf2ac84]. The uncalibrated score is 5.3 [q:D9a5602728c].
- **Why it's not seasonality:** Peer markets stayed low. Their median was 3.9% [q:D9af48c03e2] in week 37 and 0.2% [q:D5c121577c8] in week 44. M05 kept rising, so the move is specific to M05.
- **Adverse-selection verdict:** Not applicable. This is a renovation cost-estimate problem, not a seller-acceptance problem.
- **Impact:** Measured from current leading-indicator data, sample-scale, at $255K [q:D3770031067]. That is 3 bps [q:D0f037211c7] of portfolio contribution margin and 20 bps [q:Dc9457bc484] of M05 margin. The exposure is $124.7M [q:D9c98237df7]. Each 100 bps of erosion would cost $1.2M [q:D3f611c2fc8].
- **Action / owner:** Renovation should re-baseline M05 renovation estimates and require in-person assessment.

## What we're not sure about
- **B2 alert strength:** The B2 gap has faded toward peers and its score is low. The alert still fires, but we can't tell whether the pressure is easing or just harder to see. The dollar range is a scenario until resales confirm it. A cohort check would help once resales arrive.
- **B2 cause:** Our spread was flat against peers throughout, which fits adverse selection. We have not examined the valuation inputs, so we can't say why the model overvalues these homes.
- **M05 gap definition:** The tool's gap figures do not equal the scope value minus the peer median shown beside them, and I have not reconciled the difference. The alert showed a gap of +4.7 pts [q:Ddcb630750b] and a score of 4.4 [q:D3c27a7bf61]. The week 45 comparison shows a larger gap and score, so the drift is not easing.
- **Watch items and abstentions:** The alert tool returned none. We make no claim about other markets or bands.

---
_Dollar figures are sample-scale ($ at the synthetic portfolio's ~$1.6B/yr). Drift scores are uncalibrated scores, not probabilities that an alert is real. Status: valid._

## Citations

| ref | what | value | source queries |
|---|---|---|---|
| `q:D9b7cca71ce` | contract_rate B2 gap vs peers week 37 | +13.7 pts | Q3aa016583b, Qd448a13898 |
| `q:D10f014e7f3` | contract_rate B2 gap vs peers week 38 | +14.2 pts | Q3aa016583b, Qd448a13898 |
| `q:D0e7e7902cd` | contract_rate B2 week 45 | 40.4% | Q3aa016583b, Qd448a13898 |
| `q:Da4b39f7815` | contract_rate peers of B2 week 45 | 38.2% | Q3aa016583b, Qd448a13898 |
| `q:D4c614083d2` | contract_rate B2 gap vs peers week 45 | +2.3 pts | Q3aa016583b, Qd448a13898 |
| `q:Dbc823172e4` | contract_rate B2 drift score week 45 | 0.5 | Q3aa016583b, Qd448a13898 |
| `q:D837717b7df` | contract_rate B2 gap vs peers week 35 | +6.9 pts | Q3aa016583b, Qd448a13898 |
| `q:D1b66f39508` | avg_spread_pct B2 week 45 | 6.6% | Qa4a2d4e43e, Qf4208c099e |
| `q:D12753180e3` | avg_spread_pct peers of B2 week 45 | 6.6% | Qa4a2d4e43e, Qf4208c099e |
| `q:D42f631cea3` | avg_spread_pct B2 gap vs peers week 45 | +0.0 pts | Qa4a2d4e43e, Qf4208c099e |
| `q:Da15ef17c74` | A2527e410 B2 excess_share | 5.7% | Q219dda118c, Q443997a8d9, Q4ed0eff2be, Q7699a5997d, Q79966a57df, Q92c8a6f1ce, Q9a919a43ba, Qc28f4cfc17, Qdfb0e29e20, Qf7383b66c0, Qfc26c433ff |
| `q:D69f095ffd0` | A2527e410 usd_low | $164K | Q219dda118c, Q3aa016583b, Q443997a8d9, Q4ed0eff2be, Q7699a5997d, Q79966a57df, Q92c8a6f1ce, Q9a919a43ba, Qc28f4cfc17, Qdfb0e29e20, Qf7383b66c0, Qfc26c433ff |
| `q:D1bfe4e7ed5` | A2527e410 usd_high | $492K | Q219dda118c, Q3aa016583b, Q443997a8d9, Q4ed0eff2be, Q7699a5997d, Q79966a57df, Q92c8a6f1ce, Q9a919a43ba, Qc28f4cfc17, Qdfb0e29e20, Qf7383b66c0, Qfc26c433ff |
| `q:Dc6e052072f` | A2527e410 usd_mid | $328K | Q219dda118c, Q3aa016583b, Q443997a8d9, Q4ed0eff2be, Q7699a5997d, Q79966a57df, Q92c8a6f1ce, Q9a919a43ba, Qc28f4cfc17, Qdfb0e29e20, Qf7383b66c0, Qfc26c433ff |
| `q:D8859acb6f8` | A2527e410 portfolio_cm_bps_low | 3 bps | Q219dda118c, Q3aa016583b, Q443997a8d9, Q4ed0eff2be, Q7699a5997d, Q79966a57df, Q92c8a6f1ce, Q9a919a43ba, Qc28f4cfc17, Qdfb0e29e20, Qf7383b66c0, Qfc26c433ff |
| `q:D81644df68b` | A2527e410 portfolio_cm_bps_high | 8 bps | Q219dda118c, Q3aa016583b, Q443997a8d9, Q4ed0eff2be, Q7699a5997d, Q79966a57df, Q92c8a6f1ce, Q9a919a43ba, Qc28f4cfc17, Qdfb0e29e20, Qf7383b66c0, Qfc26c433ff |
| `q:D8f2e765ae8` | A2527e410 portfolio_cm_bps_mid | 5 bps | Q219dda118c, Q3aa016583b, Q443997a8d9, Q4ed0eff2be, Q7699a5997d, Q79966a57df, Q92c8a6f1ce, Q9a919a43ba, Qc28f4cfc17, Qdfb0e29e20, Qf7383b66c0, Qfc26c433ff |
| `q:Df908b6b18e` | A2527e410 exposure_usd | $288.5M | Q219dda118c, Q3aa016583b, Q443997a8d9, Q4ed0eff2be, Q7699a5997d, Q79966a57df, Q92c8a6f1ce, Q9a919a43ba, Qc28f4cfc17, Qdfb0e29e20, Qf7383b66c0, Qfc26c433ff |
| `q:D0be2d1d569` | A2527e410 usd_per_100bps | $2.9M | Q219dda118c, Q3aa016583b, Q443997a8d9, Q4ed0eff2be, Q7699a5997d, Q79966a57df, Q92c8a6f1ce, Q9a919a43ba, Qc28f4cfc17, Qdfb0e29e20, Qf7383b66c0, Qfc26c433ff |
| `q:D428e0d48ae` | reno_overrun_pct M05 week 45 | 21.6% | Qca7a341d62, Qe83367e8ae |
| `q:D8c8772d4fa` | reno_overrun_pct peers of M05 week 45 | 0.2% | Qca7a341d62, Qe83367e8ae |
| `q:Dd3f684356b` | reno_overrun_pct M05 gap vs peers week 45 | +5.8 pts | Qca7a341d62, Qe83367e8ae |
| `q:Da7cbf2ac84` | reno_overrun_pct M05 week 37 | 13.1% | Qca7a341d62, Qe83367e8ae |
| `q:D9a5602728c` | reno_overrun_pct M05 drift score week 45 | 5.3 | Qca7a341d62, Qe83367e8ae |
| `q:D9af48c03e2` | reno_overrun_pct peers of M05 week 37 | 3.9% | Qca7a341d62, Qe83367e8ae |
| `q:D5c121577c8` | reno_overrun_pct peers of M05 week 44 | 0.2% | Qca7a341d62, Qe83367e8ae |
| `q:D3770031067` | Ab238fd5c usd_mid | $255K | Q3ce14038af, Q5df4ff3cc9, Q81a305fbf8, Q92c8a6f1ce, Qaa4209a6db, Qd1270909d3 |
| `q:D0f037211c7` | Ab238fd5c portfolio_cm_bps_mid | 3 bps | Q3ce14038af, Q5df4ff3cc9, Q81a305fbf8, Q92c8a6f1ce, Qaa4209a6db, Qd1270909d3 |
| `q:Dc9457bc484` | Ab238fd5c scope_bps_mid | 20 bps | Q3ce14038af, Q5df4ff3cc9, Q81a305fbf8, Q92c8a6f1ce, Qaa4209a6db, Qd1270909d3 |
| `q:D9c98237df7` | Ab238fd5c exposure_usd | $124.7M | Q3ce14038af, Q5df4ff3cc9, Q81a305fbf8, Q92c8a6f1ce, Qaa4209a6db, Qd1270909d3 |
| `q:D3f611c2fc8` | Ab238fd5c usd_per_100bps | $1.2M | Q3ce14038af, Q5df4ff3cc9, Q81a305fbf8, Q92c8a6f1ce, Qaa4209a6db, Qd1270909d3 |
| `q:Ddcb630750b` | Ab238fd5c gap vs peers | +4.7 pts | Qd1270909d3 |
| `q:D3c27a7bf61` | Ab238fd5c score | 4.4 | Qd1270909d3 |

