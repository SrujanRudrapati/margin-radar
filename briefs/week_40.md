Synthetic data — not Opendoor data.

# Margin Radar weekly brief — week 40 (week of 2025-10-13)

_Synthetic iBuyer portfolio (injected-scenario run). Every number cites a governed fact `[q:ID]`; see Citations at the end._

## Top actions

### B2 — adverse selection (contract rate)
- **What changed:** The contract rate in B2 rose to 46.6% [q:D81eb477cc6] in week 40. The peer median was 38.5% [q:D32352c2a1d], a gap of +8.2 pts [q:D67db236025]. The drift score is 1.8 [q:Df1f11b4127], an uncalibrated score. The share of contracts above the peer-expected rate is 17.5% [q:Ddaf443f411]. Onset was week 35.
- **Why it's not seasonality:** Peers moved with the season and B2 moved away from them. In week 33 B2 was at -3.6 pts [q:Db903d2050b] against peers. The gap then widened to +13.7 pts [q:D5dd436fe8c] in week 37 and +14.2 pts [q:D2f71651b36] in week 38. It narrowed to +5.5 pts [q:D37c65708f3] in week 39 before widening again. The gap is persistent but noisy.
- **Adverse-selection verdict:** Yes, as a pattern. Conversion rose while our spread stayed level with peers. B2 spread was 6.6% [q:D3cd5be75cf] against a peer median of 6.6% [q:D6a690a0148], a gap of +0.0 pts [q:Dc32519e453]. That fits sellers accepting more because the homes are worth less than our model thinks. This is unconfirmed until resales.
- **Impact:** Scenario estimate, sample-scale, unconfirmed until resales and ranked on its midpoint. The range is $444K [q:Dad0f537dd7] to $1.3M [q:D9a151e7a68], with a midpoint of $888K [q:D51a5835f9f]. That is 8 bps [q:Dc71f85eeb0] to 24 bps [q:D729860b50b] of portfolio contribution margin, with a midpoint of 16 bps [q:Df51c23682f]. The scenario assumes a valuation shortfall of 1.0% [q:D12868fb46b] to 3.0% [q:Dc05bb4c888] on $253.4M [q:D958f373c21] of exposure. As a sensitivity, each 100 bps of erosion would cost $2.5M [q:D56f0dfd248].
- **Action / owner:** Pricing should widen the B2 spread or add in-person inspection, and audit the model's valuation inputs.

### M05 — renovation cost drift
- **What changed:** Renovation overrun in M05 reached 18.1% [q:Dc0ade0d9ae] in week 40. The peer median was 5.6% [q:D27257cee86], a gap of +11.7 pts [q:D935256294f]. The drift score is 4.4 [q:Dc322951ac0], an uncalibrated score. Onset was week 37.
- **Why it's not seasonality:** Peers stayed in a narrow band over recent weeks, from 3.0% [q:D4382a25d1a] to 5.6% [q:D27257cee86]. M05 climbed from 5.1% [q:D2cb889ceca] in week 33 to 13.1% [q:D74cd07dfde] in week 37, then kept rising.
- **Adverse-selection verdict:** Not applicable. This is a cost-estimate problem, not a conversion signal.
- **Impact:** Measured from current leading-indicator data, sample-scale: $758K [q:D150c3216ae]. That is 59 bps [q:Ddf2db77d4d] of M05 margin and 8 bps [q:Db58fe56dd4] of portfolio contribution margin, on $127.9M [q:D700f13ad0a] of exposure. As a sensitivity, each 100 bps of erosion would cost $1.3M [q:D8b330e87bb].
- **Action / owner:** Renovation should re-baseline M05 renovation estimates and require in-person assessment.

## What we're not sure about
- The B2 adverse-selection call rests on conversion rising without a spread change. It is not confirmed by resales, and the dollar impact is a scenario, not a loss. The drift score is modest, and the gap fell sharply in week 39 before recovering. We can't yet say whether the week 39 dip was noise or a real pause.
- For M05 we have not examined which renovation categories or vendors drive the overrun. We can't say whether it is a pricing-baseline error or an execution problem, and the recommended re-baseline assumes the former.
- No watch items or abstentions were raised this week. We did not test the resale side of either action, so margin impact is not yet visible in resale data.

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
| `q:Dc0ade0d9ae` | reno_overrun_pct M05 week 40 | 18.1% | Q7a0b8a692f, Qf0ba93ea02 |
| `q:D27257cee86` | reno_overrun_pct peers of M05 week 40 | 5.6% | Q7a0b8a692f, Qf0ba93ea02 |
| `q:D935256294f` | reno_overrun_pct M05 gap vs peers week 40 | +11.7 pts | Q7a0b8a692f, Qf0ba93ea02 |
| `q:Dc322951ac0` | reno_overrun_pct M05 drift score week 40 | 4.4 | Q7a0b8a692f, Qf0ba93ea02 |
| `q:D4382a25d1a` | reno_overrun_pct peers of M05 week 36 | 3.0% | Q7a0b8a692f, Qf0ba93ea02 |
| `q:D2cb889ceca` | reno_overrun_pct M05 week 33 | 5.1% | Q7a0b8a692f, Qf0ba93ea02 |
| `q:D74cd07dfde` | reno_overrun_pct M05 week 37 | 13.1% | Q7a0b8a692f, Qf0ba93ea02 |
| `q:D150c3216ae` | Ab238fd5c usd_mid | $758K | Q5a4892b584, Q8488b62824, Qaaafba5f28, Qb9c16469c2, Qc6b10a3419, Qf0ba93ea02 |
| `q:Ddf2db77d4d` | Ab238fd5c scope_bps_mid | 59 bps | Q5a4892b584, Q8488b62824, Qaaafba5f28, Qb9c16469c2, Qc6b10a3419, Qf0ba93ea02 |
| `q:Db58fe56dd4` | Ab238fd5c portfolio_cm_bps_mid | 8 bps | Q5a4892b584, Q8488b62824, Qaaafba5f28, Qb9c16469c2, Qc6b10a3419, Qf0ba93ea02 |
| `q:D700f13ad0a` | Ab238fd5c exposure_usd | $127.9M | Q5a4892b584, Q8488b62824, Qaaafba5f28, Qb9c16469c2, Qc6b10a3419, Qf0ba93ea02 |
| `q:D8b330e87bb` | Ab238fd5c usd_per_100bps | $1.3M | Q5a4892b584, Q8488b62824, Qaaafba5f28, Qb9c16469c2, Qc6b10a3419, Qf0ba93ea02 |

