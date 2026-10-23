# CLAUDE.md

Behavioral guidelines to reduce common LLM coding mistakes. Merge with project-specific instructions as needed.

**Tradeoff:** These guidelines bias toward caution over speed. For trivial tasks, use judgment.

## 1. Think Before Coding

**Don't assume. Don't hide confusion. Surface tradeoffs.**

Before implementing:
- State your assumptions explicitly. If uncertain, ask.
- If multiple interpretations exist, present them - don't pick silently.
- If a simpler approach exists, say so. Push back when warranted.
- If something is unclear, stop. Name what's confusing. Ask.

## 2. Simplicity First

**Minimum code that solves the problem. Nothing speculative.**

- No features beyond what was asked.
- No abstractions for single-use code.
- No "flexibility" or "configurability" that wasn't requested.
- No error handling for impossible scenarios.
- If you write 200 lines and it could be 50, rewrite it.

Ask yourself: "Would a senior engineer say this is overcomplicated?" If yes, simplify.

## 3. Surgical Changes

**Touch only what you must. Clean up only your own mess.**

When editing existing code:
- Don't "improve" adjacent code, comments, or formatting.
- Don't refactor things that aren't broken.
- Match existing style, even if you'd do it differently.
- If you notice unrelated dead code, mention it - don't delete it.

When your changes create orphans:
- Remove imports/variables/functions that YOUR changes made unused.
- Don't remove pre-existing dead code unless asked.

The test: Every changed line should trace directly to the user's request.

## 4. Goal-Driven Execution

**Define success criteria. Loop until verified.**

Transform tasks into verifiable goals:
- "Add validation" → "Write tests for invalid inputs, then make them pass"
- "Fix the bug" → "Write a test that reproduces it, then make it pass"
- "Refactor X" → "Ensure tests pass before and after"

For multi-step tasks, state a brief plan:
```
1. [Step] → verify: [check]
2. [Step] → verify: [check]
3. [Step] → verify: [check]
```

Strong success criteria let you loop independently. Weak criteria ("make it work") require constant clarification.

---

**These guidelines are working if:** fewer unnecessary changes in diffs, fewer rewrites due to overcomplication, and clarifying questions come before implementation rather than after mistakes.

---

## CONTEXT
- Business math: profit = volume × contribution margin − OpEx − financing. OpEx ≈ 2.4% and interest ≈ 2% of revenue at a $9B run rate, so contribution margin must stay above ~4.5%. Every 100 bps ≈ $90M/year.
- Contribution margin is lagging (only computed on sold homes). Mispricing is baked in at purchase and shows up months later. Goal: cut that lag from months to days using leading indicators.
- The agent reads funnel leading indicators by segment, separates seasonality from drift, detects adverse selection disguised as "great conversion", ranks actions by $ of contribution margin at risk, and writes a weekly brief where every number traces to a governed metric/query ID.

## NON-NEGOTIABLE RULES
1. Every screen, brief and README says "Synthetic data — not Opendoor data."
2. Deterministic detection first, LLM second. The LLM never computes numbers.
3. Every number in a brief carries a query ID; the agent abstains when data is insufficient.
4. Expected seasonality (spring peak, ~500 bps Q2→Q3 margin dip) must NOT alert.

## API KEY AND BUDGET RULES (I pay per token for the app's API calls)
1. The app's key lives ONLY in .env as MARGIN_RADAR_API_KEY. Load with python-dotenv and pass explicitly: anthropic.Anthropic(api_key=os.environ["MARGIN_RADAR_API_KEY"]). Never use the name ANTHROPIC_API_KEY. Never print, log or commit the key. .env stays in .gitignore.
2. Models via env: CLAUDE_MODEL_DEV (default "claude-haiku-5-5") for all development and debugging; CLAUDE_MODEL_FINAL (default "claude-sonnet-5-5") only for the final eval and the sample brief.
3. Record/replay cache: every API response cached on disk keyed by hash of (model, system, messages, tools). Identical reruns cost $0. REPLAY=1 forbids live calls.
4. `make demo`, the API and the dashboard ALWAYS run in REPLAY mode. They never call Claude live.
5. pytest never makes live API calls: mock the client or use recorded fixtures.
6. Use prompt caching on the system prompt and tool definitions.
7. Log input/output tokens per call to data/token_log.jsonl; eval reports show total tokens and estimated cost. Hard cap MAX_API_CALLS per run (default 50); abort cleanly when hit.
8. Before any step that will make more than 20 live calls, print the planned call count and ask me first.

## SKILLS TO USE
- dbt work → dbt agent skills (analytics engineering + building-dbt-semantic-layer). Ignore dbt skills that need the paid dbt platform.
- Claude API code → the claude-api skill
- UI → frontend-design; browser checks → webapp-testing
- All code → test-driven-development; debugging → systematic-debugging; reviews → requesting-code-review

## STACK (all free/open source)
Python 3.11 (conda env "margin-radar"), DuckDB, dbt-duckdb + dbt-metricflow, statsmodels, anthropic SDK, python-dotenv, pytest, FastAPI, Vite + React + TypeScript + Tailwind + Recharts.

## LAYOUT
/generator /dbt_project /detector /agent /eval /api /web /briefs /tests /docs, Makefile with `make demo`, `make eval`, `make test`.
