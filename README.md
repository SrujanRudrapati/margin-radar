# Margin Radar

**Synthetic data — not Opendoor data.**

An early-warning agent for an iBuyer's contribution margin. Margin is a lagging number: it is computed only on homes that have sold, so a pricing mistake made at purchase shows up months later. Margin Radar watches leading funnel indicators by segment (first-offer rate, contract rate, renovation overrun), separates seasonality from drift by comparing each segment with its peers in the same week, flags adverse selection that looks like "great conversion", ranks actions by dollars of margin at risk, and writes a weekly brief in which every number cites a governed query.

## How it works

```mermaid
flowchart LR
  G[generator<br/>synthetic offers, homes,<br/>3 injected problems + control] --> D[(DuckDB<br/>one file per run)]
  D --> T[dbt + MetricFlow<br/>governed metrics]
  T --> S[GovernedStore<br/>read-only, query IDs]
  S --> R[detector<br/>peer residuals, drift score,<br/>rules, $ impact]
  R --> A[Claude agent<br/>tools return cited facts;<br/>grounding checker fails closed]
  A --> B[weekly brief<br/>every number → query ID]
  R --> API[FastAPI<br/>replay only]
  B --> API
  API --> W[React dashboard<br/>+ static export]
  E[eval<br/>20 seeds + ground truth] -.reads.-> D
```

- **Deterministic first, LLM second.** The detector computes every number. Claude only chooses among facts its tools return and writes prose. A checker rejects any number in the brief that doesn't exactly match a cited fact, then allows one revision, then fails closed.
- **Seasonality doesn't alert.** The spring peak and the ~500 bps Q2→Q3 margin dip move every segment together, so peer-relative residuals cancel them.
- **The agent abstains.** It writes no LLM brief when history is too short or no alert is active.

## Run it

Requires conda (env `margin-radar`, see `environment.yml`) and Node 22. No API key is needed: the demo, API and dashboard run in replay mode (`REPLAY=1`) from recorded responses and never call Claude.

```bash
make setup     # conda env
make demo      # data → dbt → detector → briefs (replay) → API :8000 + dashboard http://localhost:5173
make export    # pre-render every API response and build the static dashboard into web/dist
make test      # pytest (never makes live API calls)
conda run -n margin-radar python -m pytest -m slow   # the multi-seed sweeps (slow)
make eval      # 20-seed detector evaluation (gates on seeds 11–20) + seed-42 LLM evaluation, replayed → eval/results.md
```

Stop `make demo` before running `make export` or `make build`: DuckDB allows one writer per file, and the API holds the run databases open. A GitHub Actions workflow (`.github/workflows/pages.yml`) builds the static export and deploys it to GitHub Pages. It runs only when started by hand (`workflow_dispatch`), after Pages is enabled in the repository settings. Nothing has been pushed.

Screenshots (light, dark, mobile): `docs/screenshots/`.

## Results

From `eval/results.json`. Every detector number below is on the **true holdout, seeds 11–20**. No setting was tuned on these seeds, and each one draws its own scenario scopes (which market or price band) and onset weeks (weeks 28–46). The thresholds and the renovation shrinkage were tuned on seeds 1–5. Gates are reported as measured and are never loosened. Rates are truncated, never rounded up. Lead ranges cover only the seeds caught in time. Old vs new detector, and a leakage check on never-inspected seeds 21–30: `eval/holdout_comparison.md`.

| Measure (seeds 11–20) | Result | Gate |
|---|---|---|
| B: adverse selection (one price band), caught before margin showed it | 8/10, median lead 9.5 weeks (5–13) | ≥ 8/10: meets it |
| C: renovation overrun (one market), caught before margin | 8/10, median lead 5.5 weeks (1–12) | ≥ 8/10: meets it |
| A: buyers slow down (one market), caught before margin | 0/10 | ≥ 8/10: **fail** (so the recall gate fails) |
| False alerts per week, control run | 0.056 (29 alert-weeks / 510) | 0 alert-weeks: **fail** |
| Wrong-scope alert episodes | 5 | ≤ 2: **fail** |
| Control false alerts inside the Q3 margin dip | 0 of 29 (Q3 is 110 of the 510 weeks) | — |

| LLM evaluation (seed 42, final model) | Result | Gate |
|---|---|---|
| Briefs published (weeks 40, 45, 50, 60) | 4/4 | pass |
| Numbers grounded in cited facts | 107/107 (100%) | pass |
| Brief accuracy | every brief 100% of sections, 0 direction errors | pass |
| Top action on an injected scope | 4/4 | pass |
| 20 questions: semantic layer vs raw SQL | 20/20 vs 19/20 | — |
| Abstains on 5 unanswerable questions | 5/5 | pass |
| Cost to record the eval's responses (all recordings to date) | 170 live calls, $0.6511 estimated | — |

## Limitations

- **Simultaneous all-segment shifts are invisible.** Peer comparison cancels anything that moves every segment at once. A portfolio check catches only abrupt ones.
- **Sample-scale dollars.** Dollar figures are at the synthetic portfolio's ~$1.6B/yr, always shown as sample-scale and in bps. They are never scaled to a real business.
- **Uncalibrated scores.** Detector scores rank how unusual a move is. They are not probabilities.
- **The detector gates fail.** At ~20k offers over 78 weeks (median 2 sales per segment-week), scenario A (time to a first buyer offer 40% longer in one market) sits below the noise floor and is never caught. The control run still has 29 false alert-weeks across 10 seeds. See `docs/DECISIONS.md` D16–D17 and D28–D31.
- **One design choice predates the true holdout.** The expanding-baseline design (D16) was chosen on seeds 1–10, before seeds 11–20 existed. The renovation shrinkage was tuned on seeds 1–5 only.
- **Adverse-selection impact is a scenario estimate** (a 1–3% valuation shortfall) until resales confirm it.

## Claude Code skills used, and why

- **brainstorming → writing-plans**: turn the brief into `PLAN.md` before any code.
- **subagent-driven-development** (Phase 2) and **executing-plans** (Phases 3+), with **requesting-code-review** at the end of each phase.
- **test-driven-development**: every feature and fix starts from a failing test.
- **systematic-debugging**: found the frozen-baseline root cause of the control false alerts, and a replay miss caused by unordered SQL.
- **dbt skills** (analytics engineering, semantic layer): governed metrics in MetricFlow.
- **claude-api**: record/replay cache, prompt caching, strict tool schemas, Message Batches for evals.
- **frontend-design** and **webapp-testing**: dashboard design, plus Playwright screenshots in light, dark and mobile (`docs/screenshots/`).

The skills are not vendored in this repo (`.claude/skills/` is gitignored). To install them:

| Skill(s) | Source | Install |
|---|---|---|
| claude-api, webapp-testing | [anthropics/skills](https://github.com/anthropics/skills) (Apache-2.0) | `git clone https://github.com/anthropics/skills /tmp/skills && mkdir -p .claude/skills && cp -R /tmp/skills/skills/{claude-api,webapp-testing} .claude/skills/` |
| brainstorming, writing-plans, executing-plans, subagent-driven-development, test-driven-development, systematic-debugging, requesting-code-review | `superpowers` plugin, official marketplace | in Claude Code: `/plugin install superpowers@claude-plugins-official` |
| frontend-design | `frontend-design` plugin, official marketplace | `/plugin install frontend-design@claude-plugins-official` |
| dbt (analytics engineering, semantic layer) | [dbt-labs/dbt-agent-skills](https://github.com/dbt-labs/dbt-agent-skills) | `/plugin marketplace add dbt-labs/dbt-agent-skills`, then `/plugin install dbt@dbt-agent-marketplace` |

Playwright (screenshots only) is a pinned dev dependency in `environment.yml`; run `playwright install chromium` once.

Decisions and their reasoning are in `docs/DECISIONS.md`.

**Synthetic data — not Opendoor data.**
