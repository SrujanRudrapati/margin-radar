Synthetic data — not Opendoor data.

# Margin Radar weekly brief — week 50 (week of 2025-12-22)

_Synthetic iBuyer portfolio (injected-scenario run). Every number cites a governed fact `[q:ID]`; see Citations at the end._

## Top actions

### B2 — adverse selection
- **What changed:** The contract rate in B2 is above peers. In week 50 it was 45.8% [q:D9d32a7ff18] against a peer median of 38.0% [q:Df0d49c8fa7], a gap of +6.4 pts [q:Df53d9cf2db]. The uncalibrated drift score is 1.4 [q:Df2e7e9d95e]. The share of contracts above the peer-expected rate is 13.9% [q:Dad218742fb].
- **Why it's not seasonality:** Peer bands share the same weeks, so seasonality moves them together. B2 stayed above peers in every week from week 38 to week 50. The gap was +14.2 pts [q:D19c497c334] in week 38 and narrowed to +2.3 pts [q:D77f8eb6bd5] in week 45. It has since widened again, to +7.3 pts [q:D7f67dc30a8] in week 49 and +6.4 pts [q:Df53d9cf2db] in week 50.
- **Adverse-selection verdict:** Yes. Conversion rose while our spread did not change. In week 50, B2 spread was 6.6% [q:D89f99519a8] against a peer median of 6.6% [q:D9ee58f664a], a gap of +0.0 pts [q:Db852945e06]. That pattern fits sellers accepting more because the homes are worth less than our model thinks.
- **Impact:** This is a scenario estimate, sample-scale. It is unconfirmed until resales and is ranked on its midpoint. The range is $534K [q:D48e86149e3] to $1.6M [q:D60fe52f673], with a midpoint of $1.1M [q:D86ed2d5eda]. In portfolio contribution margin that is 6 bps [q:D8e415b2339] to 18 bps [q:Dffdec06a7b], with a midpoint of 12 bps [q:D2b6137d495]. The exposure is $383.4M [q:Db1dfa95370]. As a sensitivity, each 100 bps of erosion would cost $3.8M [q:De7e68bed08].
- **Action / owner:** Pricing should widen the spread or add in-person inspection for B2, and audit the model valuation inputs.

### M05 — renovation cost drift
- **What changed:** Renovation overrun in M05 was 21.0% [q:D8563d6d349] in week 50 against a peer median of 4.1% [q:D38a2df190d]. That is a gap of +17.8 pts [q:D29d9953c9c]. The uncalibrated drift score is 3.5 [q:D73c327d465].
- **Why it's not seasonality:** Peer markets stayed low and moved together. M05 sat far above them in every week shown. The gap was +5.7 pts [q:D8ba60355b4] in week 38 and reached +18.0 pts [q:D3679a94935] in week 42. It has stayed wide since.
- **Adverse-selection verdict:** Not applicable. This is a cost overrun on renovation estimates, not a conversion signal.
- **Impact:** This is measured from current leading-indicator data, sample-scale. It comes to $764K [q:Dd7f88ac229], or 68 bps [q:D92f00ee6a7] of M05 contribution margin and 11 bps [q:D19048eeebc] of portfolio contribution margin. The exposure is $111.9M [q:Dc7d7263b35]. As a sensitivity, each 100 bps of erosion would cost $1.1M [q:D38af8d38a6].
- **Action / owner:** Renovation should re-baseline renovation estimates in M05 and require in-person assessment.

## What we're not sure about
- **B2 is a scenario, not a loss.** No resales confirm it yet. The range rests on assumed shortfalls of 1.0% [q:D18c3c9fc27] to 3.0% [q:Dfe3b9c3f7e], so the true cost could fall outside it. The drift score of 1.4 [q:Df2e7e9d95e] is modest. The gap has also swung from week to week.
- **B2 spread check.** I checked spread only over the most recent weeks. I did not check it back to the week 35 onset.
- **M05 cause.** The data show that overruns are high and persistent. They do not show why. I can't say whether the cause is estimating error, scope creep or vendor cost.
- **Watch items and abstentions.** The alert feed lists none. I have not looked at other markets or bands beyond the scopes in these actions.

---
_Dollar figures are sample-scale ($ at the synthetic portfolio's ~$1.6B/yr). Drift scores are uncalibrated scores, not probabilities that an alert is real. Status: valid._

## Citations

| ref | what | value | source queries |
|---|---|---|---|
| `q:D9d32a7ff18` | contract_rate B2 week 50 | 45.8% | Q30c2a42417, Qa92d4f9124 |
| `q:Df0d49c8fa7` | contract_rate peers of B2 week 50 | 38.0% | Q30c2a42417, Qa92d4f9124 |
| `q:Df53d9cf2db` | contract_rate B2 gap vs peers week 50 | +6.4 pts | Q30c2a42417, Qa92d4f9124 |
| `q:Df2e7e9d95e` | contract_rate B2 drift score week 50 | 1.4 | Q30c2a42417 |
| `q:Dad218742fb` | A2527e410 B2 excess_share | 13.9% | Q279a573b28, Q2cc677c21a, Q63c8a0de9e, Q785ad7a675, Q82a851814b, Q93458669df, Qae0b742a90, Qb71b1817b8, Qc1ae6647e5, Qd97cbd2840, Qe2d947ebde |
| `q:D19c497c334` | contract_rate B2 gap vs peers week 38 | +14.2 pts | Q30c2a42417, Qa92d4f9124 |
| `q:D77f8eb6bd5` | contract_rate B2 gap vs peers week 45 | +2.3 pts | Q30c2a42417, Qa92d4f9124 |
| `q:D7f67dc30a8` | contract_rate B2 gap vs peers week 49 | +7.3 pts | Q30c2a42417, Qa92d4f9124 |
| `q:D89f99519a8` | avg_spread_pct B2 week 50 | 6.6% | Q7ef540a349, Q86c85b8dc2 |
| `q:D9ee58f664a` | avg_spread_pct peers of B2 week 50 | 6.6% | Q7ef540a349, Q86c85b8dc2 |
| `q:Db852945e06` | avg_spread_pct B2 gap vs peers week 50 | +0.0 pts | Q7ef540a349, Q86c85b8dc2 |
| `q:D48e86149e3` | A2527e410 usd_low | $534K | Q279a573b28, Q2cc677c21a, Q30c2a42417, Q63c8a0de9e, Q785ad7a675, Q82a851814b, Q93458669df, Qae0b742a90, Qb71b1817b8, Qc1ae6647e5, Qd97cbd2840, Qe2d947ebde |
| `q:D60fe52f673` | A2527e410 usd_high | $1.6M | Q279a573b28, Q2cc677c21a, Q30c2a42417, Q63c8a0de9e, Q785ad7a675, Q82a851814b, Q93458669df, Qae0b742a90, Qb71b1817b8, Qc1ae6647e5, Qd97cbd2840, Qe2d947ebde |
| `q:D86ed2d5eda` | A2527e410 usd_mid | $1.1M | Q279a573b28, Q2cc677c21a, Q30c2a42417, Q63c8a0de9e, Q785ad7a675, Q82a851814b, Q93458669df, Qae0b742a90, Qb71b1817b8, Qc1ae6647e5, Qd97cbd2840, Qe2d947ebde |
| `q:D8e415b2339` | A2527e410 portfolio_cm_bps_low | 6 bps | Q279a573b28, Q2cc677c21a, Q30c2a42417, Q63c8a0de9e, Q785ad7a675, Q82a851814b, Q93458669df, Qae0b742a90, Qb71b1817b8, Qc1ae6647e5, Qd97cbd2840, Qe2d947ebde |
| `q:Dffdec06a7b` | A2527e410 portfolio_cm_bps_high | 18 bps | Q279a573b28, Q2cc677c21a, Q30c2a42417, Q63c8a0de9e, Q785ad7a675, Q82a851814b, Q93458669df, Qae0b742a90, Qb71b1817b8, Qc1ae6647e5, Qd97cbd2840, Qe2d947ebde |
| `q:D2b6137d495` | A2527e410 portfolio_cm_bps_mid | 12 bps | Q279a573b28, Q2cc677c21a, Q30c2a42417, Q63c8a0de9e, Q785ad7a675, Q82a851814b, Q93458669df, Qae0b742a90, Qb71b1817b8, Qc1ae6647e5, Qd97cbd2840, Qe2d947ebde |
| `q:Db1dfa95370` | A2527e410 exposure_usd | $383.4M | Q279a573b28, Q2cc677c21a, Q30c2a42417, Q63c8a0de9e, Q785ad7a675, Q82a851814b, Q93458669df, Qae0b742a90, Qb71b1817b8, Qc1ae6647e5, Qd97cbd2840, Qe2d947ebde |
| `q:De7e68bed08` | A2527e410 usd_per_100bps | $3.8M | Q279a573b28, Q2cc677c21a, Q30c2a42417, Q63c8a0de9e, Q785ad7a675, Q82a851814b, Q93458669df, Qae0b742a90, Qb71b1817b8, Qc1ae6647e5, Qd97cbd2840, Qe2d947ebde |
| `q:D8563d6d349` | reno_overrun_pct M05 week 50 | 21.0% | Qafd4b61ffe, Qd0aa3ef4e2 |
| `q:D38a2df190d` | reno_overrun_pct peers of M05 week 50 | 4.1% | Qafd4b61ffe, Qd0aa3ef4e2 |
| `q:D29d9953c9c` | reno_overrun_pct M05 gap vs peers week 50 | +17.8 pts | Qafd4b61ffe, Qd0aa3ef4e2 |
| `q:D73c327d465` | reno_overrun_pct M05 drift score week 50 | 3.5 | Qbef2c3e379 |
| `q:D8ba60355b4` | reno_overrun_pct M05 gap vs peers week 38 | +5.7 pts | Qafd4b61ffe, Qd0aa3ef4e2 |
| `q:D3679a94935` | reno_overrun_pct M05 gap vs peers week 42 | +18.0 pts | Qafd4b61ffe, Qd0aa3ef4e2 |
| `q:Dd7f88ac229` | Ab238fd5c usd_mid | $764K | Q2c8ba57ad2, Q5e47649f78, Q82a851814b, Q89e3658bec, Q9006a8c988, Qbef2c3e379, Qd0aa3ef4e2 |
| `q:D92f00ee6a7` | Ab238fd5c scope_bps_mid | 68 bps | Q2c8ba57ad2, Q5e47649f78, Q82a851814b, Q89e3658bec, Q9006a8c988, Qbef2c3e379, Qd0aa3ef4e2 |
| `q:D19048eeebc` | Ab238fd5c portfolio_cm_bps_mid | 11 bps | Q2c8ba57ad2, Q5e47649f78, Q82a851814b, Q89e3658bec, Q9006a8c988, Qbef2c3e379, Qd0aa3ef4e2 |
| `q:Dc7d7263b35` | Ab238fd5c exposure_usd | $111.9M | Q2c8ba57ad2, Q5e47649f78, Q82a851814b, Q89e3658bec, Q9006a8c988, Qbef2c3e379, Qd0aa3ef4e2 |
| `q:D38af8d38a6` | Ab238fd5c usd_per_100bps | $1.1M | Q2c8ba57ad2, Q5e47649f78, Q82a851814b, Q89e3658bec, Q9006a8c988, Qbef2c3e379, Qd0aa3ef4e2 |
| `q:D18c3c9fc27` | planning shortfall low (user-given) | 1.0% | Qc1ae6647e5 |
| `q:Dfe3b9c3f7e` | planning shortfall high (user-given) | 3.0% | Qc1ae6647e5 |

