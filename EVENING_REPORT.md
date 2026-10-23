# Evening report — Margin Radar (2026-10-23)

**Synthetic data — not Opendoor data.**

I worked through your answers to the six morning-report questions, plus the three extras. Everything is on branch `phase-9-holdout`, merged to `main` (see section 9). Nothing was pushed and no remote was added.

**Headline:**
- On the true holdout (seeds 11–20), the new detector cuts control false alerts from 74 to 29 alert-weeks and wrong-scope episodes from 9 to 5. It catches renovation overrun in 8/10 instead of 7/10.
- All three detector gates still fail, and they are unchanged.
- A second, never-inspected seed set (21–30) confirms the false-alert drop but catches adverse selection only 4/10. Details in section 2.
- The API cost was **24 live calls, $0.4641**, against your $2 / 150-call cap.

## 1. Your six answers, and what I did

| # | Your answer | Done | Where |
|---|---|---|---|
| 1 | API may open both DBs; add a test that /detector and /agent can't reach control; document in D21 | Done. Every `GovernedStore` connection is now read-only with DuckDB external access off, so it can't `ATTACH` the other run or scan its Parquet. Tests prove both are refused with the configuration error, not a missing path. A second test proves no agent tool takes a db, path, file or run argument. D21 is updated. | `tests/test_boundaries.py`, `detector/governed.py` |
| 2a | Build a true holdout (seeds 11–20, randomized scopes and onsets) and report the current detector before changing anything | Done. Scopes and onset weeks (28–46) are drawn per seed. The unchanged detector was recorded first: 74 control alert-weeks, 9 wrong-scope episodes, A 0/10, B 8/10, C 7/10. | `eval/detector_eval.py`, D28 |
| 2b | Try a volume floor and/or shrinkage, tuned on 1–5 only | Done. Both knobs are per metric. The selection rule was written in D29 before any new holdout run. On 1–5: renovation-overrun floor 4 with k = 35. Contract rate stays unchanged, because its only gain on 1–5 was one seed. | D29, D31 |
| 2c | Old vs new side by side on the holdout; keep the better; gates unchanged | Done; new kept (section 2). Gates use the same rules, now scored on 11–20 only. | `eval/holdout_comparison.md`, D30 |
| 2d | Do control false alerts cluster in the Q3 dip? | On the holdout, no: 0 of 29 alert-weeks fall in Q3 2025 (old detector: 3 of 74). Caveat: on the untouched set 21–30, 4 of 10 do (one episode). | section 3 |
| 3 | Keep both xfails with clear reasons | Kept as is. Both still fail for the stated reason, and their reason strings were already specific. They are strict, so they'll flag it if either starts passing. | `tests/detector/test_rules.py`, `tests/detector/test_impact.py` |
| 4 | Per-run `MAX_API_CALLS` OK | No change. Both recording runs used it (cap 50). | — |
| 5 | Pin playwright as a dev dependency | `playwright==1.64.1  # dev only …` is in `environment.yml`, with a test. | `environment.yml` |
| 6 | Remove `.claude/skills/` from repo and history; gitignore; README install list | Done (details below). History now has 0 commits touching `.claude/skills`. `git log --all -p | grep sk-ant` drops from 10 lines to 5, and none of the 5 comes from the vendored docs: they're SPEC, PLAN and report text describing the check itself. The real-key pattern `sk-ant-[A-Za-z0-9_-]{20,}` matches 0. The README has an install table with sources. | `.gitignore`, `README.md` |
| + | One seed set everywhere | README, MORNING_REPORT.md (updated, with a note at the top) and the dashboard quote seeds 11–20 only. Seeds 21–30 appear only as a labelled leakage check in `eval/holdout_comparison.md` and here. | — |
| + | Talk track with new numbers, no rounding up | Section 7. Rates are truncated (0.0568 → 0.056). | — |
| + | Citations open on tap | Done. A tap opens and pins a citation; a second tap, Escape, blur or a tap elsewhere closes it. Hover counts only for a real mouse, the tooltip stays open while hovered, and `aria-describedby` is wired. Verified in headless Chromium with 14 checks across touch, mouse and keyboard. | `web/src/screens/Briefs.tsx` |

**History rewrite (item 6), and one slip:**
- I ran `git filter-branch --index-filter 'git rm -r --cached --quiet --ignore-unmatch .claude/skills' --prune-empty -- --all` over all 5 branches, then deleted the backup refs, expired the reflog and ran `gc --prune=now`.
- I removed the two stale merged worktrees (`.worktrees/p6`, `.worktrees/p7`) first, so their branches could be rewritten.
- **Slip:** filter-branch's final checkout also deleted the skill files from disk, which I hadn't intended. I restored them (all 102 files, diffed identical) from a bundle I had made of the full pre-rewrite repo just before. They are now untracked and ignored, so Claude Code still sees them.
- **That bundle still contains the old history with the skills.** It's at `/private/tmp/claude-501/-Users-srujan-margin-radar/7d5fa368-5a50-4b18-be88-577c29323813/scratchpad/pre-rewrite-backup.bundle`. Delete it once you're happy.
- **All commit hashes changed.** For example, `main`'s pre-today tip was `c242e8c` and is now `73aeed6`, so the merge commits quoted in MORNING_REPORT.md section 1 are old hashes.

## 2. Detector: old vs new on the true holdout (seeds 11–20)

Rates are truncated. The gate rules are unchanged.

| Measure | Old (`9ac8b7b`, knobs off) | New (renovation shrinkage) | Gate |
|---|---|---|---|
| Control false alert-weeks | 74 / 510 (0.145 per week) | **29 / 510 (0.056 per week)** | 0: fail, fail |
| Control seeds with zero alert-weeks | 4 of 10 | 6 of 10 | — |
| Wrong-scope episodes | 9 | **5** | ≤ 2: fail, fail |
| A caught before margin | 0/10 | 0/10 | ≥ 8/10 |
| B caught before margin | 8/10, median lead 9.5 weeks (5–13) | 8/10, median lead 9.5 (5–13) | ≥ 8/10 |
| C caught before margin | 7/10, median lead 5 (3–12) | **8/10**, median lead 5.5 (1–12) | ≥ 8/10 |
| Precision / recall before margin | 0.709 / 0.500 | 0.814 / 0.533 | — |
| Gates passed | 0 of 3 | 0 of 3 | — |

**Why the new one is kept.** The D29 rule (written before the holdout run) was: more gates passed, or the same gates with recall no lower and fewer control alert-weeks. New has the same gates, recall 16 vs 15 and 29 vs 74 control alert-weeks.

**Root cause it fixes** (systematic debugging):
1. A thin segment (about 8 renovations per window) crosses the hard sample floor of 8.
2. The rollup's segment mix changes, and the pooled residual jumps 0.06–0.09 (z ≈ 7).
3. The CUSUM then decays for months: one blip became a 29-week episode.

Shrinking each segment residual by n / (n + 35) removes the cliff. The detector **scores** on shrunk residuals, but every reported gap and dollar figure uses the observed residual (D33, after the review).

**What it cost:** on seed 42 (the demo, in-sample), M05 renovation now alerts at week 43 instead of 40. That's 3 weeks before margin shows it instead of 6. B2 is unchanged (week 38, 7 weeks early).

**Leakage check, seeds 21–30.** I looked at one holdout control run (seed 18) while diagnosing, which is leakage (D32). So I drew 10 more seeds the same way and ran them once, after every decision, with the final detector:

| Measure | Holdout 11–20 | Confirmation 21–30 |
|---|---|---|
| Control false alert-weeks | 29 / 510 (0.056) | 10 / 510 (0.019) |
| Wrong-scope episodes | 5 | 4 |
| A / B / C caught before margin | 0/10, 8/10, 8/10 | 2/10, **4/10**, 8/10 |

- False alerts and C hold up on the unseen set. B does not: 3 seeds missed outright and 3 caught only after margin.
- I haven't investigated the B gap. With 10 seeds per set, draw variance is a likely part of it. The README now says B's rate is unstable across seed sets, without quoting the second set's numbers.

## 3. Q3 clustering (your question 2d)

On the true holdout, the control false alerts **do not cluster in the Q3 margin dip**. Evaluation starts at week 27, so Q3 2025 is weeks 27–37: 110 of the 510 evaluable control weeks (21.6%).

| Quarter | Old alert-weeks (of 74) | New alert-weeks (of 29) |
|---|---|---|
| 2025 Q3 (dip) | 3 | **0** |
| 2025 Q4 | 27 | 13 |
| 2026 Q1 | 28 | 9 |
| 2026 Q2 | 16 | 7 |
| 2026 Q3 (week 77) | 0 | 0 |

**Caveat for your talk track:** on the untouched set 21–30, 4 of 10 control alert-weeks fall in Q3 2025. That's one B2 adverse-selection episode, seed 25, weeks 32–35, a Q3 rate of 0.036 per week against 0.019 overall. That is too little to call a cluster, but it means "never fires in the dip" would overclaim. The talk track says "on the ten holdout runs, none of the remaining false alerts fell in the Q3 dip quarter", which is exactly true. If pressed, say they don't cluster there.

## 4. End-of-day review and fixes

A fresh reviewer read the branch diff (no Critical findings). Everything Important and the Minors were fixed test-first:
- **Important, verified:**
  - **The problem.** `peer_residuals` shrank residuals for every caller. On seed 42 the agent cited a 0.056 "scope minus peers" gap next to a 0.203 scope value and a 0.021 peer median, and the measured renovation dollars were scaled down the same way.
  - **Fix (D33).** Shrinkage now only feeds scoring. The alert gap, renovation dollar impact, `compare_segments` gaps and the drilldown gap line all use observed residuals. `compare_segments` and the drilldown cite the detector's own score.
  - **Side effects.** Detections are byte-identical on all 20 seeds. At seed-42 week 45, M05's measured dollars now outrank B2's scenario midpoint, so the API test checks membership, not order.
- **Important:** holdout leakage (seed 18). I disclosed it everywhere "never used for tuning" appeared, and added the 21–30 check (D32).
- **Minor:**
  - `assemble` without holdout seeds now raises a clear error.
  - The boundary test matches DuckDB's "disabled by configuration" message.
  - The citation state machine was reworked: outside tap, second click and Enter close it, the tooltip stays open while hovered, and `aria-describedby` is wired.
- **Not changed (pre-existing, by definition):** a `compare_segments` gap is a volume-weighted mean of segment residuals, so it tracks "scope value minus peer median" only roughly (0.156 vs 0.160 at M05, week 60). The test asserts the exact property instead: the gap equals the observed rollup residual.

## 5. API calls, tokens, cost (today)

From `data/token_log.jsonl`, live calls only:

| Run | Live calls | Model | Est. cost |
|---|---|---|---|
| Re-record 4 eval briefs after D31 | 13 | claude-sonnet-5-5 | $0.2574 |
| Re-record 4 eval briefs after D33 | 11 | claude-sonnet-5-5 | $0.2067 |
| **Total** | **24** of 150 | | **$0.4641** of $2 |

- Tokens: 112,393 input, 21,048 output, 67,562 cache-read.
- Each run printed its planned upper bound first: 298, which assumes nothing replays. Only the 4 briefs could miss, at most 4 × 12 = 48 calls. Both runs had a hard cap of `MAX_API_CALLS=50`.
- The QA conversations replayed unchanged. The demo's week-40 brief shares its recording with the eval's.
- `eval/recording_cost.json` (all eval recordings to date) is 181 calls, $0.8578.
- After each recording, `make eval` plus `make briefs decisions markers export` ran with **0 live calls** (121 replays).

## 6. Decisions logged today (docs/DECISIONS.md)

- **D21 (updated):** API opening both databases is approved. The guard is now enforced in code and in tests.
- **D28:** true holdout seeds 11–20. Scopes and onsets are drawn per seed, with the range fixed before any results.
- **D29:** the two knobs, plus the selection and keep rules, written before the holdout run.
- **D30:** gates are scored on 11–20 only, with the same rules. The tuning (1–5) and seen (6–10) splits are kept for transparency.
- **D31:** adopted renovation-overrun shrinkage (floor 4, k = 35), with the old-vs-new numbers.
- **D32:** disclosure that I inspected holdout seed 18, plus the 21–30 leakage check.
- **D33:** shrinkage only scores; every reported gap and dollar figure is observed.

## 7. Two-minute talk track (updated; holdout numbers only, truncated)

> Contribution margin is a lagging number. We only learn it when a home resells, so a pricing mistake made at purchase surfaces months later. Every 100 bps is about $90M a year at a $9B run rate. Margin Radar watches the leading indicators instead: first-offer rate, contract rate and renovation overrun, for every market, price band and product, every week.
>
> The key move is comparing each segment with its peers in the same week. Seasonality, like the spring peak and the summer margin dip, moves everyone together, so it cancels and doesn't alert. On the ten clean holdout runs, none of the remaining false alerts fell in the Q3 dip quarter.
>
> I tested it on ten synthetic runs that no setting was tuned on. Each run injected three problems into a randomly chosen market or price band, starting in a random week. It caught adverse selection a median of **9.5 weeks** before sold-home margin showed it, in **8 of 10** runs. It caught the renovation overrun a median of **5.5 weeks** early, in **8 of 10**. Adverse selection is the subtle one. Conversion goes *up*, which looks like good news, while our spread is flat against peers. That's the pattern of sellers accepting because the home is worth less than our model thinks.
>
> Each week Claude writes a brief, but it never computes a number. Its tools return governed facts with query IDs, and a checker rejects any number that doesn't match a cited fact exactly. In the evaluation, **105 of 105** numbers were grounded. It also abstains: it declined **5 of 5** unanswerable questions.
>
> What doesn't work yet: it missed the slow-buyer problem in all ten runs. At roughly 15 listings a week per market, that signal sits below the noise. On clean runs it still fires **0.056** false alerts a week: 29 alert-weeks across ten runs, and none at all in six of them. It was 74 before I shrank thin segments toward their peers. And adverse-selection recall swings a lot between seed sets: a second untouched set caught it far less often. I report all of this rather than tuning it away. Dollar figures are sample-scale, at this synthetic portfolio's ~$1.6B a year.

Changes from last night's version:
- Lead times are now on runs with random scopes and onsets: B 9.5 weeks (was 9 on 6–10), C 5.5 weeks (was 8).
- Grounding is 105/105.
- The false-alert line is 0.056 per week (was "about 0.15").
- New: a sentence that B's recall is unstable across seed sets.
- The Q3 sentence is scoped to the holdout (see the caveat in section 3).

## 8. Weaknesses an interviewer might probe (new or changed today)

- **"Is the holdout really held out?"** Mostly. No setting was tuned on 11–20. But I inspected one holdout control run (seed 18) while diagnosing, and the keep-or-revert call was made on 11–20, by your design. The untouched 21–30 set is the honest check: false alerts and C hold up, B doesn't.
- **"Is 8 of 10 for adverse selection stable?"** No (section 2). I haven't investigated why.
- **"Your shrinkage just hides signal."** Partly true. It cost the demo seed 3 weeks of lead on M05. The detector scores on shrunk residuals, but every gap and dollar figure shown is observed (D33).
- **"Do false alerts hit during the summer dip?"** Not on the holdout (0 of 29). On the untouched set, one 4-week episode did.
- All of last night's other points still stand (MORNING_REPORT.md section 7, updated to 11–20 numbers).

## 9. Verification

- **Tests.** The full suite passes on the branch, with 2 strict xfails (the A miss and B2 resale confirmation on seed 42). The slow multi-seed tests pass. New tests cover:
  - the run boundary (×2)
  - scenario draws, split and gate assembly, and the missing-holdout error
  - shrinkage on and off
  - observed vs scored gaps in the detector and in `compare_segments`
  - the playwright pin
- **Replay.** After the final recording, `make eval` and `make briefs decisions markers export` made 0 live calls (121 replays).
- **Fresh clone of the branch, no `.env`.** `make briefs export` built everything. The eval's LLM part replayed with all 6 gates passing, 0 live calls and 121 replays. The only diffs were float last bits in the query logs.
- **Browser.** Headless Chromium, using the static export:
  - touch (390×844): tap, second tap and outside tap
  - desktop: hover, hover into the tooltip, click to pin and unpin, outside click
  - keyboard: focus, Enter to close and reopen, Escape
- **Branch.** `phase-9-holdout` (9 commits) is merged into `main` with `--no-ff`, as last night. Not pushed.

## 10. What's left, in priority order

1. **Adverse-selection recall is unstable across seed sets** (8/10 vs 4/10). Investigate on tuning seeds only: is it B3 scopes, late onsets, or volume?
2. **Scenario A (demand softening)** is still 0/10 on the holdout (unchanged from last night's item 2).
3. **Remaining control false alerts** (29 alert-weeks on the holdout) are adverse-selection and demand-softening episodes. The contract-rate knobs showed no effect on 1–5.
4. **Deferred minors** from last night's list are unchanged, except the citation tap fix (done). Radio and tab roles still lack arrow keys.
5. Phase 10 (Pages) remains manual.

## 11. Questions for you

1. **Delete the pre-rewrite backup bundle?** It still contains the vendored skills in history. It's in my session scratchpad (path in section 1), outside the repo, and will go when that temp directory is cleaned. I didn't delete it, so you keep a rollback until you've checked the rewritten history.
2. **Seeds 21–30.** Should they become the new "quoted" set, given seed 18 was looked at? Or stay a labelled leakage check, as now? I kept 11–20 as quoted because that's what you specified.
3. **The B instability.** Do you want me to dig into it (tuning seeds only), or present it as a known limit?

**Synthetic data — not Opendoor data.**
