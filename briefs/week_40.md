Synthetic data — not Opendoor data.

# Margin Radar weekly brief — week 40 (week of 2025-10-13)

_Synthetic iBuyer portfolio (injected-scenario run). Every number cites a governed fact `[q:ID]`; see Citations at the end._

## Top actions

### B2 — adverse selection (scenario estimate)

- **What changed:** The B2 contract rate rose to 46.6% [q:D81eb477cc6] in week 40. The peer median was 38.5% [q:D32352c2a1d], so the gap is +8.2 pts [q:D67db236025]. The uncalibrated drift score is 1.9 [q:Df1f11b4127]. The share of contracts above the peer-expected rate is 17.5% [q:Ddaf443f411]. The drift began in week 35.
- **Why it's not seasonality:** Peer bands move together with the season, and B2 moved apart from them. In week 33 B2 was below peers at -3.6 pts [q:Db903d2050b]. In week 35 it was above them at +6.9 pts [q:D5b2cc4fc17]. The gap then reached +14.2 pts [q:D2f71651b36] in week 38. It narrowed to +5.5 pts [q:D37c65708f3] in week 39 and widened again in week 40. The gap is volatile, but it has stayed positive since week 34.
- **Adverse-selection verdict:** Yes, this fits the pattern. Conversion rose while our spread did not change. B2 average spread was 6.6% [q:D3cd5be75cf] against a peer median of 6.6% [q:D6a690a0148], a gap of +0.0 pts [q:Dc32519e453]. Sellers appear to be accepting more because the homes may be worth less than our model thinks. Resales have not confirmed this.
- **Impact:** This is a scenario estimate, sample-scale. It is unconfirmed until resales, and it is ranked on its midpoint.
  - Range: $444K [q:Dad0f537dd7] to $1.3M [q:D9a151e7a68], with a midpoint of $888K [q:D51a5835f9f].
  - In bps of portfolio contribution margin: 8 bps [q:Dc71f85eeb0] to 24 bps [q:D729860b50b], with a midpoint of 16 bps [q:Df51c23682f].
  - Within B2 alone the range is 18 bps [q:Dd092a07017] to 53 bps [q:D38b4b895ae].
  - The assumed shortfall runs from 1.0% [q:D12868fb46b] to 3.0% [q:Dc05bb4c888] on an exposure of $253.4M [q:D958f373c21].
  - As a sensitivity, each 100 bps of erosion would cost $2.5M [q:D56f0dfd248].
- **Action / owner:** Pricing should widen the B2 spread or add in-person inspection. Pricing should also audit the model valuation inputs for B2.

## What we're not sure about

- **Margin not yet observed:** The impact is a scenario estimate. No resale data confirms that B2 homes were overpriced. The range depends on the assumed shortfall.
- **Noisy signal:** The drift score is uncalibrated and is not a probability that the alert is real. The weekly gap swings widely, including the week 39 dip. A single week is not enough to size the problem.
- **Cause not isolated:** Flat spread and higher conversion point to adverse selection. I did not check other explanations, such as a lead-mix change or a competitor pulling back. I cannot rule them out.
- **Watch items and abstentions:** The alerts tool returned no watch items and no abstentions this week. I made no other peer comparisons beyond contract rate and spread for B2.

---
_Dollar figures are sample-scale ($ at the synthetic portfolio's ~$1.6B/yr). Drift scores are uncalibrated scores, not probabilities that an alert is real. Status: valid._

## Citations

| ref | what | value | source queries |
|---|---|---|---|
| `q:D81eb477cc6` | contract_rate B2 week 40 | 46.6% | Q528e719f4c, Qed68e5ad5b |
| `q:D32352c2a1d` | contract_rate peers of B2 week 40 | 38.5% | Q528e719f4c, Qed68e5ad5b |
| `q:D67db236025` | contract_rate B2 gap vs peers week 40 | +8.2 pts | Q528e719f4c, Qed68e5ad5b |
| `q:Df1f11b4127` | contract_rate B2 drift score week 40 | 1.9 | Q528e719f4c, Qed68e5ad5b |
| `q:Ddaf443f411` | A2527e410 B2 excess_share | 17.5% | Q26df8135ce, Q3bccb8c72c, Q3ff4ca2ccb, Q4a07620e54, Q5c18db4f82, Q98f8209faa, Q9c4f89261e, Qaaafba5f28, Qb38341b581, Qe864db5adf, Qfd25fcb222 |
| `q:Db903d2050b` | contract_rate B2 gap vs peers week 33 | -3.6 pts | Q528e719f4c, Qed68e5ad5b |
| `q:D5b2cc4fc17` | contract_rate B2 gap vs peers week 35 | +6.9 pts | Q528e719f4c, Qed68e5ad5b |
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
| `q:Dd092a07017` | A2527e410 scope_bps_low | 18 bps | Q26df8135ce, Q3bccb8c72c, Q3ff4ca2ccb, Q4a07620e54, Q528e719f4c, Q5c18db4f82, Q98f8209faa, Q9c4f89261e, Qaaafba5f28, Qb38341b581, Qe864db5adf, Qfd25fcb222 |
| `q:D38b4b895ae` | A2527e410 scope_bps_high | 53 bps | Q26df8135ce, Q3bccb8c72c, Q3ff4ca2ccb, Q4a07620e54, Q528e719f4c, Q5c18db4f82, Q98f8209faa, Q9c4f89261e, Qaaafba5f28, Qb38341b581, Qe864db5adf, Qfd25fcb222 |
| `q:D12868fb46b` | planning shortfall low (user-given) | 1.0% | Qb38341b581 |
| `q:Dc05bb4c888` | planning shortfall high (user-given) | 3.0% | Qb38341b581 |
| `q:D958f373c21` | A2527e410 exposure_usd | $253.4M | Q26df8135ce, Q3bccb8c72c, Q3ff4ca2ccb, Q4a07620e54, Q528e719f4c, Q5c18db4f82, Q98f8209faa, Q9c4f89261e, Qaaafba5f28, Qb38341b581, Qe864db5adf, Qfd25fcb222 |
| `q:D56f0dfd248` | A2527e410 usd_per_100bps | $2.5M | Q26df8135ce, Q3bccb8c72c, Q3ff4ca2ccb, Q4a07620e54, Q528e719f4c, Q5c18db4f82, Q98f8209faa, Q9c4f89261e, Qaaafba5f28, Qb38341b581, Qe864db5adf, Qfd25fcb222 |

