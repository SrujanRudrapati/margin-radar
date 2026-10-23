Synthetic data — not Opendoor data.

# Old vs new detector on the true holdout (seeds 11–20)

No setting was tuned on seeds 11–20, and each seed draws its own scopes and onset weeks (DECISIONS D28). One holdout control run (seed 18) was inspected while diagnosing the false alerts (D32), so a second, never-inspected set, seeds 21–30, is reported at the end as a leakage check. "Old" is the detector as of commit `9ac8b7b`, with the D29 knobs off. Its holdout numbers were recorded before any change was made. "New" adds renovation-overrun shrinkage (floor 4, k = 35), chosen on seeds 1–5 only (D29, D31). Rates are truncated, never rounded up. The gate rules are unchanged (D30).

| Measure (seeds 11–20) | Old | New | Gate |
|---|---|---|---|
| Control false alert-weeks | 74 / 510 (0.145 per week) | **29 / 510 (0.056 per week)** | 0: fail, fail |
| Control seeds with zero alert-weeks | 4 of 10 | 6 of 10 | — |
| Wrong-scope alert episodes (injected runs) | 9 | **5** | ≤ 2: fail, fail |
| A: buyers slow down, caught before margin | 0/10 | 0/10 | ≥ 8/10: fail, fail |
| B: adverse selection, caught before margin | 8/10, median lead 9.5 weeks (5–13) | 8/10, median lead 9.5 weeks (5–13) | ≥ 8/10: meets it in both |
| C: renovation overrun, caught before margin | 7/10, median lead 5 weeks (3–12) | **8/10**, median lead 5.5 weeks (1–12) | ≥ 8/10: old misses, new meets it |
| Precision (true episodes / all episodes) | 0.709 | 0.814 | — |
| Recall before margin (all 30 scenario-seeds) | 0.500 | 0.533 | — |
| Gates passed | 0 of 3 | 0 of 3 | — |

The recall gate needs every scenario to reach 8/10, so A's 0/10 fails it for both detectors.

**Decision rule (fixed in D29 before the new detector saw the holdout):** keep the new detector only if it passes more gates, or passes the same gates with no lower recall and fewer control alert-weeks. New: same gates (0 of 3), recall 16 vs 15, control alert-weeks 29 vs 74, so the new detector is kept.

## Do control false alerts cluster in the Q3 margin dip?

No. Evaluation starts at week 27, so Q3 2025 covers weeks 27–37: 110 of the 510 evaluable control weeks (21.6%).

| Quarter | Evaluable control weeks | Old alert-weeks | New alert-weeks |
|---|---|---|---|
| 2025 Q3 (the margin dip) | 110 (21.6%) | 3 (4.0% of 74) | **0** (0% of 29) |
| 2025 Q4 | 130 | 27 | 13 |
| 2026 Q1 | 130 | 28 | 9 |
| 2026 Q2 | 130 | 16 | 7 |
| 2026 Q3 (week 77 only) | 10 | 0 | 0 |

The dip quarter has the lowest false-alert rate under both detectors. The old detector's false alerts were mostly renovation drift in the low-volume fall and winter weeks; shrinkage removed all of them. The new detector's 29 alert-weeks are:
- one B2 adverse-selection episode in seed 15 (13 alert-weeks, Q4–Q1)
- two demand-softening episodes (B1 in seed 11, M01 in seed 16; 14 alert-weeks)
- two one-week portfolio shifts

Margin metrics never trigger an alert. They are the lagging outcome.

## What it cost

On seed 42 (the demo seed, in-sample), the M05 renovation alert now fires at week 43 instead of 40: 3 weeks before sold-home margin shows the problem (week 46) instead of 6. B2 is unchanged (week 38, 7 weeks early).

## Leakage check: seeds 21–30 (never inspected)

While diagnosing the old detector's false alerts I inspected one holdout control run, seed 18 (DECISIONS D32). As a check, seeds 21–30 were drawn the same way and run **once**, with the final detector, after every decision was made. Nothing was tuned or decided on them. They are not the quoted result; the quoted result stays 11–20.

| Measure | Holdout 11–20 (new) | Confirmation 21–30 (new) |
|---|---|---|
| Control false alert-weeks | 29 / 510 (0.056 per week) | 10 / 510 (0.019 per week) |
| Wrong-scope alert episodes | 5 | 4 |
| A caught before margin | 0/10 | 2/10, median lead 6 weeks (2–10) |
| B caught before margin | 8/10, median lead 9.5 (5–13) | **4/10**, median lead 7.5 (2–12) |
| C caught before margin | 8/10, median lead 5.5 (1–12) | 8/10, median lead 5 (4–13) |
| Control alert-weeks in the Q3 2025 dip quarter | 0 of 29 | **4 of 10** (one B2 adverse-selection episode, seed 25, weeks 32–35) |

What this says:
- False alerts and C hold up on the unseen set.
- B is much weaker on 21–30: 3 seeds missed outright (22, 23, 25) and 3 caught only after margin showed it (24, 27, 28). I have not investigated why. With 10 seeds per set, draw-to-draw variance in scope and onset is a likely part of it. Either way, B's 8/10 on 11–20 should not be read as a stable rate.
- In Q3 2025 the control false-alert rate is 0.036 per week, against 0.019 overall. That's one 4-week episode, too little to call a cluster, but "false alerts never fall in the dip" is not supported. Say "they don't cluster in the dip on the holdout".

## Reported gaps after the review (D33)

The end-of-day review found that shrunk residuals had leaked into reported gaps and into the measured renovation dollars. Now the detector only *scores* on shrunk residuals, and every reported gap and dollar figure uses the observed residual. Detections are byte-identical before and after this fix on all 20 seeds, so the numbers above are unchanged.
