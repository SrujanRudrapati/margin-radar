Synthetic data — not Opendoor data.

# Margin Radar weekly brief — week 45 (week of 2025-11-17)

_Synthetic iBuyer portfolio (injected-scenario run). Every number cites a governed fact `[q:ID]`; see Citations at the end._

## Top actions

### M05 — renovation cost drift
- **What changed:** Renovation overrun in M05 rose sharply from onset in week 37. It is now 21.6% [q:D428e0d48ae] against a peer median of 0.2% [q:D8c8772d4fa]. That is a gap of +19.3 pts [q:Dd3f684356b]. The uncalibrated score is 4.4 [q:Dabe6b85b58].
- **Why it's not seasonality:** Peer markets stayed low and drifted down, from 3.9% [q:D9af48c03e2] in week 37 to 0.2% [q:D8c8772d4fa] now. M05 moved the other way, from 13.1% [q:Da7cbf2ac84] to 21.6% [q:D428e0d48ae]. A seasonal pattern would move peers and M05 together.
- **Adverse-selection verdict:** Not applicable. This is a cost-estimate problem on renovation, not a seller-acceptance problem.
- **Impact:** The impact is measured from current leading-indicator data. It is $1.0M [q:D04c127bede] sample-scale, or 84 bps [q:D0cf0676ff6] of scope margin. That is 13 bps [q:D12f9039c77] of portfolio contribution margin. Each 100 bps of erosion would cost $1.2M [q:D5fba52219d] on the $124.7M [q:Db0fa6def1d] exposure.
- **Action / owner:** Re-baseline renovation estimates in M05 and require in-person assessment. Owner: Renovation.

### B2 — adverse selection
- **What changed:** The B2 contract rate rose against peers. It is 40.4% [q:D0e7e7902cd] against a peer median of 38.2% [q:Da4b39f7815], a gap of +2.3 pts [q:D4c614083d2]. The uncalibrated score is 0.5 [q:D86326674b6]. The share of contracts above the peer-expected rate is 5.7% [q:Da15ef17c74].
- **Why it's not seasonality:** Peer contract rates moved with the season, from 32.9% [q:D7250055096] in week 37 to 38.2% [q:Da4b39f7815] now. B2 sat above peers for most of the window. The gap peaked at +14.2 pts [q:D10f014e7f3] in week 38 and has narrowed since. The current signal is modest.
- **Adverse-selection verdict:** Yes, as a pattern. Conversion rose while B2 spread stayed level with peers, at 6.6% [q:D1b66f39508] against 6.6% [q:D12753180e3]. That is consistent with sellers accepting because homes are worth less than our model thinks. It is not proven.
- **Impact:** This is a scenario estimate, sample-scale. The range is $164K [q:D69f095ffd0] to $328K [q:Dc6e052072f] at the midpoint to $492K [q:D1bfe4e7ed5]. It is unconfirmed until resales and is ranked on its midpoint. In bps of portfolio contribution margin, the range is 3 bps [q:D8859acb6f8] to 8 bps [q:D81644df68b], with a midpoint of 5 bps [q:D8f2e765ae8]. The assumed shortfall runs from 1.0% [q:D42af78a82e] to 3.0% [q:D39e338d6c0]. Each 100 bps of erosion would cost $2.9M [q:D0be2d1d569] on the $288.5M [q:Df908b6b18e] exposure.
- **Action / owner:** Widen spread or add in-person inspection for B2, and audit the model valuation inputs. Owner: Pricing.

## What we're not sure about
- **B2 is unconfirmed.** The B2 dollar figures are scenario assumptions, not realised losses. Resales will confirm or reject them. The score is low, and the gap has narrowed from its peak. We cannot say whether the pattern is fading or persisting.
- **M05 magnitude.** The $1.0M [q:D04c127bede] is measured from current indicators. Realised margin will only show up at resale, so the final figure may differ.
- **M05 cause.** We cannot say why M05 overruns diverged. The data does not separate scope creep, contractor pricing and estimate error.
- **Watch items and abstentions.** The alert feed lists no watch items and no abstentions this week.

---
_Dollar figures are sample-scale ($ at the synthetic portfolio's ~$1.6B/yr). Drift scores are uncalibrated scores, not probabilities that an alert is real. Status: valid._

## Citations

| ref | what | value | source queries |
|---|---|---|---|
| `q:D428e0d48ae` | reno_overrun_pct M05 week 45 | 21.6% | Qca7a341d62, Qe83367e8ae |
| `q:D8c8772d4fa` | reno_overrun_pct peers of M05 week 45 | 0.2% | Qca7a341d62, Qe83367e8ae |
| `q:Dd3f684356b` | reno_overrun_pct M05 gap vs peers week 45 | +19.3 pts | Qca7a341d62, Qe83367e8ae |
| `q:Dabe6b85b58` | reno_overrun_pct M05 drift score week 45 | 4.4 | Qd1270909d3 |
| `q:D9af48c03e2` | reno_overrun_pct peers of M05 week 37 | 3.9% | Qca7a341d62, Qe83367e8ae |
| `q:Da7cbf2ac84` | reno_overrun_pct M05 week 37 | 13.1% | Qca7a341d62, Qe83367e8ae |
| `q:D04c127bede` | Ab238fd5c usd_mid | $1.0M | Q3ce14038af, Q5df4ff3cc9, Q81a305fbf8, Q92c8a6f1ce, Qaa4209a6db, Qca7a341d62, Qd1270909d3 |
| `q:D0cf0676ff6` | Ab238fd5c scope_bps_mid | 84 bps | Q3ce14038af, Q5df4ff3cc9, Q81a305fbf8, Q92c8a6f1ce, Qaa4209a6db, Qca7a341d62, Qd1270909d3 |
| `q:D12f9039c77` | Ab238fd5c portfolio_cm_bps_mid | 13 bps | Q3ce14038af, Q5df4ff3cc9, Q81a305fbf8, Q92c8a6f1ce, Qaa4209a6db, Qca7a341d62, Qd1270909d3 |
| `q:D5fba52219d` | Ab238fd5c usd_per_100bps | $1.2M | Q3ce14038af, Q5df4ff3cc9, Q81a305fbf8, Q92c8a6f1ce, Qaa4209a6db, Qca7a341d62, Qd1270909d3 |
| `q:Db0fa6def1d` | Ab238fd5c exposure_usd | $124.7M | Q3ce14038af, Q5df4ff3cc9, Q81a305fbf8, Q92c8a6f1ce, Qaa4209a6db, Qca7a341d62, Qd1270909d3 |
| `q:D0e7e7902cd` | contract_rate B2 week 45 | 40.4% | Q3aa016583b, Qd448a13898 |
| `q:Da4b39f7815` | contract_rate peers of B2 week 45 | 38.2% | Q3aa016583b, Qd448a13898 |
| `q:D4c614083d2` | contract_rate B2 gap vs peers week 45 | +2.3 pts | Q3aa016583b, Qd448a13898 |
| `q:D86326674b6` | contract_rate B2 drift score week 45 | 0.5 | Q3aa016583b |
| `q:Da15ef17c74` | A2527e410 B2 excess_share | 5.7% | Q219dda118c, Q443997a8d9, Q4ed0eff2be, Q7699a5997d, Q79966a57df, Q92c8a6f1ce, Q9a919a43ba, Qc28f4cfc17, Qdfb0e29e20, Qf7383b66c0, Qfc26c433ff |
| `q:D7250055096` | contract_rate peers of B2 week 37 | 32.9% | Q3aa016583b, Qd448a13898 |
| `q:D10f014e7f3` | contract_rate B2 gap vs peers week 38 | +14.2 pts | Q3aa016583b, Qd448a13898 |
| `q:D1b66f39508` | avg_spread_pct B2 week 45 | 6.6% | Qa4a2d4e43e, Qf4208c099e |
| `q:D12753180e3` | avg_spread_pct peers of B2 week 45 | 6.6% | Qa4a2d4e43e, Qf4208c099e |
| `q:D69f095ffd0` | A2527e410 usd_low | $164K | Q219dda118c, Q3aa016583b, Q443997a8d9, Q4ed0eff2be, Q7699a5997d, Q79966a57df, Q92c8a6f1ce, Q9a919a43ba, Qc28f4cfc17, Qdfb0e29e20, Qf7383b66c0, Qfc26c433ff |
| `q:Dc6e052072f` | A2527e410 usd_mid | $328K | Q219dda118c, Q3aa016583b, Q443997a8d9, Q4ed0eff2be, Q7699a5997d, Q79966a57df, Q92c8a6f1ce, Q9a919a43ba, Qc28f4cfc17, Qdfb0e29e20, Qf7383b66c0, Qfc26c433ff |
| `q:D1bfe4e7ed5` | A2527e410 usd_high | $492K | Q219dda118c, Q3aa016583b, Q443997a8d9, Q4ed0eff2be, Q7699a5997d, Q79966a57df, Q92c8a6f1ce, Q9a919a43ba, Qc28f4cfc17, Qdfb0e29e20, Qf7383b66c0, Qfc26c433ff |
| `q:D8859acb6f8` | A2527e410 portfolio_cm_bps_low | 3 bps | Q219dda118c, Q3aa016583b, Q443997a8d9, Q4ed0eff2be, Q7699a5997d, Q79966a57df, Q92c8a6f1ce, Q9a919a43ba, Qc28f4cfc17, Qdfb0e29e20, Qf7383b66c0, Qfc26c433ff |
| `q:D81644df68b` | A2527e410 portfolio_cm_bps_high | 8 bps | Q219dda118c, Q3aa016583b, Q443997a8d9, Q4ed0eff2be, Q7699a5997d, Q79966a57df, Q92c8a6f1ce, Q9a919a43ba, Qc28f4cfc17, Qdfb0e29e20, Qf7383b66c0, Qfc26c433ff |
| `q:D8f2e765ae8` | A2527e410 portfolio_cm_bps_mid | 5 bps | Q219dda118c, Q3aa016583b, Q443997a8d9, Q4ed0eff2be, Q7699a5997d, Q79966a57df, Q92c8a6f1ce, Q9a919a43ba, Qc28f4cfc17, Qdfb0e29e20, Qf7383b66c0, Qfc26c433ff |
| `q:D42af78a82e` | planning shortfall low (user-given) | 1.0% | Q443997a8d9 |
| `q:D39e338d6c0` | planning shortfall high (user-given) | 3.0% | Q443997a8d9 |
| `q:D0be2d1d569` | A2527e410 usd_per_100bps | $2.9M | Q219dda118c, Q3aa016583b, Q443997a8d9, Q4ed0eff2be, Q7699a5997d, Q79966a57df, Q92c8a6f1ce, Q9a919a43ba, Qc28f4cfc17, Qdfb0e29e20, Qf7383b66c0, Qfc26c433ff |
| `q:Df908b6b18e` | A2527e410 exposure_usd | $288.5M | Q219dda118c, Q3aa016583b, Q443997a8d9, Q4ed0eff2be, Q7699a5997d, Q79966a57df, Q92c8a6f1ce, Q9a919a43ba, Qc28f4cfc17, Qdfb0e29e20, Qf7383b66c0, Qfc26c433ff |

