Synthetic data — not Opendoor data.

# Margin Radar weekly brief — week 60 (week of 2026-03-02)

_Synthetic iBuyer portfolio (injected-scenario run). Every number cites a governed fact `[q:ID]`; see Citations at the end._

## Top actions

### M05 — renovation cost drift

- **What changed:** Renovation overrun in M05 has run well above peers since onset in week 37 (2025-09-22). In week 60 it was 20.3% [q:D515d02cd77], against a peer median of 2.1% [q:D6ed91cb83b]. The tool reports the gap as +5.6 pts [q:D87f2e23fd2]. The uncalibrated drift score is 2.8 [q:D3d00c6c274]. It is a score, not a probability that the alert is real.
- **Why it's not seasonality:** Peers share the same weeks, so seasonal effects move them together. The peer median stayed low through the whole window, for example 4.0% [q:D4611a210cc] in week 48 and 4.1% [q:D7ee447ed50] in week 59. M05 stayed high throughout, for example 21.2% [q:D09a48ef8d7] in week 48 and 18.2% [q:De16b896d3e] in week 59. The gap persisted, from +4.9 pts [q:Db0ad5c3f9d] in week 48 to +6.1 pts [q:D116e7c945b] in week 55 and +5.6 pts [q:D87f2e23fd2] in week 60. M05 moved apart from its peers.
- **Adverse-selection verdict:** Not applicable. This is a cost-estimate problem on the renovation side. It is not a case of conversion rising without a matching change in our spread.
- **Impact:** The impact is measured from current leading-indicator data. It is not a scenario estimate, and it is not confirmed by resales. The sample-scale impact is $273K [q:D406975b0df]. That is 21 bps [q:Dafa02f9e9b] of M05 contribution margin and 3 bps [q:Df0a83fde20] of portfolio contribution margin. The exposure is $132.6M [q:D661ce1c1fb]. As a sensitivity, not a loss, each 100 bps of erosion would cost $1.3M [q:D0f2975026f].
- **Action / owner:** Re-baseline renovation estimates in M05 and require an in-person assessment. The owner is Renovation.

## What we're not sure about

- **Gap arithmetic:** The tool's reported gap does not equal the scope value minus the peer median on the same row. I have cited the gap as the tool gives it and have not tried to reconcile it. The likely cause is how peers are weighted, but I can't confirm that.
- **Missing peer data:** The peer median and gap are missing for week 57 (2026-02-09). That week is a gap in the peer comparison.
- **Measured, not realized:** The $273K [q:D406975b0df] is measured from current indicators. Final margin will only be known when the affected homes resell.
- **Watch items and abstentions:** The tool returned no watch items and no abstentions. It returned no other actions, so I'm reporting nothing on other markets.
- **Data source:** The data is synthetic, not Opendoor data.

---
_Dollar figures are sample-scale ($ at the synthetic portfolio's ~$1.6B/yr). Drift scores are uncalibrated scores, not probabilities that an alert is real. Status: valid._

## Citations

| ref | what | value | source queries |
|---|---|---|---|
| `q:D515d02cd77` | reno_overrun_pct M05 week 60 | 20.3% | Q31a3760396, Qafdd15796e |
| `q:D6ed91cb83b` | reno_overrun_pct peers of M05 week 60 | 2.1% | Q31a3760396, Qafdd15796e |
| `q:D87f2e23fd2` | reno_overrun_pct M05 gap vs peers week 60 | +5.6 pts | Q31a3760396, Qafdd15796e |
| `q:D3d00c6c274` | reno_overrun_pct M05 drift score week 60 | 2.8 | Q31a3760396, Qafdd15796e |
| `q:D4611a210cc` | reno_overrun_pct peers of M05 week 48 | 4.0% | Q31a3760396, Qafdd15796e |
| `q:D7ee447ed50` | reno_overrun_pct peers of M05 week 59 | 4.1% | Q31a3760396, Qafdd15796e |
| `q:D09a48ef8d7` | reno_overrun_pct M05 week 48 | 21.2% | Q31a3760396, Qafdd15796e |
| `q:De16b896d3e` | reno_overrun_pct M05 week 59 | 18.2% | Q31a3760396, Qafdd15796e |
| `q:Db0ad5c3f9d` | reno_overrun_pct M05 gap vs peers week 48 | +4.9 pts | Q31a3760396, Qafdd15796e |
| `q:D116e7c945b` | reno_overrun_pct M05 gap vs peers week 55 | +6.1 pts | Q31a3760396, Qafdd15796e |
| `q:D406975b0df` | Ab238fd5c usd_mid | $273K | Q1bdd2859c3, Q4272afac77, Q5a6a21638b, Qa55aa51545, Qb7da5afa49, Qda4afa7611 |
| `q:Dafa02f9e9b` | Ab238fd5c scope_bps_mid | 21 bps | Q1bdd2859c3, Q4272afac77, Q5a6a21638b, Qa55aa51545, Qb7da5afa49, Qda4afa7611 |
| `q:Df0a83fde20` | Ab238fd5c portfolio_cm_bps_mid | 3 bps | Q1bdd2859c3, Q4272afac77, Q5a6a21638b, Qa55aa51545, Qb7da5afa49, Qda4afa7611 |
| `q:D661ce1c1fb` | Ab238fd5c exposure_usd | $132.6M | Q1bdd2859c3, Q4272afac77, Q5a6a21638b, Qa55aa51545, Qb7da5afa49, Qda4afa7611 |
| `q:D0f2975026f` | Ab238fd5c usd_per_100bps | $1.3M | Q1bdd2859c3, Q4272afac77, Q5a6a21638b, Qa55aa51545, Qb7da5afa49, Qda4afa7611 |

