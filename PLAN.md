# Margin Radar Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A cohort early-warning and action agent for an iBuyer, built on synthetic data. It spots contribution-margin (CM) erosion by segment from funnel leading indicators within days of onset instead of months, ranks actions by $ of CM at risk, and writes a weekly brief where every number traces to a governed query ID.

**Architecture:** A seeded Python generator writes home-level raw tables into DuckDB, with three injected scenarios plus a control run. dbt builds point-in-time weekly segment marts and a MetricFlow semantic layer, and a thin governed query layer turns every metric read into a logged, ID'd query. A deterministic detector (seasonal baseline from STL, then CUSUM drift and rule-based classification) produces ranked alerts. Claude only writes the narrative, by referencing fact IDs; it never writes numerals. A renderer and grounding validator fill in the numbers, and a record/replay LLM cache makes the demo, API, dashboard and tests free to run.

**Tech Stack:** Python 3.11 (conda env `margin-radar`), DuckDB, dbt-duckdb, dbt-metricflow, statsmodels, pandas, anthropic SDK, python-dotenv, pytest, FastAPI + uvicorn, Vite + React + TypeScript + Tailwind + Recharts, Playwright (browser checks), GitHub Actions → GitHub Pages.

**Spec:** `CLAUDE.md` (sections CONTEXT, NON-NEGOTIABLE RULES, API KEY AND BUDGET RULES, SKILLS TO USE, STACK, LAYOUT). Brainstorming was skipped at the user's request, so the design decisions below that the spec doesn't pin down are the planner's calls. Each one is marked *(planner's call)* where it first appears.

## Global Constraints

- Banner string, exact: `Synthetic data — not Opendoor data.` It must appear on every web page (in the layout component), at the top of every brief (`.md` and `.json`), in README, and in the API `/api/meta` response. Constant: `SYNTHETIC_BANNER` in `common/banner.py`. The web app mirrors it in `web/src/banner.ts`, and a test checks the two match.
- Deterministic detection first. The LLM never computes or writes numbers. Every number in a brief carries a query ID. The agent abstains when data is insufficient.
- Expected seasonality must NOT alert: a spring volume peak and a ~500 bps Q2→Q3 CM dip.
- Business constants (`common/business.py`): `RUN_RATE_USD = 9_000_000_000`, `OPEX_PCT = 0.024`, `INTEREST_PCT = 0.02`, `CM_FLOOR_PCT = 0.045`, `USD_PER_100BPS_YEAR = 90_000_000`.
- API key: read only from `.env` as `MARGIN_RADAR_API_KEY` via python-dotenv and passed as `anthropic.Anthropic(api_key=os.environ["MARGIN_RADAR_API_KEY"])`. The string `ANTHROPIC_API_KEY` must not appear anywhere in the repo. The key is never printed, logged or committed.
- Models: `CLAUDE_MODEL_DEV` (default `claude-haiku-5-5`) for everything except the final eval and the sample brief, which use `CLAUDE_MODEL_FINAL` (default `claude-sonnet-5-5`).
- LLM cache key: sha256 of canonical JSON of `(model, system, messages, tools)`. `REPLAY=1` forbids live calls. `make demo`, the API and the dashboard always set `REPLAY=1`.
- pytest never makes live API calls. `tests/conftest.py` sets `REPLAY=1` and deletes `MARGIN_RADAR_API_KEY` from the environment for the whole session.
- Prompt caching (`cache_control: {"type": "ephemeral"}`) goes on the system prompt and the last tool definition.
- Token log: one JSON line per call in `data/token_log.jsonl` (gitignored). `MAX_API_CALLS` defaults to 50 per run; hitting it raises `BudgetExceeded` and the CLI exits with code 3 and a clear message.
- Any command that would make more than 20 live calls prints the planned count and requires interactive confirmation (or `--yes`). The executing agent must also ask the user in chat before running it.
- Layout: `/generator /dbt_project /detector /agent /eval /api /web /briefs /tests /docs`, plus `common/` for shared constants *(planner's call)*. Makefile targets: `make demo`, `make eval`, `make test`.
- Skills: dbt → `dbt:using-dbt-for-analytics-engineering` and `dbt:building-dbt-semantic-layer`; Claude API → claude-api skill; UI → `frontend-design:frontend-design`; browser checks → `webapp-testing`; all code → `superpowers:test-driven-development`.

## Review Focus

1. **Look-ahead leakage.** A brief or alert for `as_of = w` must not change when data after `w` exists. Expected: metrics and alerts for weeks ≤ w are identical whether the generator run is truncated at w or not. Pinned in Task 7 (`test_no_lookahead`) and Task 10 (`test_alerts_stable_under_truncation`).
2. **Thin or empty segments.** A segment-week with zero offers or zero sales must yield `None` plus an insufficient-data flag, not 0, NaN or a crash, and it must never trigger an alert. Pinned in Task 7 (`test_zero_denominator_returns_none`) and Task 9 (`test_thin_segment_abstains`).
3. **`as_of` with less than 104 weeks of history, or outside the data range.** Expected: a deterministic abstain-only brief, zero LLM calls, and a clear reason. Pinned in Task 9 (`test_short_history_abstains`) and Task 13 (`test_abstain_brief_makes_no_llm_call`).
4. **Replay cache miss under `REPLAY=1`.** Expected: `ReplayMiss` naming the cache key and the command to record it. No live call, no empty brief. Pinned in Task 11 (`test_replay_miss_raises_with_hint`) and Task 17 (`test_api_brief_missing_returns_404_not_live_call`).
5. **The LLM writes a numeral or an unknown fact ID.** Expected: the validator rejects it, there is one retry with the error fed back, then the run fails closed (brief marked `invalid`, not published). Pinned in Task 13 (`test_hallucinated_number_rejected`, `test_unknown_fact_id_rejected`, `test_fails_closed_after_one_retry`).

## Shared design decisions

> **Revised 2026-10-22.** The user's Phase 1 spec replaced the original data design (156 weeks, 24 segments, scenarios S1–S3). Phase 1 below is the as-built version. **Phases 2–5 still reference the old design** (segment ids like `M03-B3`, 104 weeks of history, STL with period 52, 2025 `as_of` weeks) and must be re-planned before Phase 2 starts. The main break: with 78 weeks of data and onset at week 30, there is no prior year to learn seasonality from, so the detector needs a different baseline (for example, peer segments in the same week, since seasonality is shared across markets and an injection is not).

- **Time:** weekly grain, Monday week starts. 78 weeks, numbered from 0, with week 0 = `2025-01-06`; data cutoff `2026-07-05`. *(user)*
- **Segments:** 6 markets `M01..M06` × 3 price bands by model valuation (`B1 <$300K`, `B2 $300–450K`, `B3 >$450K`) × 2 products (`cash`, `CNML`), giving 36 segments. Segment id is `M02-B2-cash`. *(user: counts; planner: names and thresholds)* Both products have the same economics; only the mix differs (75/25) *(planner's call)*.
- **Scale:** ~20.5K offers per run, ~6.4K closes, ~4.9K resales by the cutoff. That's about $1.6B a year of resale revenue, not $9B. Dollar figures later must either scale to the $9B run rate or be labeled sample-scale. **Decide before Phase 3.**
- **Funnel per home** (`raw.homes`, one row per offer; nullable timestamps; NaT = not happened by the cutoff):
  - offer → contract → close → assessment → renovation start/complete → list → first buyer offer → resale.
  - Outcomes: `seller_declined`, `fell_through`, `company_declined` (from the pre-close inspection, so it lands between contract and close), `closed`, and `open` for offers unresolved at the cutoff.
  - Price cuts are events in `raw.price_cuts`.
  - Both tables carry `run_id ∈ {injected, control}`.
- **Seasonality:** offers peak in mid-April (+15% around the yearly average). Days to first buyer offer are fastest in April and slowest in October. Realized price against the seasonally naive model valuation varies by resale month. The result, on the control run at seed 42: overall margin 5.5%, 2025 Q2 7.9% → Q3 3.1% (477 bps dip).
- **Scenarios** (`injected` run, seed 42, all from week 30 = `2025-08-04`, all settable by CLI flag):
  - **A:** market `M02`, days to first buyer offer ×1.40 for listings from week 30. Showings to first offer stay the same, so showings per week fall.
  - **B:** band `B2`, offer→contract conversion ×1.25 for offers from week 30 at unchanged spread, and resale ×0.97 against the model for the same homes (adverse selection).
  - **C:** market `M05`, renovation actual ×1.18 for renovations starting from week 30.
- **Control:** the same seed with no injections. All random draws are taken up front, so homes outside a scenario's scope are identical between runs, and tests assert this.
- **Ground truth** (`data/ground_truth.json`, never loaded into DuckDB): the margin-visible week is the first resale week where the scope's sold-cohort margin, with that scenario run alone, is ≥ 50 bps below control for 2 consecutive weeks. Seed 42: A visible at week 39 (lag 9 weeks), B at week 47 (lag 17), C at week 46 (lag 16).
- **Headline KPIs:** *detection delay* = first alert week − `start_week` (target ≤ 21 days). *Lead time* = `cm_first_visible_week` − first alert week.

---

## Phase 1: Generator + 3 injected scenarios + control run ✅ built 2026-10-22

**DoD (met):** `make data` writes `data/parquet/{injected,control}/{homes,price_cuts}.parquet`, `data/radar.duckdb` (`raw.homes` and `raw.price_cuts` with `run_id`) and `data/ground_truth.json`. `make test` gives 49 passed.

**Files:** `common/{banner,business}.py`, `generator/{config,scenarios,simulate,metrics,ground_truth,io,__main__}.py`, `tests/conftest.py`, `tests/test_scaffold.py`, `tests/generator/test_{volumes,funnel,margin,seasonality,injections,ground_truth,cli}.py`, `environment.yml`, `pyproject.toml`, `Makefile`.

**Interfaces later phases rely on:**
- `generator.simulate.simulate(seed: int, scenarios: Sequence[Scenario] = (), cutoff_week: int = 78) -> SimOutput(homes, price_cuts)`. `cutoff_week` gives point-in-time truncation for no-look-ahead tests.
- `generator.scenarios.Scenario(name, scope_type, scope, start_week, effects)` and `default_scenarios(...)`.
- `generator.metrics.contribution_margin_usd(homes)` and `sold_cohort_cm(homes)`. CM = resale − (offer − 5% fee) − actual renovation − holding − selling (3%). Financing is excluded. dbt must reproduce this (parity test in Phase 2).
- `generator.ground_truth.compute_ground_truth(seed, scenarios) -> list[dict]`.
- CLI: `python -m generator --seed 42 --out-dir data [--inject A,B,C] [--a-market M02 --a-start-week 30 --b-band B2 --b-start-week 30 --c-market M05 --c-start-week 30]`.


## Phase 2: dbt + semantic layer

**Phase DoD:** `make build` (`dbt build` + `mf validate-configs`) is green on both runs. `pytest tests/dbt tests/governed` passes, including the MetricFlow parity check and the no-look-ahead test. Every metric used downstream is defined in `dbt_project/models/semantic/*.yml`.

### Task 5: dbt project, staging and weekly segment mart

Use `dbt:using-dbt-for-analytics-engineering`.

**Files:** Create `dbt_project/dbt_project.yml`, `dbt_project/profiles.yml` (duckdb, `path: "{{ env_var('MR_DB_PATH') }}"`), `models/staging/{_sources.yml,stg_offers.sql,stg_homes.sql}`, `models/marts/{fct_offers.sql,fct_homes.sql,mart_segment_week.sql,metricflow_time_spine.sql,_marts.yml}`, `tests/dbt/test_marts.py`. Modify the `Makefile` `build:` target.

**Interfaces:**
- Produces: `mart_segment_week` has one row per (segment, market, band, week) for all 24 × 156 combinations, zero-filled counts, with columns `leads, offers, accepted, acquisitions, acquisition_volume_usd, offer_premium_bps_sum, offer_premium_n, repair_overrun_sum, repair_overrun_n, active_listings, listings_with_cut, dom_sum, dom_n, list_to_purchase_bps_sum, list_to_purchase_n, sold, cm_usd_sum, revenue_usd_sum, unsold_inventory_usd` (purchase value of homes acquired ≤ w and not sold by w). These are numerators and denominators only; ratios belong to the semantic layer. Each event is attributed to its own event week. Active-listing state at week w uses only dates ≤ w.

- [ ] **Step 1:** Write `tests/dbt/test_marts.py`. It runs `dbt build` against a tmp copy of a generated DB via `MR_DB_PATH`.
  - `test_mart_grain_complete`: row count == 24 × 156, and (segment, week) is unique.
  - `test_counts_reconcile`: `sum(acquisitions)` == `count(*)` from `raw.homes`.
  - Plus dbt schema tests in `_marts.yml`: `unique_combination_of_columns`, `not_null`, `accepted_values` for band.
- [ ] **Step 2:** Run `pytest tests/dbt/test_marts.py -v`. Expected: FAIL.
- [ ] **Step 3:** Implement the models. The time spine is day grain covering 2023-01-01 to 2026-06-30.
- [ ] **Step 4:** Run. Expected: PASS, and `dbt build` reports 0 errors.
- [ ] **Step 5:** Commit `feat(dbt): staging and weekly segment mart`.

### Task 6: Semantic layer (MetricFlow)

Use `dbt:building-dbt-semantic-layer`. Only local `mf` CLI, no paid platform.

**Files:** Create `dbt_project/models/semantic/segment_week.yml` (semantic model on `mart_segment_week` with entity `segment`, time dimension `week`, dimensions `market` and `band`) and `dbt_project/models/semantic/metrics.yml`, plus `tests/dbt/test_semantic.py`.

**Interfaces:**
- Produces these metrics. Ratio metrics are numerator/denominator measures; the rest are simple.

| metric | type | definition |
|---|---|---|
| `offer_acceptance_rate` | ratio | accepted / offers |
| `offer_premium_vs_avm_bps` | ratio | offer_premium_bps_sum / offer_premium_n |
| `repair_overrun_pct` | ratio | repair_overrun_sum / repair_overrun_n |
| `days_on_market` | ratio | dom_sum / dom_n |
| `price_cut_rate` | ratio | listings_with_cut / active_listings |
| `list_to_purchase_bps` | ratio | list_to_purchase_bps_sum / list_to_purchase_n |
| `acquisitions` | simple | sum acquisitions |
| `acquisition_volume_usd` | simple | sum acquisition_volume_usd |
| `contribution_margin_pct` | ratio | cm_usd_sum / revenue_usd_sum |
| `unsold_inventory_usd` | simple | sum unsold_inventory_usd |

- [ ] **Step 1:** Write the tests:
  - `test_mf_validate`: `mf validate-configs` exits 0.
  - `test_mf_query_cm`: `mf query --metrics contribution_margin_pct --group-by metric_time__quarter` on the control run returns Q2−Q3 2024 ≈ 500 ± 75 bps.
- [ ] **Step 2:** Run. Expected: FAIL.
- [ ] **Step 3:** Write the YAML.
- [ ] **Step 4:** Run. Expected: PASS.
- [ ] **Step 5:** Commit `feat(dbt): MetricFlow semantic layer with governed metrics`.

### Task 7: Governed query layer with query IDs

**Files:** Create `detector/__init__.py`, `detector/governed.py`, `tests/governed/test_governed.py`

**Interfaces:**
- Consumes: the `mart_segment_week` columns and the metric definitions from Task 6. Load the metric→(numerator, denominator) map by parsing `metrics.yml` and the semantic model YAML with PyYAML, so definitions live in one place.
- Produces:

```python
@dataclass(frozen=True)
class MetricResult:
    query_id: str                 # "Q" + sha256(run_id|metric|segment|start|end|as_of|sql)[:10]
    metric: str
    segment: str | None           # None = all segments; "M05" = market rollup
    as_of: date
    weeks: tuple[date, ...]
    values: tuple[float | None, ...]   # None where denominator < MIN_N[metric]
    n: tuple[int, ...]            # denominators
    sql: str

class GovernedStore:
    def __init__(self, db_path: str, run_id: str, log_path: str | None = None): ...
    def metric(self, metric: str, segment: str | None, start: date, end: date, as_of: date) -> MetricResult
    def get(self, query_id: str) -> MetricResult       # from in-memory/log registry
    def all(self) -> tuple[MetricResult, ...]
    def register_derived(self, label: str, value: float, unit: str, inputs: tuple[str, ...], formula: str) -> str  # returns "D…" id; logged like queries
```

`MIN_N = {"offer_acceptance_rate": 30, "contribution_margin_pct": 10, default: 10}`. `end` is clamped to `as_of`. SQL is parameter-free text (values inlined from a whitelist of metric and segment names, with dates validated as `date`), so the SQL string is reproducible and hashable. Unknown metric or segment raises `ValueError`.

- [ ] **Step 1:** Write the tests:
  - `test_query_id_deterministic`: the same call twice gives the same `query_id`.
  - `test_query_id_changes_with_as_of`.
  - `test_zero_denominator_returns_none`: a segment-week with 0 offers gives `values[i] is None` *(Review Focus 2)*.
  - `test_parity_with_metricflow`: for 3 metrics × 2 segments × a 4-week window, values match `mf query ... --where` within 1e-9.
  - `test_no_lookahead`: build from `--truncate-at 2025-05-05` vs the full run; all metrics for weeks ≤ 2025-05-05 with `as_of=2025-05-05` are equal *(Review Focus 1)*.
  - `test_rejects_unknown_metric`: raises `ValueError`.
  - `test_log_written`: with `log_path`, each call appends one JSONL line containing `query_id`, `sql`, `values`.
- [ ] **Step 2:** Run. Expected: FAIL.
- [ ] **Step 3:** Implement.
- [ ] **Step 4:** Run `make build && pytest tests/governed -v`. Expected: PASS.
- [ ] **Step 5:** Commit `feat(governed): ID'd, logged metric queries with MetricFlow parity`.

---

## Phase 3: Detector

**Phase DoD:** `python -m detector --db data/scenarios.duckdb --as-of 2025-08-04` writes `data/out/scenarios/2025-08-04/alerts.json`. `pytest tests/detector` passes. On seed 42: all 3 scenarios detected with detection delay ≤ 21 days; lead time ≥ 8 weeks for S1, ≥ 6 for S3 and ≥ 2 for S2; and **zero alerts on the control run for every 2025 `as_of` week** (the seasonality trap).

### Task 8: Seasonal baseline and residuals

**Files:** Create `detector/config.py`, `detector/seasonal.py`, `tests/detector/test_seasonal.py`

**Interfaces:**
- Produces: `fit_expected(series: pd.Series, as_of: date) -> SeasonalFit | Insufficient`. `series` is weekly-indexed and may contain NaN. `SeasonalFit(expected: pd.Series, residual: pd.Series, sigma: float, eval_start: date)` is frozen. `Insufficient(reason: str)`.
- Algorithm *(planner's call)*. The reference window is all weeks ≤ `as_of − EVAL_WEEKS` (`EVAL_WEEKS = 13`). Fit `statsmodels.tsa.seasonal.STL(period=52, robust=True)` on the reference window, with gaps interpolated. Expected over the eval window = last reference trend value + the seasonal component from 52 weeks earlier. `sigma` = 1.4826 × MAD of reference residuals. Return `Insufficient` when the reference window has < 104 weeks or > 20% NaN.
- Constants in `detector/config.py`: `EVAL_WEEKS = 13`, `MIN_HISTORY_WEEKS = 104`, `CUSUM_K = 0.5`, `CUSUM_H = 5.0`, `MIN_RECENT_N_WEEKS = 3`. Tuning is allowed in Task 10, but only by editing this file.

- [ ] **Step 1:** Write the tests on synthetic series:
  - `test_pure_seasonal_small_residuals`: sine plus noise, |residual| / sigma < 3 everywhere.
  - `test_level_shift_large_residuals`: a +4σ step in the eval window gives mean z > 3.
  - `test_short_history_insufficient` *(Review Focus 3)*.
  - `test_q3_cm_dip_not_anomalous`: control `M02-B2` CM at `as_of=2025-08-25` has a mean |z| < 2.
- [ ] **Step 2:** Run. Expected: FAIL.
- [ ] **Step 3:** Implement.
- [ ] **Step 4:** Run. Expected: PASS.
- [ ] **Step 5:** Commit `feat(detector): STL seasonal baseline with abstention`.

### Task 9: Drift tests and classification rules

**Files:** Create `detector/rules.py`, `detector/models.py`, `tests/detector/test_rules.py`

**Interfaces:**
- Consumes: `GovernedStore.metric`, `fit_expected`.
- Produces (in `detector/models.py`):

```python
@dataclass(frozen=True)
class Signal:          # one metric's evidence
    metric: str; segment: str; direction: Literal["+", "-"]
    observed: float; expected: float; z: float; cusum_week: date | None
    query_id: str
@dataclass(frozen=True)
class Alert:
    alert_id: str      # "A" + sha256(run_id|kind|scope|onset_week)[:8]; stable across as_of weeks
    kind: Literal["adverse_selection", "demand_softening", "repair_cost_drift"]
    scope: str         # segment id, or market id for demand_softening
    onset_week: date   # first CUSUM crossing
    signals: tuple[Signal, ...]
@dataclass(frozen=True)
class Abstention:
    scope: str; metric: str | None; reason: str
@dataclass(frozen=True)
class DetectorResult:
    run_id: str; as_of: date; alerts: tuple[Alert, ...]; abstentions: tuple[Abstention, ...]
```

`detect_signals(store, segment, as_of) -> tuple[list[Signal], list[Abstention]]` runs a one-sided CUSUM on standardized eval-window residuals for each leading metric. `classify(signals_by_segment, store, as_of) -> list[Alert]` applies the rules:
- **adverse_selection:** acceptance `+` AND premium `+` in the same segment, AND the market's other bands do not show acceptance `+`. Acceptance `+` alone is never an alert ("genuine demand").
- **demand_softening:** `days_on_market +` AND `price_cut_rate +` in ≥ 2 bands of one market. Scope is the market.
- **repair_cost_drift:** `repair_overrun_pct +`.
- `contribution_margin_pct` is never an alert trigger. It is reported as context only, because it lags.

- [ ] **Step 1:** Write the tests, using `GovernedStore` on the seed-42 DBs:
  - `test_s1_detected`: `as_of=2025-03-24` includes an `adverse_selection` alert on `M03-B3` with onset ≤ 2025-03-24.
  - `test_s2_detected_despite_summer`: `as_of=2025-06-23` includes `demand_softening` on `M05`.
  - `test_s3_detected`: `as_of=2025-04-28` includes `repair_cost_drift` on `M01-B1`.
  - `test_acceptance_up_alone_no_alert`: a synthetic signals dict with only acceptance `+` gives `[]`.
  - `test_control_zero_alerts_all_2025`: for every Monday in 2025, the control run gives `alerts == ()`. This is the seasonality trap: spring peak plus the Q3 dip.
  - `test_thin_segment_abstains` *(Review Focus 2)*: a segment whose recent 4 weeks have < `MIN_RECENT_N_WEEKS` non-None values yields an `Abstention` and no Signal.
  - `test_short_history_abstains`: `as_of=2024-06-03` gives no alerts and one global `Abstention(scope="all", reason contains "104 weeks")` *(Review Focus 3)*.
- [ ] **Step 2:** Run. Expected: FAIL.
- [ ] **Step 3:** Implement. If control alerts appear, use superpowers:systematic-debugging, and tune only `detector/config.py`.
- [ ] **Step 4:** Run. Expected: PASS.
- [ ] **Step 5:** Commit `feat(detector): CUSUM drift and adverse-selection classification`.

### Task 10: $ at risk, action ranking, detector CLI

**Files:** Create `detector/impact.py`, `detector/actions.py`, `detector/__main__.py`, `tests/detector/test_impact.py`. Modify the `Makefile` `detect:` target.

**Interfaces:**
- Produces: `RankedAction(rank, alert_id, kind, scope, usd_at_risk: float, components: tuple[Component, ...], action: str, owner: str)` and `Component(label, value, unit: Literal["usd","bps","count","pct","days"], query_id)`. Then `rank_actions(result: DetectorResult, store) -> tuple[RankedAction, ...]`, sorted by `usd_at_risk` descending.
- **$ at risk** *(planner's call)*: `erosion_bps × (exposed_inventory_usd + FORWARD_WEEKS × trailing_4w_weekly_acq_usd) / 1e4`, with `FORWARD_WEEKS = 13`. `erosion_bps` per kind:
  - adverse_selection: excess `offer_premium_vs_avm_bps` (observed − expected).
  - demand_softening: excess `list_to_purchase_bps` decline.
  - repair_cost_drift: excess `repair_overrun_pct` × est_repair / purchase price, in bps.
  - `exposed_inventory_usd` = metric `unsold_inventory_usd` for the scope at `as_of` (Task 5/6).
- Every component is a `MetricResult`-backed number carrying its `query_id`. The arithmetic is done here, in Python, and logged as derived facts whose `query_id` is `"D" + sha256(formula|input query_ids)[:10]`. These are registered via `store.register_derived(...)` (Task 7).
- Action catalog (deterministic text):
  - adverse_selection → "Tighten offer premium in {scope} by {excess_bps} bps; review pricing model inputs" (owner Pricing).
  - demand_softening → "Slow acquisitions in {market}; reprice aged inventory" (owner Ops/Resale).
  - repair_cost_drift → "Re-baseline repair estimates in {scope}; add inspection buffer" (owner Renovation).
  - Placeholders are filled by fact IDs, not raw numbers.
- CLI: `python -m detector --db PATH --run-id ID --as-of DATE [--out DIR]` writes `alerts.json` (DetectorResult plus RankedActions) and `queries.jsonl` under `data/out/{run_id}/{as_of}/`. Detector-only, so it's cheap. `make detect` runs every 2025 Monday for both runs.

- [ ] **Step 1:** Write the tests:
  - `test_ranking_sorted_desc`.
  - `test_every_component_has_query_id`: every component `query_id` resolves via `store.get`.
  - `test_derived_fact_traces_inputs`: a derived fact's inputs are all existing query IDs.
  - `test_usd_at_risk_matches_formula`: a hand-built fixture with known inputs gives the exact expected $.
  - `test_alerts_stable_under_truncation` *(Review Focus 1)*: the `alert_id` set for `as_of=2025-05-05` is equal on truncated vs full data.
  - `test_kpis_seed42`: detection delay ≤ 21 days for all 3; lead time S1 ≥ 8 weeks, S3 ≥ 6, S2 ≥ 2. This uses `eval.kpis.lead_time` from Task 14, so write a minimal version of that function here and let Task 14 extend it.
- [ ] **Step 2:** Run. Expected: FAIL.
- [ ] **Step 3:** Implement.
- [ ] **Step 4:** Run `pytest tests/detector -v && make detect`. Expected: PASS, and alerts.json exists for 52 × 2 weeks.
- [ ] **Step 5:** Commit `feat(detector): $-at-risk ranking and CLI`.

---

## Phase 4: Claude agent + grounded briefs

Use the claude-api skill for all SDK code: tool use, prompt caching, current model IDs and pricing.

**Phase DoD:** `pytest tests/agent` passes with zero live calls. `python -m agent brief --run scenarios --as-of <S1 detection week>` run live once with the dev model writes `briefs/scenarios/<as_of>.{md,json}` that passes the grounding validator. Rerunning it with `REPLAY=1` reproduces the brief byte-for-byte at $0. Then the final sample briefs are recorded with `CLAUDE_MODEL_FINAL` and committed, along with their `data/llm_cache/` entries.

### Task 11: LLM client wrapper: key, models, cache/replay, budget, token log

**Files:** Create `agent/__init__.py`, `agent/config.py`, `agent/llm.py`, `agent/pricing.py`, `tests/agent/test_llm.py`

**Interfaces:**
- Produces:
  - `model_for(purpose: Literal["dev","final"]) -> str` reads `CLAUDE_MODEL_DEV`/`CLAUDE_MODEL_FINAL` with the spec defaults.
  - `class LLM: __init__(self, model, purpose: Literal["dev","final"], cache_dir="data/llm_cache",  # files under {cache_dir}/{purpose}/ token_log="data/token_log.jsonl", max_calls=int(os.getenv("MAX_API_CALLS", 50)), client_factory=None)` and `create(self, *, system: list[dict], messages: list[dict], tools: list[dict], max_tokens: int) -> dict`. It returns the response as a plain dict (`model_dump()`).
  - Exceptions: `ReplayMiss(key)`, `BudgetExceeded`, `MissingKey`.
  - `cache_key(model, system, messages, tools) -> str` is sha256 of `json.dumps(..., sort_keys=True, separators=(",",":"))`.
  - `estimate_cost(model, usage) -> float | None` uses `PRICES_PER_MTOK[model]` (input, output, cache_write, cache_read). Fill the values from the claude-api skill's pricing reference. An unknown model returns `None`, and reports print "unknown", never $0.
- Behaviour: on a cache hit, return it and log `{replay: true, cost: 0}`. On a miss with `REPLAY=1`, raise `ReplayMiss` whose message includes the key and "record with: REPLAY=0 python -m agent brief ...". On a live miss, increment the call counter; if it exceeds `max_calls` raise `BudgetExceeded` before calling. Then `load_dotenv()`, read `MARGIN_RADAR_API_KEY` (raise `MissingKey` if absent; the message names the variable, never a value), call `anthropic.Anthropic(api_key=os.environ["MARGIN_RADAR_API_KEY"]).messages.create(...)`, write the cache file atomically, and append to the token log: `ts, model, purpose, input_tokens, output_tokens, cache_creation_input_tokens, cache_read_input_tokens, est_cost_usd, replay`. The client is created lazily, only on a live miss, so REPLAY runs never touch the key.
- `with_prompt_caching(system, tools) -> (system, tools)` returns copies with `cache_control: {"type":"ephemeral"}` on the last system block and the last tool.

- [ ] **Step 1:** Write the tests. All use a fake `client_factory`; none touches the network.
  - `test_cache_hit_no_client_call`.
  - `test_replay_miss_raises_with_hint` *(Review Focus 4)*.
  - `test_budget_exceeded_before_call`: `max_calls=2`, 3 distinct misses; the third raises and the fake saw exactly 2 calls.
  - `test_missing_key_message_has_no_value`.
  - `test_key_never_in_logs_or_cache`: set a fake key `"sk-test-SENTINEL"`; after a live (fake) call, neither the cache dir nor the token log contains `SENTINEL`.
  - `test_cache_key_order_insensitive_dicts`.
  - `test_prompt_caching_markers`.
  - `test_token_log_fields`.
  - `test_unknown_model_cost_none`.
  - `test_no_network_in_pytest`: under conftest (`REPLAY=1`, no key), `LLM(...).create` on an uncached request raises `ReplayMiss`.
- [ ] **Step 2:** Run. Expected: FAIL.
- [ ] **Step 3:** Implement.
- [ ] **Step 4:** Run. Expected: PASS.
- [ ] **Step 5:** Commit `feat(agent): record/replay LLM client with budget and token log`.

### Task 12: Agent tools and loop

**Files:** Create `agent/facts.py`, `agent/tools.py`, `agent/prompts.py`, `agent/loop.py`, `tests/agent/test_loop.py`, `tests/agent/fixtures/` (recorded fake responses)

**Interfaces:**
- Consumes: `GovernedStore`, `DetectorResult`, `RankedAction`, `LLM`.
- Produces:
  - `Fact(fact_id: str, query_id: str, label: str, value: float | None, unit: str)`. `fact_id = f"F{query_id}_{k}"`, where `k` is the week index or component name, sanitized to `[A-Za-z0-9_]`.
  - `FactSheet`: an immutable mapping fact_id → Fact, built with `FactSheet.from_detector(result, actions, store)`, plus `.extend(metric_result)`.
  - Tools exposed to Claude, with JSON schemas in `agent/tools.py`:
    - `get_ranked_actions()` → actions with fact IDs, not numbers.
    - `get_metric_series(metric, scope, weeks<=26)` → a list of `{week, fact_id}` and `expected_fact_id`. It calls the store with `as_of` fixed by the loop, never by the model.
    - `get_abstentions()`
    - `get_feedback_summary()` (stub returns `[]` until Task 16)
    - `submit_brief(brief)`, where `brief` has the schema `{headline: str, sections: [{alert_id, title, what_moved, why_not_seasonality, impact, action, confidence: "high"|"medium"|"low"}], watchlist: [str]}`.
  - **The model sees fact IDs and their labels and units, never values** *(planner's call)*. This makes "LLM never computes numbers" structural: the model has no numbers to compute with.
  - `run_agent(llm, store, result, actions, max_turns=8) -> dict` returns the submitted brief JSON. Each loop turn is one `llm.create`. Stop on `submit_brief`. Exceeding `max_turns` raises `AgentDidNotSubmit`.
  - System prompt (in `agent/prompts.py`) states the role, that it must reference numbers only as `{{fact_id}}`, that it must never write digits except inside those tokens and segment/market IDs, that it must not claim causes beyond the alert kind's mechanism, that it must explain why each alert isn't seasonality using the expected-vs-observed facts, and that abstentions are reported, not filled in.

- [ ] **Step 1:** Write the tests, using a scripted fake LLM that returns fixture tool_use blocks.
  - `test_loop_calls_tools_then_submits`.
  - `test_tool_results_contain_no_numeric_values`: the serialized tool results match no `\d` outside fact IDs, segment IDs and ISO dates.
  - `test_as_of_not_overridable`: a model-supplied `as_of` arg is rejected by the schema.
  - `test_max_turns_raises`.
- [ ] **Step 2:** Run. Expected: FAIL.
- [ ] **Step 3:** Implement.
- [ ] **Step 4:** Run. Expected: PASS.
- [ ] **Step 5:** Commit `feat(agent): fact-ID tool loop`.

### Task 13: Renderer, grounding validator, abstention, brief CLI

**Files:** Create `agent/render.py`, `agent/validate.py`, `agent/__main__.py`, `tests/agent/test_render_validate.py`. Modify the `Makefile` `briefs:` target.

**Interfaces:**
- Produces:
  - `validate(brief: dict, facts: FactSheet, allowed_ids: set[str]) -> list[str]` (an empty list means valid). Errors include: a digit outside `{{…}}` that isn't an allowed segment/market ID or ISO date; an unknown fact ID; a fact whose value is `None`; a section `alert_id` not in the detector result; or a ranked alert missing from the brief.
  - `render(brief, facts, result, actions) -> tuple[str, dict]` produces markdown and JSON. Markdown layout:
    1. Banner line.
    2. Run/as_of.
    3. Headline.
    4. One section per alert, with number tokens rendered as `value` plus a superscript citation `[Q…]`.
    5. A deterministic "Ranked actions" table (rank, scope, $ at risk, action, owner, query IDs).
    6. A deterministic "Abstentions" section.
    7. A "Feedback since last brief" section (empty until Task 16).
    8. An appendix query table (query_id, metric, scope, window, sql sha256[:8]).
  - Formatting by unit: usd → `$1.2M`, bps → `+312 bps`, pct → `3.4%`, count → `1,204`, days → `41 days`.
  - JSON holds the same content plus `banner`, `status: "valid"|"invalid"|"abstain"`, `model`, and `facts_used`.
  - `make_brief(run_id, db, as_of, purpose) -> Path`:
    - If the detector result has a global abstention, write an abstain-only brief **without any LLM call**.
    - If there are no alerts, write a deterministic "No alerts; seasonality within expected band" brief with key facts. This is also no LLM call *(planner's call: saves tokens; the LLM adds nothing when there's nothing to explain)*.
    - Otherwise run the agent and validate. On errors, do one retry with the errors appended as a user message. If it still fails, write status `invalid` to `briefs/{run}/{as_of}.invalid.json` and exit 2.
  - CLI: `python -m agent brief --run scenarios --as-of 2025-03-24 [--final] [--yes]`.

- [ ] **Step 1:** Write the tests:
  - `test_banner_first_line`.
  - `test_hallucinated_number_rejected`: "acceptance rose 12%" fails *(Review Focus 5)*.
  - `test_unknown_fact_id_rejected` *(Review Focus 5)*.
  - `test_segment_ids_and_dates_allowed`.
  - `test_fails_closed_after_one_retry`: a fake LLM always returns a bad brief; exactly 2 agent runs, an `.invalid.json` is written, and no `.md` *(Review Focus 5)*.
  - `test_abstain_brief_makes_no_llm_call`: `as_of=2024-06-03` with an LLM whose factory raises if called *(Review Focus 3)*.
  - `test_no_alert_brief_makes_no_llm_call`: the control run at `2025-08-25`.
  - `test_every_rendered_number_has_citation`: in the rendered markdown, every number is followed by a `[Q…]` or `[D…]` citation, or sits in the ranked-actions table row that carries its IDs.
  - `test_missing_ranked_alert_rejected`.
- [ ] **Step 2:** Run. Expected: FAIL.
- [ ] **Step 3:** Implement.
- [ ] **Step 4:** Run `pytest tests/agent -v`. Expected: PASS.
- [ ] **Step 5:** Live dev smoke test. **Ask the user first.** This is ≤ 16 calls: 1 brief × ≤ 8 turns × ≤ 2 attempts. Run `REPLAY=0 python -m agent brief --run scenarios --as-of 2025-03-24` with the dev model. Then rerun with `REPLAY=1` and diff the output. Expected: identical, with a `replay: true` token log line.
- [ ] **Step 6:** Commit `feat(agent): grounded rendering, validator, abstention, brief CLI`. Commit the cache files created in Step 5 only if this is the final model. Dev-model cache (`data/llm_cache/dev/`) stays local and gitignored.

**Demo brief weeks** *(planner's call; fixed after Phase 3)*:
- The first detection week of each scenario (expected 2025-03-24, 2025-04-28, 2025-06-23).
- Control `2025-08-25` (no-alert brief, $0).
- `2024-06-03` (abstain, $0).

The three scenario briefs are the only LLM spend. Recording them with the final model is ≤ 48 calls, which is above 20, so the executor **must print the count and ask the user** before running `make record-final`.

---

## Phase 5: Evaluation harness

**Phase DoD:** `make eval` (REPLAY) writes `eval/reports/latest.md` and `.json` with detector metrics across seeds 1–10, brief metrics, and token/cost totals. The detector gates hold: recall 30/30 scenario-seeds, control alerts 0 across 10 seeds × 52 weeks, false alerts on non-injected scopes ≤ 1 per 10 seed-runs, median detection delay ≤ 21 days. Brief gates hold: grounding 100%, abstention correct 100%, top-ranked action names the injected scope for each scenario brief.

### Task 14: Detector evaluation across seeds

**Files:** Create `eval/__init__.py`, `eval/kpis.py`, `eval/detector_eval.py`, `tests/eval/test_detector_eval.py`

**Interfaces:**
- Produces: `lead_time(truth, alerts_by_week, cm_series) -> dict[str, {detect_week, breach_week, delay_days, lead_days}]` and `run_detector_eval(seeds=range(1,11), out="data/eval") -> DetectorReport` with `recall, control_alerts, false_alerts, median_delay_days, median_lead_days_by_kind, per_seed rows`. It generates each seed with the generator CLI, runs `dbt build` with `MR_DB_PATH`, then the detector for all 2025 Mondays. Results are cached on disk by (seed, run, git tree hash of generator/dbt/detector) so reruns skip work.

- [ ] **Step 1:** Write the tests:
  - `test_lead_time_math`: hand-built truth/alerts/CM give exact delay/lead days.
  - `test_breach_requires_two_consecutive_weeks`.
  - `test_report_gates`: on a 2-seed smoke run (marked `@pytest.mark.slow`), the gate fields exist and control_alerts == 0.
- [ ] **Step 2:** Run. Expected: FAIL.
- [ ] **Step 3:** Implement. If gates fail on seeds 1–10, debug with superpowers:systematic-debugging and tune only `detector/config.py`. Then re-run the Task 9/10 tests.
- [ ] **Step 4:** Run `pytest tests/eval -v -m "slow or not slow"`. Expected: PASS.
- [ ] **Step 5:** Commit `feat(eval): multi-seed detector evaluation with lead-time KPIs`.

### Task 15: Brief evaluation, cost report, live gating

**Files:** Create `eval/brief_eval.py`, `eval/report.py`, `eval/__main__.py`, `tests/eval/test_brief_eval.py`. Modify the `Makefile` targets `eval:` (REPLAY=1) and `record-final:`.

**Interfaces:**
- Produces: `run_brief_eval(weeks, purpose, live: bool) -> BriefReport` with `grounding_rate, abstention_correct, top_action_correct, invalid_count, calls, input_tokens, output_tokens, cache_read_tokens, est_cost_usd | None`. Tokens and cost are summed from `token_log.jsonl` lines tagged with this eval's `run_tag`. `planned_calls(weeks) = n_llm_briefs × 8 × 2`.
- `python -m eval [--live] [--final] [--yes]`: when `--live` and `planned_calls > 20`, print `Planned live calls: N (model M). Proceed? [y/N]` and abort unless `y` or `--yes`.
- `write_report(detector_report, brief_report, path)` produces markdown with the banner, a gates table (PASS/FAIL), KPIs, a tokens table and estimated cost.

- [ ] **Step 1:** Write the tests:
  - `test_planned_calls_prompt_over_20`: monkeypatch `input` → `"n"`; it aborts with exit 0 and no LLM constructed.
  - `test_report_has_banner_and_cost`.
  - `test_cost_unknown_rendered_as_unknown`.
  - `test_eval_replay_mode_default`: no `--live` means `REPLAY=1` is enforced.
- [ ] **Step 2:** Run. Expected: FAIL.
- [ ] **Step 3:** Implement.
- [ ] **Step 4:** Run `pytest tests/eval -v`. Expected: PASS. Then **ask the user**, and run `make record-final`, which does `python -m eval --live --final` (≤ 48 calls). Commit `data/llm_cache/final/` and `briefs/`. Then run `make eval` (REPLAY). Expected: all gates PASS, 0 live calls in the token log.
- [ ] **Step 5:** Commit `feat(eval): brief evaluation, cost report, live-call gating`.

---

## Phase 6: Feedback log

**Phase DoD:** `python -m agent feedback add --alert A… --verdict useful --note "..."` appends to `data/feedback.jsonl`. The next brief's "Feedback since last brief" section lists it deterministically. The eval report shows human precision. `pytest tests/feedback` passes.

### Task 16: Feedback store and its uses

**Files:** Create `agent/feedback.py`, `tests/feedback/test_feedback.py`. Modify `agent/__main__.py` (subcommand), `agent/tools.py` (implement `get_feedback_summary`), `agent/render.py` (feedback section) and `eval/report.py` (human precision).

**Interfaces:**
- Produces: `FeedbackEntry(ts: datetime, alert_id: str, verdict: Literal["useful","false_positive","acted","dismissed"], note: str, user: str)`, frozen. `note` is ≤ 500 chars and `user` ≤ 64 chars, both validated, with control characters stripped. `FeedbackLog(path)` with `.append(entry) -> FeedbackEntry`, `.all() -> tuple[FeedbackEntry, ...]` and `.since(ts) -> tuple`. It is append-only, and a malformed line is skipped with a logged warning that includes the line number. `summary(log, alert_ids) -> list[{alert_id, verdict_counts, last_note_fact?}]`. Notes are shown verbatim in the deterministic section only; they are not passed to the LLM as instructions *(planner's call: avoids prompt injection via notes; the LLM gets only verdict counts)*.
- Alerts with any `false_positive` verdict render with a "disputed" tag. Detection is not suppressed *(planner's call; YAGNI)*.

- [ ] **Step 1:** Write the tests:
  - `test_append_and_read`.
  - `test_rejects_bad_verdict`.
  - `test_note_too_long_rejected`.
  - `test_malformed_line_skipped`.
  - `test_brief_feedback_section_lists_entries`.
  - `test_notes_not_in_llm_tool_result`.
  - `test_human_precision_in_report`: useful / (useful + false_positive).
- [ ] **Step 2:** Run. Expected: FAIL.
- [ ] **Step 3:** Implement.
- [ ] **Step 4:** Run. Expected: PASS. The deterministic brief sections changed, so re-run `make eval` in REPLAY and check whether any LLM cache keys missed. Feedback is only sent to the LLM as counts, which are empty in recorded runs, so the keys should be unchanged. If any miss, **ask the user** before re-recording.
- [ ] **Step 5:** Commit `feat(feedback): append-only feedback log surfaced in briefs and eval`.

---

## Phase 7: Dashboard + static export

Use `frontend-design:frontend-design` for UI and `webapp-testing` for browser checks.

**Phase DoD:**
- `make demo` runs generator → dbt → detector → briefs (REPLAY) → API on :8000 → Vite on :5173 with zero live calls.
- `make export` writes `web/public/data/*.json`, and `npm run build:static` produces `web/dist` that works with no backend.
- Playwright checks pass: the banner is visible on every route; the overview shows ranked actions; segment charts render the expected band and alert marker; brief citations open the query/SQL panel; static mode hides the feedback form.

### Task 17: FastAPI read API + feedback endpoint

**Files:** Create `api/__init__.py`, `api/main.py`, `api/export.py`, `tests/api/test_api.py`

**Interfaces:**
- Produces (JSON):
  - `GET /api/meta` → `{banner, runs, as_of_weeks, brief_weeks, model_final}`
  - `GET /api/alerts?run&as_of` → alerts.json content
  - `GET /api/series?run&metric&scope&as_of` → `{weeks, values, expected, lower, upper, query_id, alerts:[{alert_id, onset_week}]}`. The band is expected ± 2σ from `fit_expected`.
  - `GET /api/kpis?run` → lead-time table from Task 14
  - `GET /api/brief?run&as_of` → brief JSON + markdown, or **404** if none exists. Never generate.
  - `GET /api/query/{query_id}` → MetricResult incl. SQL
  - `POST /api/feedback` → validated `FeedbackEntry`
  - `GET /api/feedback?alert_id`
- On import, `api/main.py` sets `os.environ["REPLAY"]="1"` and never imports `agent.loop`.
- `python -m api.export --out web/public/data` writes the same payloads as static files named `{endpoint}__{params}.json`, plus `manifest.json`.
- Query params are validated against known runs, metrics, scopes and dates, with 422 otherwise. Rate limiting is out of scope for a local demo; record that in README *(planner's call)*.

- [ ] **Step 1:** Write the tests (TestClient):
  - `test_meta_has_banner`.
  - `test_alerts_ok`.
  - `test_unknown_metric_422`.
  - `test_api_brief_missing_returns_404_not_live_call` *(Review Focus 4)*: patch `agent.llm.LLM` to raise if constructed.
  - `test_feedback_post_validates`.
  - `test_replay_forced`.
  - `test_export_writes_manifest`.
- [ ] **Step 2:** Run. Expected: FAIL.
- [ ] **Step 3:** Implement.
- [ ] **Step 4:** Run. Expected: PASS.
- [ ] **Step 5:** Commit `feat(api): read API, feedback endpoint, static export`.

### Task 18: React dashboard

**Files:** Create `web/` (Vite React TS template + Tailwind + Recharts): `src/banner.ts`, `src/data.ts` (fetches from `/api/*` or, when `import.meta.env.VITE_STATIC`, from `data/*.json` via the manifest), `src/components/Layout.tsx` (sticky banner on every route), `src/pages/{Overview,Segment,Brief,Lag}.tsx`, `web/tests/e2e.spec.ts` (Playwright). Add `tests/test_banner_sync.py`, which asserts `web/src/banner.ts` contains `SYNTHETIC_BANNER`.

**Pages** *(planner's call)*:
- **Overview:** a run toggle (scenarios/control), an as_of week slider over 2025, and the ranked-actions table ($ at risk, action, owner, query-ID chips). Plus a national CM chart with the seasonal band, which visibly shows the Q3 dip inside the band and no alert.
- **Segment:** leading-indicator small multiples (observed line, expected band, onset and first-alert markers) with a CM chart below, so the lag between "alert fired" and "CM moved" is visible.
- **Lag:** the headline view. Per scenario, onset → detection → CM breach on a timeline, with days labeled.
- **Brief:** rendered markdown. Clicking a citation opens a side panel with the query's metric, scope, window, values and SQL. It also has a feedback form (hidden when `VITE_STATIC`).

- [ ] **Step 1:** Write the Playwright tests. Run them against `make demo` and, separately, against `vite preview` of the static build.
  - `banner visible on /, /segment/M03-B3, /lag, /brief`.
  - `overview lists M03-B3 adverse_selection at as_of 2025-03-24`.
  - `control run shows "No alerts" at 2025-08-25`.
  - `citation click shows SQL`.
  - `static build has no feedback form`.
- [ ] **Step 2:** Run `cd web && npx playwright test`. Expected: FAIL.
- [ ] **Step 3:** Build the UI.
- [ ] **Step 4:** Run the Playwright tests and `pytest tests/test_banner_sync.py`. Expected: PASS. Take screenshots to `docs/screenshots/`.
- [ ] **Step 5:** Commit `feat(web): dashboard with lag view, citations, feedback`.

### Task 19: `make demo` and `make export` wiring

**Files:** Modify `Makefile`. Create `scripts/demo.sh` and `tests/test_make_demo.py`.

**Interfaces:**
- `make demo` = `REPLAY=1` data → build → detect → briefs → `uvicorn api.main:app` & `npm run dev`.
- `make export` = `python -m api.export` then `npm run build:static` with `VITE_STATIC=1 VITE_BASE=/margin-radar/`.

- [ ] **Step 1:** Write `test_make_demo_dry` (`make -n demo` output contains `REPLAY=1` on every step that runs Python) and `test_demo_zero_live_calls` (slow). It runs the pipeline part of demo without servers, and the token log gains only `replay: true` lines.
- [ ] **Step 2:** Run. Expected: FAIL.
- [ ] **Step 3:** Implement.
- [ ] **Step 4:** Run, then run `make demo` manually and load http://localhost:5173. Expected: PASS and a working UI.
- [ ] **Step 5:** Commit `chore: wire make demo and make export`.

---

## Phase 8: Polish, README, free GitHub Pages deploy

**Phase DoD:**
- `make test` is fully green, with coverage ≥ 80% on `generator detector agent eval api` (`pytest --cov`).
- README starts with the banner, and `test_readme_banner` passes.
- A code review via superpowers:requesting-code-review has no unresolved CRITICAL/HIGH findings.
- The GitHub Pages workflow builds `web/dist` from committed `web/public/data`. After the user approves the push and enables Pages, the public URL loads with the banner and works with no backend.

### Task 20: README, docs, review

**Files:** Create `README.md`, `docs/architecture.md` (mermaid: generator → DuckDB → dbt/MetricFlow → governed store → detector → agent → briefs → API/static → web), `docs/decisions.md` (every *(planner's call)* above, one line each), and `tests/test_docs.py`.

README sections:
1. Banner.
2. A one-paragraph problem statement using the CONTEXT math.
3. Screenshot.
4. A results table, pulled from `eval/reports/latest.json` by a small script, not typed by hand.
5. How it works: deterministic first, fact IDs, abstention.
6. Run locally: conda, `.env` with `MARGIN_RADAR_API_KEY` (only needed for recording), `make demo`, `make eval`, `make test`.
7. Cost: tokens and $ from the report.
8. Limitations: synthetic data, simple $-at-risk model, no auth or rate limiting.

- [ ] **Step 1:** Write the tests:
  - `test_readme_banner`.
  - `test_readme_results_match_report`: the numbers in the README table equal `latest.json`.
  - `test_no_secrets_committed`: `git ls-files` content has no `sk-ant-` and no `MARGIN_RADAR_API_KEY=` followed by a value.
- [ ] **Step 2:** Run. Expected: FAIL.
- [ ] **Step 3:** Write the docs and the README generation script `scripts/readme_results.py`.
- [ ] **Step 4:** Run `make test` with coverage. Expected: PASS, ≥ 80%. Run superpowers:requesting-code-review and fix CRITICAL/HIGH findings.
- [ ] **Step 5:** Commit `docs: README, architecture, decisions`.

### Task 21: GitHub Pages deploy

**Files:** Create `.github/workflows/pages.yml`. It runs on push to main: checkout → setup-node 20 → `npm ci` in `web` → `VITE_STATIC=1 VITE_BASE=/margin-radar/ npm run build` → `actions/upload-pages-artifact` → `actions/deploy-pages`. It runs no Python and no API key, because it uses the committed `web/public/data`.

- [ ] **Step 1:** Run `make export` and commit `web/public/data`.
- [ ] **Step 2:** Run `npx playwright test --project=static` against `vite preview --base /margin-radar/`. Expected: PASS.
- [ ] **Step 3:** **Ask the user** before creating the GitHub repo and pushing, which is outward-facing. Then push and enable Pages (source: GitHub Actions).
- [ ] **Step 4:** Load the Pages URL and check that the banner is visible and the brief citations work.
- [ ] **Step 5:** Commit `ci: GitHub Pages static deploy`.

---

## Spend summary (live LLM calls, all others are $0 replays)

| Step | Model | Max calls | Needs user OK |
|---|---|---|---|
| Task 13 Step 5 dev smoke | dev (Haiku) | 16 | yes, to be safe |
| Task 15 Step 4 `make record-final` | final (Sonnet) | 48 | **yes (> 20)** |
| Any re-record after prompt changes | dev first, then final | 16 / 48 | yes |
| tests, `make demo`, `make eval`, API, dashboard, CI | — | 0 | — |
