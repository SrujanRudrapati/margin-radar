# Morning report — Margin Radar

**Synthetic data — not Opendoor data.**

> **Updated 2026-10-23 (evening).** Per Srujan's instruction, every detector number in sections 2, 6 and 7 now comes from one seed set: the true holdout, seeds 11–20 (DECISIONS D28–D31). The detector also changed today: renovation-overrun shrinkage, D31. Last night's mixed holdout 6–10 and all-seed numbers were removed. See EVENING_REPORT.md for today's work.

Phases 2–8 are done and merged to `main`; nothing was pushed and no remote was added. All three detector gates (scored on the true holdout) **fail**, reported as measured, never loosened. All six LLM gates **pass**. The demo, the API and the dashboard run in replay mode with zero live calls, which I verified from a fresh clone with no `.env`.

## 1. Phase status

| Phase | Status | Branch | Merge commit on `main` |
|---|---|---|---|
| 1 Generator | done (before tonight) | phase-1 (fast-forward) | `3f33280` |
| 2 dbt + MetricFlow + governed store | done | phase-2 | `1c782c9` |
| 3 Peer-relative detector | done | phase-3 | `ff04537` |
| 4 Grounded Claude agent + briefs | done | phase-4 | `d38c170` |
| 5 Evaluation | done; detector gates fail honestly | phase-5-eval | `ee143dd`, `d2b9188` |
| 6 Feedback loop (decision log) | done | phase-6-feedback | `b768587` |
| 7 Dashboard + static export | done | phase-7-dashboard | `8ede8cd` |
| 8 Review, security, fresh clone, README, Pages workflow | done | phase-8-polish | `b9cf134` |

Each phase ended with a fresh reviewer on the whole branch. Critical and Important findings were fixed test-first (RED → GREEN), and Minors were deferred (see section 8). The full test suite passes on `main`, with 2 documented xfails (section 7).

## 2. Evaluation results

Source: `eval/results.json` and `eval/results.md`. Rates are truncated, never rounded up. Every detector number is on the **true holdout, seeds 11–20**. These seeds were never used for tuning, and each one draws its own scenario scopes and onset weeks (weeks 28–46). Thresholds and the D31 shrinkage were tuned on seeds 1–5. Seed 42 is the in-sample demo.

**Lead time per scenario** (weeks between the first alert and sold-home margin showing the problem; ranges cover only the seeds caught before margin did):

| Scenario | True holdout 11–20 | Seed 42 (demo, in-sample) |
|---|---|---|
| A: buyers slow down in one market (time to first buyer offer ×1.4) | 0/10 caught | missed |
| B: adverse selection in one band (conversion ×1.25, resale ×0.97) | 8/10, median 9.5 (5–13) | B2: alert wk 38, margin wk 45, 7 weeks |
| C: renovation overrun in one market (×1.18) | 8/10, median 5.5 (1–12) | M05: alert wk 43, margin wk 46, 3 weeks |

**Precision / recall (11–20):** precision (true alert episodes / all episodes) 0.814; recall before margin shows the problem 0.533.

**False alerts per week, control run** (same seeds, nothing injected): 0.056 (29 alert-weeks / 510). None fall in the Q3 margin-dip quarter.

**Wrong-scope alert episodes:** 5 (gate ≤ 2).

**LLM evaluations** (seed 42, `CLAUDE_MODEL_FINAL` = claude-sonnet-5-5):
- Briefs at weeks 40, 45, 50, 60: 4/4 published (valid).
- Grounding: 107/107 numbers match their cited facts, 100%. The first drafts had 4 errors in total, all fixed by the single revision (briefs re-recorded today after the D31 detector change).
- Brief accuracy: minimum 1.00 of sections accurate, 0 direction errors.
- Top-ranked action on an injected scope: 4/4. Every action section labels its $ as sample-scale: 4/4.
- 20 questions, semantic layer vs raw SQL: **20/20 vs 19/20**. Note that raw-SQL mode can read `mart_segment_week`, the semantic layer's own pre-aggregated input, so this flatters raw SQL.
- Abstention on 5 unanswerable questions: 5/5 in both modes, with 0 false abstentions.

**Gates:**

| Gate | Result |
|---|---|
| Recall before margin ≥ 8/10 per scenario (seeds 11–20) | **FAIL** (A 0/10; B 8/10; C 8/10) |
| Zero control alert-weeks (seeds 11–20) | **FAIL** (29) |
| Wrong-scope episodes ≤ 2 (seeds 11–20) | **FAIL** (5) |
| All eval briefs valid | PASS |
| Grounding 100% | PASS |
| Brief accuracy ≥ 90% and 0 direction errors | PASS |
| Top action on a true scope | PASS |
| Sample-scale labelled | PASS |
| Abstention 100% | PASS |

The brief-accuracy gate first measured a minimum of 0.00. The cause was the scorer: it recognised only direction verbs and missed correct phrasing such as "above peers" and "a gap of +11.7 pts". I widened the cues with two-sided tests and left the gate rule unchanged (D19). Before and after are both recorded there.

## 3. API calls, tokens, cost

From `data/token_log.jsonl` (live calls only; replays cost $0):
- Live calls tonight: 182 of the pre-approved 300. Haiku (dev): 16. Sonnet (final): 166. 143 went through the Batches API at half price.
- Tokens: 208,118 input, 52,520 output, 281,695 cache-read.
- Estimated cost: **$0.5793** of the $5 cap.
- `eval/recording_cost.json` (committed) prices the eval recording alone: 157 calls, $0.3937.
- No cap was hit. Every live run printed its planned call count first.

## 4. Decisions made on your behalf

All are in [docs/DECISIONS.md](docs/DECISIONS.md) (D1–D27, plus a list of per-phase rulings). Tonight's main ones:
- **D16:** expanding drift baseline. This was the root cause of control false alerts: 374 → 78 alert-weeks.
- **D17:** detector gates fail and are reported as measured.
- **D18:** decision log design.
- **D19:** brief-accuracy scorer direction cues.
- **D20, D25:** QA tool output made canonical so replay survives dbt rebuilds and fresh clones.
- **D21:** the API opens both run databases.
- **D22:** alert episodes are warmed at API startup.
- **D23:** drilldown alerts are filtered per metric.
- **D24:** per-run `MAX_API_CALLS` cap; `--live` is refused under `REPLAY=1`.
- **D26:** rates are truncated, never rounded up.
- **D27:** the Pages workflow is manual-only.

## 5. Run the demo

```bash
cd ~/margin-radar
make setup          # first time only: conda env from environment.yml
make demo           # builds data + metrics, replays briefs, serves API :8000 and dashboard
open http://localhost:5173
```

- Ctrl-C stops both servers.
- Static version: `make export`, then `cd web && npx vite preview`, then open http://localhost:4173.
- Stop `make demo` before `make export`, `make build` or `make eval`. DuckDB allows one writer, and the API holds the files open.
- Replay evaluation: `make eval` (zero live calls).
- Screenshots: `docs/screenshots/` (desktop light and dark, mobile).

**Verified tonight from a fresh clone of `main` with no `.env`** (inside the repo at `.worktrees/fresh`, gitignored):
- `make demo` built everything and served the dashboard (HTTP 200) and the API.
- `make eval` reproduced every gate and number.
- `make export` built the static site.
- The clone's token log shows **0 live calls** (116 replays). The only diffs are float last bits in the query logs and the per-machine call counter.

## 6. Two-minute talk track

> Contribution margin is a lagging number. We only learn it when a home resells, so a pricing mistake made at purchase surfaces months later. Every 100 bps is about $90M a year at a $9B run rate. Margin Radar watches the leading indicators instead: first-offer rate, contract rate and renovation overrun, for every market, price band and product, every week.
>
> The key move is comparing each segment with its peers in the same week. Seasonality, like the spring peak and the summer margin dip, moves everyone together, so it cancels and doesn't alert. Across ten clean holdout runs, none of the false alerts fell in the Q3 dip quarter.
>
> I tested it on ten synthetic runs it never saw during tuning. Each run injected three problems into a randomly chosen market or price band, starting in a random week. It caught adverse selection a median of **9.5 weeks** before sold-home margin showed it, in **8 of 10** runs. It caught the renovation overrun a median of **5.5 weeks** early, in **8 of 10**. Adverse selection is the subtle one. Conversion goes *up*, which looks like good news, while our spread is flat against peers. That's the pattern of sellers accepting because the home is worth less than our model thinks.
>
> Each week Claude writes a brief, but it never computes a number. Its tools return governed facts with query IDs, and a checker rejects any number that doesn't match a cited fact exactly. In the evaluation, **107 of 107** numbers were grounded. It also abstains: it declined **5 of 5** unanswerable questions.
>
> What doesn't work yet: it missed the slow-buyer problem in all ten runs. At roughly 15 listings a week per market, that signal sits below the noise. On clean runs it still fires **0.056** false alerts a week: 29 alert-weeks across ten runs, and none at all in six of them. It was 74 before I shrank thin segments toward their peers. I report both misses rather than tuning them away. Dollar figures are sample-scale, at this synthetic portfolio's ~$1.6B a year.

## 7. Weaknesses an interviewer might probe

- **"Your detector fails its own gates."** Yes, all three, on the true holdout. B and C each reach 8/10, but A is 0/10, so the recall gate fails. There are 29 control alert-weeks and 5 wrong-scope episodes. At ~20k offers over 78 weeks (a median of 2 sales per segment-week), scenario A is below the noise floor. Lowering thresholds caught more but fired on the control run (D8, D9, D16). I kept the gates and reported the miss.
- **"Is the holdout really held out?"** Yes, as of today. Seeds 11–20 were never used for tuning, and each draws its own scopes and onset weeks (D28). The new detector was kept only under a rule written before it saw them (D29). One caveat: the expanding-baseline design (D16) was chosen on seeds 1–10, before 11–20 existed.
- **"Still too many false alerts on a clean run."** 0.056 alert-weeks per week across 10 holdout control runs (29 / 510), down from 74 before renovation shrinkage. Six of the ten runs have none, and the worst has 14. What's left: one B2 adverse-selection episode, two demand-softening episodes and two one-week portfolio shifts. None fall in the Q3 dip.
- **"Did the shrinkage cost anything?"** Yes, on the demo seed. Seed 42's M05 renovation alert now comes at week 43, 3 weeks before margin shows it, instead of 6. On the holdout, C went from 7/10 to 8/10 with a median lead of 5.5 weeks.
- **"Doesn't peer comparison miss market-wide shocks?"** Yes. Simultaneous all-segment shifts cancel. A portfolio check catches only abrupt ones.
- **"How do you know the dollar figure?"** Renovation drift is measured. Adverse selection is a scenario estimate (a 1–3% valuation shortfall, ranked on the midpoint) and stays unconfirmed until resales. On seed 42 the B2 episode ends before the cohort has enough resales, so the "confirmed by resales" switch never turns on. That's an xfail test, kept honest.
- **"Are the scores probabilities?"** No. They're uncalibrated robust z-scores, labelled that way everywhere.
- **"Semantic layer 20/20 vs raw SQL 19/20 isn't much of a gap."** Agreed. Raw SQL could read the pre-aggregated mart, so the comparison flatters raw SQL. The semantic layer's value here is governance (query IDs, one definition per metric), not accuracy.
- **"What did the decision log prove?"** Nothing causal. The synthetic data doesn't react to decisions, so "estimated $ saved" (~$2.2M on seed 42) is the no-action counterfactual, labelled as such.
- **"Does the eval replay from a fresh clone?"** Yes. dbt rebuilds changed float sums in their last bits, which broke replay. Tool outputs are now canonical (D25), and I verified this with rebuild-and-replay runs.

## 8. What's left, in priority order

1. ~~Cut control false alerts with a volume floor or shrinkage, on a true holdout.~~ Done 2026-10-23 (D28–D31): 74 → 29 control alert-weeks on seeds 11–20.
2. Scenario A (demand softening): pool first-offer and showing rate into one composite signal, or accept that it's undetectable at this volume.
3. Deferred minors from reviews:
   - A portfolio-level action card would link to an invalid drilldown (latent).
   - The decision form lists only the top 3 alerts.
   - POST error text shows `[object Object]` for validation errors.
   - Accessibility: ~~citations open only on hover or focus (not on tap)~~ fixed 2026-10-23; radio and tab roles still lack arrow keys.
   - Importing `api.main` creates `data/decisions.duckdb`.
   - Phase 4 minors are listed in DECISIONS.
4. Phase 10 (skipped as instructed): enable Pages and run the workflow by hand.

## 9. Questions for Srujan

1. **The API opens both run databases** so the dashboard can toggle between injected and control (D21). That's the spirit of "only /eval opens both", not the letter. OK, or should the dashboard run as two processes?
2. **Detector gates:** do you want me to try the shrinkage baseline next (item 1), or present the honest failure as is?
3. **Two xfails** stay: `test_a_detected_before_cm_visible` (scenario A missed) and `test_adverse_selection_switches_to_measured_after_resales` (B2 never reaches resale confirmation on seed 42). Keep them as xfails or delete them?
4. **The pre-approved 300-call night cap** lived in code only for tonight. I replaced it with your standing per-run `MAX_API_CALLS` (default 50) rule (D24). OK?
5. **Two environment slips to know about.**
   - `pip install playwright` put Playwright 1.64.1, unpinned, into the conda env for screenshots (it's not in `environment.yml`). Its Chromium was already cached in `~/Library/Caches/ms-playwright` from Oct 12.
   - A mistyped `npx tsc` fetched an unrelated package, `tsc@2.0.4`, into `~/.npm/_npx/1d6e82a4126006c4`. It didn't run code beyond printing a warning. I didn't delete it, because your rule says never delete outside the repo. You may want to remove that folder.
6. **The `sk-ant` check:** `git log -p | grep -i "sk-ant"` returns 10 lines, and none is a key. They're placeholders in the vendored claude-api skill docs (`sk-ant-oat01-...`, `sk-ant-admin...`) plus SPEC.md and PLAN.md describing the check. The real-key pattern `sk-ant-[A-Za-z0-9_-]{20,}` returns 0 lines across all history, logs and cache. Should the vendored `.claude/skills/` stay committed?
