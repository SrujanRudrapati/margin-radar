Synthetic data — not Opendoor data.

# Margin Radar weekly brief — week 60 (week of 2026-03-02)

_Synthetic iBuyer portfolio (injected-scenario run). Every number cites a governed fact `[q:ID]`; see Citations at the end._

## Top actions

### M05 — renovation cost drift

- **What changed:** Renovation overrun in M05 has run well above peers since onset in week 37 (2025-09-22). In week 60 it was 20.3% [q:D515d02cd77] against a peer median of 2.1% [q:D6ed91cb83b]. That is a gap of +18.9 pts [q:D87f2e23fd2]. The uncalibrated drift score is 2.4 [q:D3d00c6c274].
- **Why it's not seasonality:** Peer markets share the same weeks, so seasonality would move them together. Peers stayed low, between 2.1% [q:D6ed91cb83b] and 5.2% [q:D52538a998a] in the weeks shown. M05 stayed high, from 18.2% [q:De16b896d3e] to 22.3% [q:D0a16d42df4]. The gap was +15.5 pts [q:D2d68cb4434] in week 56 and +13.7 pts [q:Dae09687598] in week 59. It then widened again in week 60. The gap has persisted for months, so this is drift and not a seasonal swing.
- **Adverse-selection verdict:** Not applicable. This is a cost overrun on renovation, not a conversion-versus-spread pattern on offers.
- **Impact:** The sample-scale impact is $927K [q:D1e26c93883], measured from current leading-indicator data. It is not confirmed by resales. That is 11 bps [q:Dce7c84f4f3] of portfolio contribution margin, or 70 bps [q:Db5917af930] of M05's own margin. The exposure is $132.6M [q:Dff04ae5db5]. As a sensitivity, each 100 bps of erosion would cost $1.3M [q:D5f648a24b9].
- **Action / owner:** Re-baseline renovation estimates in M05 and require in-person assessment. Owner: Renovation.

## What we're not sure about

- This is the only action returned. There are no watch items and no abstentions this week.
- The $927K [q:D1e26c93883] figure is a measured point estimate. The low, mid and high values are identical, so it carries no range. It reflects the overrun seen so far and does not forecast resale margin.
- The week 57 peer median was missing. I can't state a peer gap for that week.
- Week-to-week noise in M05 is visible, and the gap moved around between weeks. I can't say from this evidence whether the overrun is getting better or worse. It is clearly elevated.
- I did not look at the cohort bleed curve or at other metrics, so I can't say whether the overrun has yet reached realized contribution margin.

---
_Dollar figures are sample-scale ($ at the synthetic portfolio's ~$1.6B/yr). Drift scores are uncalibrated scores, not probabilities that an alert is real. Status: valid._

## Citations

| ref | what | value | source queries |
|---|---|---|---|
| `q:D515d02cd77` | reno_overrun_pct M05 week 60 | 20.3% | Q31a3760396, Qafdd15796e |
| `q:D6ed91cb83b` | reno_overrun_pct peers of M05 week 60 | 2.1% | Q31a3760396, Qafdd15796e |
| `q:D87f2e23fd2` | reno_overrun_pct M05 gap vs peers week 60 | +18.9 pts | Q31a3760396, Qafdd15796e |
| `q:D3d00c6c274` | reno_overrun_pct M05 drift score week 60 | 2.4 | Q31a3760396, Qafdd15796e |
| `q:D52538a998a` | reno_overrun_pct peers of M05 week 58 | 5.2% | Q31a3760396, Qafdd15796e |
| `q:De16b896d3e` | reno_overrun_pct M05 week 59 | 18.2% | Q31a3760396, Qafdd15796e |
| `q:D0a16d42df4` | reno_overrun_pct M05 week 56 | 22.3% | Q31a3760396, Qafdd15796e |
| `q:D2d68cb4434` | reno_overrun_pct M05 gap vs peers week 56 | +15.5 pts | Q31a3760396, Qafdd15796e |
| `q:Dae09687598` | reno_overrun_pct M05 gap vs peers week 59 | +13.7 pts | Q31a3760396, Qafdd15796e |
| `q:D1e26c93883` | Ab238fd5c usd_mid | $927K | Q1bdd2859c3, Q31a3760396, Q4272afac77, Q5a6a21638b, Qa55aa51545, Qda4afa7611 |
| `q:Dce7c84f4f3` | Ab238fd5c portfolio_cm_bps_mid | 11 bps | Q1bdd2859c3, Q31a3760396, Q4272afac77, Q5a6a21638b, Qa55aa51545, Qda4afa7611 |
| `q:Db5917af930` | Ab238fd5c scope_bps_mid | 70 bps | Q1bdd2859c3, Q31a3760396, Q4272afac77, Q5a6a21638b, Qa55aa51545, Qda4afa7611 |
| `q:Dff04ae5db5` | Ab238fd5c exposure_usd | $132.6M | Q1bdd2859c3, Q31a3760396, Q4272afac77, Q5a6a21638b, Qa55aa51545, Qda4afa7611 |
| `q:D5f648a24b9` | Ab238fd5c usd_per_100bps | $1.3M | Q1bdd2859c3, Q31a3760396, Q4272afac77, Q5a6a21638b, Qa55aa51545, Qda4afa7611 |

