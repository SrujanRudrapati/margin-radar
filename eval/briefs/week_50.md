Synthetic data — not Opendoor data.

# Margin Radar weekly brief — week 50 (week of 2025-12-22)

_Synthetic iBuyer portfolio (injected-scenario run). Every number cites a governed fact `[q:ID]`; see Citations at the end._

## Top actions

### B2 — adverse selection
- **What changed:** The contract rate in B2 is above peers and has stayed there since onset in week 35. In week 50 it was 45.8% [q:D9d32a7ff18] against a peer median of 38.0% [q:Df0d49c8fa7], a gap of +6.4 pts [q:Df53d9cf2db]. The uncalibrated score is 1.4 [q:D6512e9bc44]. The share of contracts above the peer-expected rate is 13.9% [q:Dad218742fb].
- **Why it's not seasonality:** Peer bands share the same weeks, and their median moved with the season, from 33.8% [q:D7097162ca4] in week 38 to 38.0% [q:Df0d49c8fa7] in week 50. B2 stayed above the peer median in every week of the window. The gap was +14.2 pts [q:D19c497c334] in week 38 and +6.4 pts [q:Df53d9cf2db] in week 50. It narrowed in the middle weeks, for example +0.5 pts [q:Dffd45edb4c] in week 42, then widened again.
- **Adverse-selection verdict:** Yes. B2's average spread was 6.6% [q:D89f99519a8] against a peer median of 6.6% [q:D9ee58f664a], a gap of +0.0 pts [q:Db852945e06]. Sellers are accepting more often without any change in our spread. That pattern fits homes being worth less than our model thinks.
- **Impact:** This is a scenario estimate, sample-scale, and it is unconfirmed until resales. It is ranked on its midpoint. The range is $534K [q:D48e86149e3] to $1.6M [q:D60fe52f673], with a midpoint of $1.1M [q:D86ed2d5eda]. That is 6 bps [q:D8e415b2339] to 18 bps [q:Dffdec06a7b] of portfolio contribution margin, with a midpoint of 12 bps [q:D2b6137d495]. The exposure is $383.4M [q:Db1dfa95370]. Each 100 bps of erosion would cost $3.8M [q:De7e68bed08].
- **Action / owner:** Pricing should widen the spread or add in-person inspection for B2, and should audit the model's valuation inputs.

### M05 — renovation cost drift
- **What changed:** Renovation overruns in M05 are far above peers. In week 50 the overrun was 21.0% [q:D8563d6d349] against a peer median of 4.1% [q:D38a2df190d], a gap of +17.8 pts [q:D29d9953c9c]. The uncalibrated score is 4.7 [q:D3198c9ae84]. Onset was in week 37.
- **Why it's not seasonality:** The peer median stayed low throughout, for example 4.5% [q:D5bf61e5698] in week 38 and 4.1% [q:D38a2df190d] in week 50. M05 rose from 15.0% [q:D977097faa7] to 21.0% [q:D8563d6d349] over the same weeks. The gap was +5.7 pts [q:D8ba60355b4] in week 38 and has stayed wide since.
- **Adverse-selection verdict:** Not applicable. This is a cost-estimation problem on the renovation side. It is not a conversion signal.
- **Impact:** Measured from current leading-indicator data, sample-scale, at $764K [q:Db64571b692]. That is 68 bps [q:D0901381d8d] of scope contribution margin and 11 bps [q:D00d8bc58f7] of portfolio contribution margin. The exposure is $111.9M [q:D2d82c1da75]. Each 100 bps of erosion would cost $1.1M [q:D57b91e8ec4].
- **Action / owner:** Renovation should re-baseline renovation estimates in M05 and require an in-person assessment.

## What we're not sure about
- The B2 impact is a scenario, not a result. Resales have not yet confirmed it. The scenario assumes a shortfall of 1.0% [q:D18c3c9fc27] to 3.0% [q:Dfe3b9c3f7e].
- The B2 score is low at 1.4 [q:D6512e9bc44], and the gap has swung from week to week. Treat the signal as persistent but noisy. I did not check whether it is concentrated in particular markets.
- For M05 I did not look at which renovation categories drive the overruns, so I can't say what a re-baseline should change.
- `get_alerts` returned no watch items and no abstentions this week.

---
_Dollar figures are sample-scale ($ at the synthetic portfolio's ~$1.6B/yr). Drift scores are uncalibrated scores, not probabilities that an alert is real. Status: valid._

## Citations

| ref | what | value | source queries |
|---|---|---|---|
| `q:D9d32a7ff18` | contract_rate B2 week 50 | 45.8% | Q30c2a42417, Qa92d4f9124 |
| `q:Df0d49c8fa7` | contract_rate peers of B2 week 50 | 38.0% | Q30c2a42417, Qa92d4f9124 |
| `q:Df53d9cf2db` | contract_rate B2 gap vs peers week 50 | +6.4 pts | Q30c2a42417, Qa92d4f9124 |
| `q:D6512e9bc44` | contract_rate B2 drift score week 50 | 1.4 | Q30c2a42417, Qa92d4f9124 |
| `q:Dad218742fb` | A2527e410 B2 excess_share | 13.9% | Q279a573b28, Q2cc677c21a, Q63c8a0de9e, Q785ad7a675, Q82a851814b, Q93458669df, Qae0b742a90, Qb71b1817b8, Qc1ae6647e5, Qd97cbd2840, Qe2d947ebde |
| `q:D7097162ca4` | contract_rate peers of B2 week 38 | 33.8% | Q30c2a42417, Qa92d4f9124 |
| `q:D19c497c334` | contract_rate B2 gap vs peers week 38 | +14.2 pts | Q30c2a42417, Qa92d4f9124 |
| `q:Dffd45edb4c` | contract_rate B2 gap vs peers week 42 | +0.5 pts | Q30c2a42417, Qa92d4f9124 |
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
| `q:D3198c9ae84` | reno_overrun_pct M05 drift score week 50 | 4.7 | Qafd4b61ffe, Qd0aa3ef4e2 |
| `q:D5bf61e5698` | reno_overrun_pct peers of M05 week 38 | 4.5% | Qafd4b61ffe, Qd0aa3ef4e2 |
| `q:D977097faa7` | reno_overrun_pct M05 week 38 | 15.0% | Qafd4b61ffe, Qd0aa3ef4e2 |
| `q:D8ba60355b4` | reno_overrun_pct M05 gap vs peers week 38 | +5.7 pts | Qafd4b61ffe, Qd0aa3ef4e2 |
| `q:Db64571b692` | Ab238fd5c usd_low | $764K | Q2c8ba57ad2, Q5e47649f78, Q82a851814b, Q89e3658bec, Q9006a8c988, Qd0aa3ef4e2 |
| `q:D0901381d8d` | Ab238fd5c scope_bps_low | 68 bps | Q2c8ba57ad2, Q5e47649f78, Q82a851814b, Q89e3658bec, Q9006a8c988, Qd0aa3ef4e2 |
| `q:D00d8bc58f7` | Ab238fd5c portfolio_cm_bps_low | 11 bps | Q2c8ba57ad2, Q5e47649f78, Q82a851814b, Q89e3658bec, Q9006a8c988, Qd0aa3ef4e2 |
| `q:D2d82c1da75` | Ab238fd5c exposure_usd | $111.9M | Q2c8ba57ad2, Q5e47649f78, Q82a851814b, Q89e3658bec, Q9006a8c988, Qd0aa3ef4e2 |
| `q:D57b91e8ec4` | Ab238fd5c usd_per_100bps | $1.1M | Q2c8ba57ad2, Q5e47649f78, Q82a851814b, Q89e3658bec, Q9006a8c988, Qd0aa3ef4e2 |
| `q:D18c3c9fc27` | planning shortfall low (user-given) | 1.0% | Qc1ae6647e5 |
| `q:Dfe3b9c3f7e` | planning shortfall high (user-given) | 3.0% | Qc1ae6647e5 |

