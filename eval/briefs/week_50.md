Synthetic data — not Opendoor data.

# Margin Radar weekly brief — week 50 (week of 2025-12-22)

_Synthetic iBuyer portfolio (injected-scenario run). Every number cites a governed fact `[q:ID]`; see Citations at the end._

## Top actions

### B2 — adverse selection
- **What changed:** The contract rate in B2 is above peers. In week 50 it was 45.8% [q:D9d32a7ff18] against a peer median of 38.0% [q:Df0d49c8fa7], a gap of +6.4 pts [q:Df53d9cf2db]. The gap began in week 35. The uncalibrated drift score is 1.4 [q:D6512e9bc44], which is modest.
- **Why it's not seasonality:** Peer bands moved with the season, and B2 stayed above them. The gap was +14.2 pts [q:D19c497c334] in week 38 and fell to +2.3 pts [q:D77f8eb6bd5] in week 45. It then widened again to +7.3 pts [q:D7f67dc30a8] in week 49.
- **Adverse-selection verdict:** Yes, as a scenario. B2's average spread matches peers, at 6.6% [q:D89f99519a8] against 6.6% [q:D9ee58f664a], with a gap of +0.0 pts [q:Db852945e06]. Conversion rose with no matching change in our spread. That pattern fits sellers accepting because the homes are worth less than our model thinks. The share of contracts above the peer-expected rate is 13.9% [q:Dad218742fb].
- **Impact:** Scenario estimate, sample-scale, and unconfirmed until resales. The range is $534K [q:D48e86149e3] to $1.6M [q:D60fe52f673], and the alert is ranked on its midpoint of $1.1M [q:D86ed2d5eda]. That is 6 bps [q:D8e415b2339] to 18 bps [q:Dffdec06a7b] of portfolio contribution margin, with a midpoint of 12 bps [q:D2b6137d495]. The exposure is $383.4M [q:Db1dfa95370]. Each 100 bps of erosion would cost $3.8M [q:De7e68bed08].
- **Action / owner:** Pricing should widen the B2 spread or add in-person inspection, and should audit the model's valuation inputs.

### M05 — renovation cost drift
- **What changed:** Renovation overrun in M05 is well above peers. In week 50 it was 21.0% [q:D8563d6d349] against a peer median of 4.1% [q:D38a2df190d]. The alert reports a gap of +4.0 pts [q:Dde6aaf15a4] and a score of 3.5 [q:Df3967bdee4]. The latest peer table shows +4.2 pts [q:D29d9953c9c] and a score of 3.2 [q:D3198c9ae84]. The drift began in week 37.
- **Why it's not seasonality:** Peer overruns stayed low through the period, for example 0.2% [q:D8927cf5408] in week 45. M05 stayed high, at 21.6% [q:D6ce23070b8] in the same week. The peer gap has been positive in every week shown, starting at +2.0 pts [q:D8ba60355b4] in week 38.
- **Adverse-selection verdict:** Not applicable. This is a cost-estimation issue, not a conversion issue.
- **Impact:** Sample-scale and measured from current leading-indicator data. The impact is $172K [q:Dad7339a50c], or 15 bps [q:Da7243b12e5] of scope margin and 2 bps [q:D35a5c81e32] of portfolio contribution margin. The exposure is $111.9M [q:D3b5a265f9e]. Each 100 bps of erosion would cost $1.1M [q:D1d746acb1d].
- **Action / owner:** Renovation should re-baseline M05 renovation estimates and require in-person assessment.

## What we're not sure about
- The B2 impact is a scenario, not a result. Resales will confirm or refute it. The B2 drift score is low, and the gap shrank for several weeks before it widened again.
- The B2 spread check covers only recent weeks. I did not test other explanations, such as a change in mix within the band.
- The M05 gap in the alert differs slightly from the latest peer table, and I can't say which is better. The gap column is not the plain difference between the scope and peer medians shown, so I'm treating it as the tool's own peer-weighted measure.
- The M05 impact is measured from leading indicators. It is not a realized margin loss.
- There are no watch items or abstentions this week.

---
_Dollar figures are sample-scale ($ at the synthetic portfolio's ~$1.6B/yr). Drift scores are uncalibrated scores, not probabilities that an alert is real. Status: valid._

## Citations

| ref | what | value | source queries |
|---|---|---|---|
| `q:D9d32a7ff18` | contract_rate B2 week 50 | 45.8% | Q30c2a42417, Qa92d4f9124 |
| `q:Df0d49c8fa7` | contract_rate peers of B2 week 50 | 38.0% | Q30c2a42417, Qa92d4f9124 |
| `q:Df53d9cf2db` | contract_rate B2 gap vs peers week 50 | +6.4 pts | Q30c2a42417, Qa92d4f9124 |
| `q:D6512e9bc44` | contract_rate B2 drift score week 50 | 1.4 | Q30c2a42417, Qa92d4f9124 |
| `q:D19c497c334` | contract_rate B2 gap vs peers week 38 | +14.2 pts | Q30c2a42417, Qa92d4f9124 |
| `q:D77f8eb6bd5` | contract_rate B2 gap vs peers week 45 | +2.3 pts | Q30c2a42417, Qa92d4f9124 |
| `q:D7f67dc30a8` | contract_rate B2 gap vs peers week 49 | +7.3 pts | Q30c2a42417, Qa92d4f9124 |
| `q:D89f99519a8` | avg_spread_pct B2 week 50 | 6.6% | Q7ef540a349, Q86c85b8dc2 |
| `q:D9ee58f664a` | avg_spread_pct peers of B2 week 50 | 6.6% | Q7ef540a349, Q86c85b8dc2 |
| `q:Db852945e06` | avg_spread_pct B2 gap vs peers week 50 | +0.0 pts | Q7ef540a349, Q86c85b8dc2 |
| `q:Dad218742fb` | A2527e410 B2 excess_share | 13.9% | Q279a573b28, Q2cc677c21a, Q63c8a0de9e, Q785ad7a675, Q82a851814b, Q93458669df, Qae0b742a90, Qb71b1817b8, Qc1ae6647e5, Qd97cbd2840, Qe2d947ebde |
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
| `q:Dde6aaf15a4` | Ab238fd5c gap vs peers | +4.0 pts | Qbef2c3e379 |
| `q:Df3967bdee4` | Ab238fd5c score | 3.5 | Qbef2c3e379 |
| `q:D29d9953c9c` | reno_overrun_pct M05 gap vs peers week 50 | +4.2 pts | Qafd4b61ffe, Qd0aa3ef4e2 |
| `q:D3198c9ae84` | reno_overrun_pct M05 drift score week 50 | 3.2 | Qafd4b61ffe, Qd0aa3ef4e2 |
| `q:D8927cf5408` | reno_overrun_pct peers of M05 week 45 | 0.2% | Qafd4b61ffe, Qd0aa3ef4e2 |
| `q:D6ce23070b8` | reno_overrun_pct M05 week 45 | 21.6% | Qafd4b61ffe, Qd0aa3ef4e2 |
| `q:D8ba60355b4` | reno_overrun_pct M05 gap vs peers week 38 | +2.0 pts | Qafd4b61ffe, Qd0aa3ef4e2 |
| `q:Dad7339a50c` | Ab238fd5c usd_low | $172K | Q2c8ba57ad2, Q5e47649f78, Q82a851814b, Q89e3658bec, Q9006a8c988, Qbef2c3e379 |
| `q:Da7243b12e5` | Ab238fd5c scope_bps_mid | 15 bps | Q2c8ba57ad2, Q5e47649f78, Q82a851814b, Q89e3658bec, Q9006a8c988, Qbef2c3e379 |
| `q:D35a5c81e32` | Ab238fd5c portfolio_cm_bps_mid | 2 bps | Q2c8ba57ad2, Q5e47649f78, Q82a851814b, Q89e3658bec, Q9006a8c988, Qbef2c3e379 |
| `q:D3b5a265f9e` | Ab238fd5c exposure_usd | $111.9M | Q2c8ba57ad2, Q5e47649f78, Q82a851814b, Q89e3658bec, Q9006a8c988, Qbef2c3e379 |
| `q:D1d746acb1d` | Ab238fd5c usd_per_100bps | $1.1M | Q2c8ba57ad2, Q5e47649f78, Q82a851814b, Q89e3658bec, Q9006a8c988, Qbef2c3e379 |

