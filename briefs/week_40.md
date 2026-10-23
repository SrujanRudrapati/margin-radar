Synthetic data — not Opendoor data.

# Margin Radar weekly brief — week 40 (week of 2025-10-13)

_Synthetic iBuyer portfolio (injected-scenario run). Every number cites a governed fact `[q:ID]`; see Citations at the end._

## Top actions

### B2 — adverse selection (contract rate)

- **What changed:** The B2 contract rate rose to 46.6% [q:D81eb477cc6] in week 40. The peer median was 38.5% [q:D32352c2a1d], a gap of +8.2 pts [q:D67db236025]. The gap opened in week 35 (2025-09-08). The uncalibrated drift score is 1.9 [q:D0d500ed625]. The share of contracts above the peer-expected rate is 17.5% [q:Ddaf443f411].
- **Why it's not seasonality:** Peer bands share the same weeks, so a seasonal move would lift them together. The peer median moved between 32.0% [q:Dee15294bcf] and 41.4% [q:D130f4ef5d3], while B2 stayed above it in every week from week 35 onward. The gap was -3.6 pts [q:Db903d2050b] in week 33. It was +13.7 pts [q:D5dd436fe8c] in week 37 and +14.2 pts [q:D2f71651b36] in week 38. It narrowed to +5.5 pts [q:D37c65708f3] in week 39 and widened again in week 40. The gap is noisy week to week, but it has stayed positive since onset.
- **Adverse-selection verdict:** Yes, on the leading-indicator pattern. Conversion rose while our spread did not change. B2 spread was 6.6% [q:D3cd5be75cf] against a 6.6% [q:D6a690a0148] peer median, a gap of +0.0 pts [q:Dc32519e453]. That fits sellers accepting more often because the homes are worth less than our model assumes. Resales have not confirmed it.
- **Impact:** This is a scenario estimate, sample-scale, and it is unconfirmed until resales. It is ranked on its midpoint.
  - The range is $444K [q:Dad0f537dd7] to $1.3M [q:D9a151e7a68], with a midpoint of $888K [q:D51a5835f9f].
  - In portfolio contribution margin, that is 8 bps [q:Dc71f85eeb0] to 24 bps [q:D729860b50b], with a midpoint of 16 bps [q:Df51c23682f].
  - The scenario assumes a resale shortfall of 1.0% [q:D12868fb46b] to 3.0% [q:Dc05bb4c888] on an exposure of $253.4M [q:D958f373c21].
  - Sensitivity: each 100 bps of erosion would cost $2.5M [q:D56f0dfd248]. This is a sensitivity, not a forecast loss.
- **Action / owner:** Pricing should widen the B2 spread or add in-person inspection. Pricing should also audit the model valuation inputs for B2.

## What we're not sure about

- **No resale confirmation:** The B2 impact is a scenario built on assumed shortfalls. Contribution margin shows up only when homes resell, so we can't say whether the loss is real or how large it is. The score is uncalibrated and is not a probability.
- **Noisy gap:** The week-to-week gap is uneven, and the week 39 dip shows that. The pattern is persistent but not smooth.
- **Cause not identified:** The spread comparison shows that price did not drive the conversion rise. It does not show whether the cause is model valuation inputs, condition information, or something else. The audit should settle that.
- **Scope limits:** The only action raised is at band level. I did not check whether the signal is concentrated in particular markets or payment types within B2.
- **Nothing else flagged:** The alert feed has no watch items and no abstentions this week.

---
_Dollar figures are sample-scale ($ at the synthetic portfolio's ~$1.6B/yr). Drift scores are uncalibrated scores, not probabilities that an alert is real. Status: valid._

## Citations

| ref | what | value | source queries |
|---|---|---|---|
| `q:D81eb477cc6` | contract_rate B2 week 40 | 46.6% | Q528e719f4c, Qed68e5ad5b |
| `q:D32352c2a1d` | contract_rate peers of B2 week 40 | 38.5% | Q528e719f4c, Qed68e5ad5b |
| `q:D67db236025` | contract_rate B2 gap vs peers week 40 | +8.2 pts | Q528e719f4c, Qed68e5ad5b |
| `q:D0d500ed625` | contract_rate B2 drift score week 40 | 1.9 | Q528e719f4c |
| `q:Ddaf443f411` | A2527e410 B2 excess_share | 17.5% | Q26df8135ce, Q3bccb8c72c, Q3ff4ca2ccb, Q4a07620e54, Q5c18db4f82, Q98f8209faa, Q9c4f89261e, Qaaafba5f28, Qb38341b581, Qe864db5adf, Qfd25fcb222 |
| `q:Dee15294bcf` | contract_rate peers of B2 week 35 | 32.0% | Q528e719f4c, Qed68e5ad5b |
| `q:D130f4ef5d3` | contract_rate peers of B2 week 39 | 41.4% | Q528e719f4c, Qed68e5ad5b |
| `q:Db903d2050b` | contract_rate B2 gap vs peers week 33 | -3.6 pts | Q528e719f4c, Qed68e5ad5b |
| `q:D5dd436fe8c` | contract_rate B2 gap vs peers week 37 | +13.7 pts | Q528e719f4c, Qed68e5ad5b |
| `q:D2f71651b36` | contract_rate B2 gap vs peers week 38 | +14.2 pts | Q528e719f4c, Qed68e5ad5b |
| `q:D37c65708f3` | contract_rate B2 gap vs peers week 39 | +5.5 pts | Q528e719f4c, Qed68e5ad5b |
| `q:D3cd5be75cf` | avg_spread_pct B2 week 40 | 6.6% | Q9c7d016286, Q9d2719f728 |
| `q:D6a690a0148` | avg_spread_pct peers of B2 week 40 | 6.6% | Q9c7d016286, Q9d2719f728 |
| `q:Dc32519e453` | avg_spread_pct B2 gap vs peers week 40 | +0.0 pts | Q9c7d016286, Q9d2719f728 |
| `q:Dad0f537dd7` | A2527e410 usd_low | $444K | Q26df8135ce, Q3bccb8c72c, Q3ff4ca2ccb, Q4a07620e54, Q528e719f4c, Q5c18db4f82, Q98f8209faa, Q9c4f89261e, Qaaafba5f28, Qb38341b581, Qe864db5adf, Qfd25fcb222 |
| `q:D9a151e7a68` | A2527e410 usd_high | $1.3M | Q26df8135ce, Q3bccb8c72c, Q3ff4ca2ccb, Q4a07620e54, Q528e719f4c, Q5c18db4f82, Q98f8209faa, Q9c4f89261e, Qaaafba5f28, Qb38341b581, Qe864db5adf, Qfd25fcb222 |
| `q:D51a5835f9f` | A2527e410 usd_mid | $888K | Q26df8135ce, Q3bccb8c72c, Q3ff4ca2ccb, Q4a07620e54, Q528e719f4c, Q5c18db4f82, Q98f8209faa, Q9c4f89261e, Qaaafba5f28, Qb38341b581, Qe864db5adf, Qfd25fcb222 |
| `q:Dc71f85eeb0` | A2527e410 portfolio_cm_bps_low | 8 bps | Q26df8135ce, Q3bccb8c72c, Q3ff4ca2ccb, Q4a07620e54, Q528e719f4c, Q5c18db4f82, Q98f8209faa, Q9c4f89261e, Qaaafba5f28, Qb38341b581, Qe864db5adf, Qfd25fcb222 |
| `q:D729860b50b` | A2527e410 portfolio_cm_bps_high | 24 bps | Q26df8135ce, Q3bccb8c72c, Q3ff4ca2ccb, Q4a07620e54, Q528e719f4c, Q5c18db4f82, Q98f8209faa, Q9c4f89261e, Qaaafba5f28, Qb38341b581, Qe864db5adf, Qfd25fcb222 |
| `q:Df51c23682f` | A2527e410 portfolio_cm_bps_mid | 16 bps | Q26df8135ce, Q3bccb8c72c, Q3ff4ca2ccb, Q4a07620e54, Q528e719f4c, Q5c18db4f82, Q98f8209faa, Q9c4f89261e, Qaaafba5f28, Qb38341b581, Qe864db5adf, Qfd25fcb222 |
| `q:D12868fb46b` | planning shortfall low (user-given) | 1.0% | Qb38341b581 |
| `q:Dc05bb4c888` | planning shortfall high (user-given) | 3.0% | Qb38341b581 |
| `q:D958f373c21` | A2527e410 exposure_usd | $253.4M | Q26df8135ce, Q3bccb8c72c, Q3ff4ca2ccb, Q4a07620e54, Q528e719f4c, Q5c18db4f82, Q98f8209faa, Q9c4f89261e, Qaaafba5f28, Qb38341b581, Qe864db5adf, Qfd25fcb222 |
| `q:D56f0dfd248` | A2527e410 usd_per_100bps | $2.5M | Q26df8135ce, Q3bccb8c72c, Q3ff4ca2ccb, Q4a07620e54, Q528e719f4c, Q5c18db4f82, Q98f8209faa, Q9c4f89261e, Qaaafba5f28, Qb38341b581, Qe864db5adf, Qfd25fcb222 |

