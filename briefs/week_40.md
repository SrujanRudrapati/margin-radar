Synthetic data — not Opendoor data.

# Margin Radar weekly brief — week 40 (week of 2025-10-13)

_Synthetic iBuyer portfolio (injected-scenario run). Every number cites a governed fact `[q:ID]`; see Citations at the end._

## Top actions

### B2 — adverse selection (scenario estimate)
- **What changed:** The B2 contract rate rose to 46.6% [q:D81eb477cc6] in week 40. Peers were at 38.5% [q:D32352c2a1d], a gap of +8.2 pts [q:D67db236025]. The gap began opening in week 35. The uncalibrated drift score is 1.8 [q:Df1f11b4127]. The share of contracts above the peer-expected rate is 17.5% [q:Ddaf443f411].
- **Why it's not seasonality:** Peer medians moved with the season. They were 32.0% [q:Dee15294bcf] in week 35 and 41.4% [q:D130f4ef5d3] in week 39. B2 stayed above peers throughout. The gap is noisy. It was +14.2 pts [q:D2f71651b36] in week 38 and +5.5 pts [q:D37c65708f3] in week 39. The direction has been consistent since week 35, but the size is not steady, and the score is modest.
- **Adverse-selection verdict:** Yes, probable. Conversion rose while our spread did not change. B2 spread was 6.6% [q:D3cd5be75cf] against a peer median of 6.6% [q:D6a690a0148], a gap of +0.0 pts [q:Dc32519e453]. This pattern fits sellers accepting because the homes are worth less than our model thinks. It is not confirmed.
- **Impact:** This is a scenario estimate, sample-scale. It is unconfirmed until resales, and it is ranked on its midpoint. The range is $444K [q:Dad0f537dd7] to $1.3M [q:D9a151e7a68], with a midpoint of $888K [q:D51a5835f9f]. That is 8 bps [q:Dc71f85eeb0] to 24 bps [q:D729860b50b] of portfolio contribution margin, with a midpoint of 16 bps [q:Df51c23682f]. As a sensitivity, not a loss: on the $253.4M [q:D958f373c21] exposure, each hundred basis points of margin erosion would cost $2.5M [q:D56f0dfd248].
- **Action / owner:** Pricing should widen the B2 spread or add in-person inspection. Pricing should also audit the model valuation inputs.

### M05 — renovation cost drift
- **What changed:** The M05 renovation overrun reached 18.1% [q:Dc0ade0d9ae] in week 40. The peer median was 5.6% [q:D27257cee86], a gap of +11.7 pts [q:D935256294f]. The uncalibrated drift score is 4.4 [q:Dc322951ac0]. The overrun was 5.1% [q:D2cb889ceca] in week 33 and has climbed since.
- **Why it's not seasonality:** Peers stayed in a narrow range, from 3.0% [q:D4382a25d1a] to 5.6% [q:D27257cee86]. M05 moved from 7.1% [q:D71206e31db] in week 35 to 13.1% [q:D74cd07dfde] in week 37. It has kept rising since.
- **Adverse-selection verdict:** Not applicable. This is a cost problem, not a seller-conversion problem.
- **Impact:** Measured from current leading-indicator data, sample-scale. It is not confirmed by resales. The impact is $758K [q:D150c3216ae], which is 59 bps [q:Ddf2db77d4d] of scope margin and 8 bps [q:Db58fe56dd4] of portfolio contribution margin. As a sensitivity, not a loss: on the $127.9M [q:D700f13ad0a] exposure, each hundred basis points of margin erosion would cost $1.3M [q:D8b330e87bb].
- **Action / owner:** Renovation should re-baseline M05 renovation estimates and require an in-person assessment.

## What we're not sure about
- **B2 is a scenario, not a measured loss.** It stays unconfirmed until the affected homes resell. The weekly gap swings a lot, and the drift score of 1.8 [q:Df1f11b4127] is modest. I checked spread, but I did not test other explanations for the higher contract rate.
- **M05 cause is unknown.** The data shows the overrun but not why it happened. I did not look at the scope of work, the vendors or the mix of homes.
- **Watch items and abstentions:** The alert feed lists no watch items and no abstentions. I made no cohort-level margin claims.

---
_Dollar figures are sample-scale ($ at the synthetic portfolio's ~$1.6B/yr). Drift scores are uncalibrated scores, not probabilities that an alert is real. Status: valid._

## Citations

| ref | what | value | source queries |
|---|---|---|---|
| `q:D81eb477cc6` | contract_rate B2 week 40 | 46.6% | Q528e719f4c, Qed68e5ad5b |
| `q:D32352c2a1d` | contract_rate peers of B2 week 40 | 38.5% | Q528e719f4c, Qed68e5ad5b |
| `q:D67db236025` | contract_rate B2 gap vs peers week 40 | +8.2 pts | Q528e719f4c, Qed68e5ad5b |
| `q:Df1f11b4127` | contract_rate B2 drift score week 40 | 1.8 | Q528e719f4c, Qed68e5ad5b |
| `q:Ddaf443f411` | A2527e410 B2 excess_share | 17.5% | Q26df8135ce, Q3bccb8c72c, Q3ff4ca2ccb, Q4a07620e54, Q5c18db4f82, Q98f8209faa, Q9c4f89261e, Qaaafba5f28, Qb38341b581, Qe864db5adf, Qfd25fcb222 |
| `q:Dee15294bcf` | contract_rate peers of B2 week 35 | 32.0% | Q528e719f4c, Qed68e5ad5b |
| `q:D130f4ef5d3` | contract_rate peers of B2 week 39 | 41.4% | Q528e719f4c, Qed68e5ad5b |
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
| `q:D958f373c21` | A2527e410 exposure_usd | $253.4M | Q26df8135ce, Q3bccb8c72c, Q3ff4ca2ccb, Q4a07620e54, Q528e719f4c, Q5c18db4f82, Q98f8209faa, Q9c4f89261e, Qaaafba5f28, Qb38341b581, Qe864db5adf, Qfd25fcb222 |
| `q:D56f0dfd248` | A2527e410 usd_per_100bps | $2.5M | Q26df8135ce, Q3bccb8c72c, Q3ff4ca2ccb, Q4a07620e54, Q528e719f4c, Q5c18db4f82, Q98f8209faa, Q9c4f89261e, Qaaafba5f28, Qb38341b581, Qe864db5adf, Qfd25fcb222 |
| `q:Dc0ade0d9ae` | reno_overrun_pct M05 week 40 | 18.1% | Q7a0b8a692f, Qf0ba93ea02 |
| `q:D27257cee86` | reno_overrun_pct peers of M05 week 40 | 5.6% | Q7a0b8a692f, Qf0ba93ea02 |
| `q:D935256294f` | reno_overrun_pct M05 gap vs peers week 40 | +11.7 pts | Q7a0b8a692f, Qf0ba93ea02 |
| `q:Dc322951ac0` | reno_overrun_pct M05 drift score week 40 | 4.4 | Q7a0b8a692f, Qf0ba93ea02 |
| `q:D2cb889ceca` | reno_overrun_pct M05 week 33 | 5.1% | Q7a0b8a692f, Qf0ba93ea02 |
| `q:D4382a25d1a` | reno_overrun_pct peers of M05 week 36 | 3.0% | Q7a0b8a692f, Qf0ba93ea02 |
| `q:D71206e31db` | reno_overrun_pct M05 week 35 | 7.1% | Q7a0b8a692f, Qf0ba93ea02 |
| `q:D74cd07dfde` | reno_overrun_pct M05 week 37 | 13.1% | Q7a0b8a692f, Qf0ba93ea02 |
| `q:D150c3216ae` | Ab238fd5c usd_mid | $758K | Q5a4892b584, Q8488b62824, Qaaafba5f28, Qb9c16469c2, Qc6b10a3419, Qf0ba93ea02 |
| `q:Ddf2db77d4d` | Ab238fd5c scope_bps_mid | 59 bps | Q5a4892b584, Q8488b62824, Qaaafba5f28, Qb9c16469c2, Qc6b10a3419, Qf0ba93ea02 |
| `q:Db58fe56dd4` | Ab238fd5c portfolio_cm_bps_mid | 8 bps | Q5a4892b584, Q8488b62824, Qaaafba5f28, Qb9c16469c2, Qc6b10a3419, Qf0ba93ea02 |
| `q:D700f13ad0a` | Ab238fd5c exposure_usd | $127.9M | Q5a4892b584, Q8488b62824, Qaaafba5f28, Qb9c16469c2, Qc6b10a3419, Qf0ba93ea02 |
| `q:D8b330e87bb` | Ab238fd5c usd_per_100bps | $1.3M | Q5a4892b584, Q8488b62824, Qaaafba5f28, Qb9c16469c2, Qc6b10a3419, Qf0ba93ea02 |

