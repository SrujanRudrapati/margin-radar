Synthetic data — not Opendoor data.

# Margin Radar weekly brief — week 60 (week of 2026-03-02)

_Synthetic iBuyer portfolio (injected-scenario run). Every number cites a governed fact `[q:ID]`; see Citations at the end._

## Top actions

### M05 — renovation cost drift
- **What changed:** The renovation overrun rate in M05 has stayed high since the onset in week 37 (2025-09-22). In week 60 it was 20.3% [q:D515d02cd77], against a peer median of 2.1% [q:D6ed91cb83b]. That is a gap of +18.9 pts [q:D87f2e23fd2]. The uncalibrated drift score is 2.8 [q:D0751e0ae06].
- **Why it's not seasonality:** Peers share the same weeks, so seasonal moves show up in them too. The peer median stayed low throughout, for example 4.1% [q:D7ee447ed50] in week 59. M05 stayed high, for example 18.2% [q:De16b896d3e] in week 59. The gap has been persistent, for example +23.3 pts [q:Dab2c75b9fd] in week 52. M05 moved apart from its peers, not with them. Week 57 has no peer median, so I can't give a gap for that week.
- **Adverse-selection verdict:** Not applicable. This is a cost-estimation problem on renovation, not a conversion signal. The alert gives no evidence of sellers accepting more because the homes are worth less than our model thinks.
- **Impact:** The impact basis is measured, not a scenario estimate. It comes from current leading-indicator data, not from resales. Sample-scale, it is $927K [q:D43a0059f66] on an exposure of $132.6M [q:Dfe8cd33e0b]. That is 70 bps [q:Dd0bb1dc276] of M05 margin and 11 bps [q:D7bace2e94d] of portfolio contribution margin. As a sensitivity, each 100 bps of erosion would cost $1.3M [q:De5bda263d5].
- **Action / owner:** Re-baseline renovation estimates in M05 and require an in-person assessment. The owner is Renovation.

## What we're not sure about
- The $927K [q:D43a0059f66] figure is measured from current leading indicators. It is not confirmed by resales, so realized margin could differ.
- I called only the peer comparison for this action. I did not check cohort bleed curves or other markets, so I can't say whether the drift has reached realized margin yet.
- Week 57 has no peer median, so the comparison has a gap there.
- The alert feed shows no watch items and no abstentions this week.

---
_Dollar figures are sample-scale ($ at the synthetic portfolio's ~$1.6B/yr). Drift scores are uncalibrated scores, not probabilities that an alert is real. Status: valid._

## Citations

| ref | what | value | source queries |
|---|---|---|---|
| `q:D515d02cd77` | reno_overrun_pct M05 week 60 | 20.3% | Q31a3760396, Qafdd15796e |
| `q:D6ed91cb83b` | reno_overrun_pct peers of M05 week 60 | 2.1% | Q31a3760396, Qafdd15796e |
| `q:D87f2e23fd2` | reno_overrun_pct M05 gap vs peers week 60 | +18.9 pts | Q31a3760396, Qafdd15796e |
| `q:D0751e0ae06` | reno_overrun_pct M05 drift score week 60 | 2.8 | Qb7da5afa49 |
| `q:D7ee447ed50` | reno_overrun_pct peers of M05 week 59 | 4.1% | Q31a3760396, Qafdd15796e |
| `q:De16b896d3e` | reno_overrun_pct M05 week 59 | 18.2% | Q31a3760396, Qafdd15796e |
| `q:Dab2c75b9fd` | reno_overrun_pct M05 gap vs peers week 52 | +23.3 pts | Q31a3760396, Qafdd15796e |
| `q:D43a0059f66` | Ab238fd5c usd_mid | $927K | Q1bdd2859c3, Q31a3760396, Q4272afac77, Q5a6a21638b, Qa55aa51545, Qb7da5afa49, Qda4afa7611 |
| `q:Dfe8cd33e0b` | Ab238fd5c exposure_usd | $132.6M | Q1bdd2859c3, Q31a3760396, Q4272afac77, Q5a6a21638b, Qa55aa51545, Qb7da5afa49, Qda4afa7611 |
| `q:Dd0bb1dc276` | Ab238fd5c scope_bps_mid | 70 bps | Q1bdd2859c3, Q31a3760396, Q4272afac77, Q5a6a21638b, Qa55aa51545, Qb7da5afa49, Qda4afa7611 |
| `q:D7bace2e94d` | Ab238fd5c portfolio_cm_bps_mid | 11 bps | Q1bdd2859c3, Q31a3760396, Q4272afac77, Q5a6a21638b, Qa55aa51545, Qb7da5afa49, Qda4afa7611 |
| `q:De5bda263d5` | Ab238fd5c usd_per_100bps | $1.3M | Q1bdd2859c3, Q31a3760396, Q4272afac77, Q5a6a21638b, Qa55aa51545, Qb7da5afa49, Qda4afa7611 |

