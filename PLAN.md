# Margin Radar Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.
>
> **Execution method (user, 2026-10-22):** Phase 2 uses subagent-driven-development (a fresh implementer per task and a fresh reviewer before the next task). Phases 3–8 use executing-plans, with requesting-code-review at the end of each phase. One branch per phase; commit after each passing task; merge to main with tests passing. `docs/SPEC.md` is authoritative for Phases 4–8 wherever this plan is less detailed. Where they conflict, the decisions in this plan's Global Constraints win (separate DBs, peer-relative detection, excess_share, sample-scale $).

**Goal:** A cohort early-warning and action agent for an iBuyer, built on synthetic data. It spots contribution-margin (CM) erosion by segment from funnel leading indicators within days of onset instead of months, ranks actions by $ of CM at risk, and writes a weekly brief where every number traces to a governed query ID.

**Architecture:** A seeded Python generator writes home-level raw tables into DuckDB, with three injected scenarios plus a control run. dbt builds point-in-time weekly segment marts and a MetricFlow semantic layer, and a thin governed query layer turns every metric read into a logged, ID'd query. A deterministic detector produces ranked alerts. It computes peer-relative residuals (leave-one-out median of segments that don't share the dimension under test, so shared seasonality cancels), rolls them up to markets and bands, scores them with z-score and CUSUM against their own trailing history, adds a portfolio-level abrupt-shift check, and classifies the result with rules. Claude only writes the narrative, by referencing fact IDs; it never writes numerals. A renderer and grounding validator fill in the numbers, and a record/replay LLM cache makes the demo, API, dashboard and tests free to run.

**Tech Stack:** Python 3.11 (conda env `margin-radar`), DuckDB, dbt-duckdb, dbt-metricflow, statsmodels, pandas, anthropic SDK, python-dotenv, pytest, FastAPI + uvicorn, Vite + React + TypeScript + Tailwind + Recharts, Playwright (browser checks), GitHub Actions → GitHub Pages.

**Spec:** `CLAUDE.md` (sections CONTEXT, NON-NEGOTIABLE RULES, API KEY AND BUDGET RULES, SKILLS TO USE, STACK, LAYOUT). Brainstorming was skipped at the user's request, so the design decisions below that the spec doesn't pin down are the planner's calls. Each one is marked *(planner's call)* where it first appears.

## Global Constraints

- Banner string, exact: `Synthetic data — not Opendoor data.` It must appear on every web page (in the layout component), at the top of every brief (`.md` and `.json`), in README, and in the API `/api/meta` response. Constant: `SYNTHETIC_BANNER` in `common/banner.py`. The web app mirrors it in `web/src/banner.ts`, and a test checks the two match.
- Deterministic detection first. The LLM never computes or writes numbers. Every number in a brief carries a query ID. The agent abstains when data is insufficient.
- Expected seasonality must NOT alert: a spring volume peak and a ~500 bps Q2→Q3 CM dip.
- Business constants (`common/business.py`): `OPEX_PCT = 0.024`, `INTEREST_PCT = 0.02`, `CM_FLOOR_PCT = 0.045`. The $9B run-rate constants are removed in Task 5.
- **Dollar scale** *(user)*: every $ figure in code output, the UI and briefs is labeled `SAMPLE_SCALE_LABEL = "sample-scale ($ at the synthetic portfolio's ~$1.6B/yr)"`. Every impact is reported both in sample-scale $ and in bps of contribution margin. Nothing scales to $9B anywhere, and a test guards it.
- **Scores are not probabilities** *(user)*: the detector score (z / CUSUM) is shown as an "uncalibrated score". No number is ever presented as the probability that an alert is real.
- **Detector independence** *(user)*: `detector/` never imports `generator` and never uses the generator's seasonal parameters. Seasonality is separated by peer comparison only.
- **Run isolation** *(user, from code review)*: each run has its own database, `data/radar_injected.duckdb` and `data/radar_control.duckdb`, with two dbt targets (`injected`, `control`). The semantic layer works against either. `eval/ground_truth.json` lives under `/eval`, and only `/eval` code may read it or open both databases. `/detector` and `/agent` never import `generator` or `eval`, and never name a run's file; they receive one database path. `tests/test_boundaries.py` enforces this.
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

1. **Look-ahead leakage.** A brief or alert for `as_of = w` must not change when data after `w` exists. Expected: metrics and alerts for weeks ≤ w are identical whether the generator run is truncated at w or not. Pinned in Task 5 (`test_no_lookahead`), Task 7 (`test_store_no_lookahead`) and Task 9 (`test_alerts_stable_under_truncation`).
2. **Thin or empty segments.** A segment-week with zero offers or zero sales must yield `None` plus an insufficient-data flag, not 0, NaN or a crash, and it must never trigger an alert. Pinned in Task 7 (`test_below_min_denominator_is_none`) and Task 8 (`test_thin_segment_excluded`).
3. **An `as_of_week` before the detector has `MIN_HISTORY_WEEKS` of valid residual history, or outside the data range.** Expected: a deterministic abstain-only brief, zero LLM calls, and a clear reason. Pinned in Task 9 (`test_short_history_insufficient`, `test_short_history_global_abstention`) and Task 13 (`test_abstain_brief_makes_no_llm_call`).
4. **Replay cache miss under `REPLAY=1`.** Expected: `ReplayMiss` naming the cache key and the command to record it. No live call, no empty brief. Pinned in Task 11 (`test_replay_miss_raises_with_hint`) and Task 17 (`test_api_brief_missing_returns_404_not_live_call`).
5. **The LLM writes a numeral or an unknown fact ID.** Expected: the validator rejects it, there is one retry with the error fed back, then the run fails closed (brief marked `invalid`, not published). Pinned in Task 13 (`test_hallucinated_number_rejected`, `test_unknown_fact_id_rejected`, `test_fails_closed_after_one_retry`).

## Shared design decisions

> **Revised 2026-10-22.** The user's Phase 1 spec replaced the original data design. Phases 2–5 were re-planned for it: 78 weeks, 36 segments, a peer-relative detector, and sample-scale dollars. Phases 6–8 were updated only where they referenced the old design.

- **Time:** weekly grain, Monday week starts. 78 weeks, numbered from 0, with week 0 = `2025-01-06`; data cutoff `2026-07-05`. *(user)*
- **Segments:** 6 markets `M01..M06` × 3 price bands by model valuation (`B1 <$300K`, `B2 $300–450K`, `B3 >$450K`) × 2 products (`cash`, `CNML`), giving 36 segments. Segment id is `M02-B2-cash`. *(user: counts; planner: names and thresholds)* Both products have the same economics; only the mix differs (75/25) *(planner's call)*.
- **Scale:** ~20.5K offers per run, ~6.4K closes, ~4.9K resales by the cutoff. That's about $1.6B a year of resale revenue. **Decided:** label everything sample-scale and never scale to $9B (see Global Constraints). Data is thin per segment-week (median 2 sales; 37% of segment-weeks have none), so the detector pools by market and band.
- **Funnel per home** (`raw.homes`, one row per offer; nullable timestamps; NaT = not happened by the cutoff):
  - offer → contract → close → assessment → renovation start/complete → list → first buyer offer → resale.
  - Outcomes: `seller_declined`, `fell_through`, `company_declined` (from the pre-close inspection, so it lands between contract and close), `closed`, and `open` for offers unresolved at the cutoff.
  - Price cuts are events in `raw.price_cuts`.
  - Each run is written to its own database (`data/radar_injected.duckdb`, `data/radar_control.duckdb`), with no `run_id` column. The runs share random draws, so a cross-run join would expose the answer key; separate files prevent that. *(user, from code review)*
- **Seasonality:** offers peak in mid-April (+15% around the yearly average). Days to first buyer offer are fastest in April and slowest in October. Realized price against the seasonally naive model valuation varies by resale month. The result, on the control run at seed 42: overall margin 5.5%, 2025 Q2 7.9% → Q3 3.1% (477 bps dip).
- **Scenarios** (`injected` run, seed 42, all from week 30 = `2025-08-04`, all settable by CLI flag):
  - **A:** market `M02`, days to first buyer offer ×1.40 for listings from week 30. Showings to first offer stay the same, so showings per week fall.
  - **B:** band `B2`, offer→contract conversion ×1.25 for offers from week 30 at unchanged spread, and resale ×0.97 against the model for the same homes (adverse selection).
  - **C:** market `M05`, renovation actual ×1.18 for renovations starting from week 30.
- **Control:** the same seed with no injections. All random draws are taken up front, so homes outside a scenario's scope are identical between runs, and tests assert this.
- **Ground truth** (`eval/ground_truth.json`, never loaded into DuckDB, read only by `/eval`): the margin-visible week is the first resale week where the scope's sold-cohort margin in the shipped combined injected run is ≥ 50 bps below control for 2 consecutive weeks. The same measure with the scenario run alone is kept as `cm_first_visible_week_solo`, for attribution. Seed 42: A visible at week 39 (lag 9 weeks), B at week 45 (lag 15; 47 solo, because B2 overlaps A's and C's markets), C at week 46 (lag 16).
- **Headline KPIs:** *detection delay* = first alert week − `start_week`. *Lead time* = `cm_first_visible_week` (combined run) − first alert week. Both are reported per scenario; Phase 5 gates on alerting before the margin-visible week (see Phase 5 DoD).

---

## Phase 1: Generator + 3 injected scenarios + control run ✅ built 2026-10-22

**DoD (met):** `make data` writes `data/parquet/{injected,control}/{homes,price_cuts}.parquet`, `data/radar_injected.duckdb` and `data/radar_control.duckdb` (each with `raw.homes` and `raw.price_cuts`), and `eval/ground_truth.json`. `make test` gives 60 passed (after the code-review fixes, the database split and `tests/test_boundaries.py`).

**Files:** `common/{banner,business}.py`, `generator/{config,scenarios,simulate,metrics,ground_truth,io,__main__}.py`, `tests/conftest.py`, `tests/test_scaffold.py`, `tests/generator/test_{volumes,funnel,margin,seasonality,injections,ground_truth,cli}.py`, `environment.yml`, `pyproject.toml`, `Makefile`.

**Interfaces later phases rely on:**
- `generator.simulate.simulate(seed: int, scenarios: Sequence[Scenario] = (), cutoff_week: int = 78) -> SimOutput(homes, price_cuts)`. `cutoff_week` gives point-in-time truncation for no-look-ahead tests.
- `generator.scenarios.Scenario(name, scope_type, scope, start_week, effects)` and `default_scenarios(...)`.
- `generator.metrics.contribution_margin_usd(homes)` and `sold_cohort_cm(homes)`. CM = resale − (offer − 5% fee) − actual renovation − holding − selling (3%). Financing is excluded. dbt must reproduce this (parity test in Phase 2).
- `generator.ground_truth.compute_ground_truth(seed, scenarios) -> list[dict]` and `first_visible_week(scenario, injected_homes, control_homes) -> int | None`.
- CLI: `python -m generator --seed 42 --out-dir data --truth-path eval/ground_truth.json [--inject A,B,C] [--a-market M02 --a-start-week 30 --b-band B2 --b-start-week 30 --c-market M05 --c-start-week 30]`.


## Phase 2: dbt + semantic layer

**Phase DoD:** `make build` (`dbt build` + `mf validate-configs` for both targets, `injected` and `control`) is green. `pytest tests/dbt tests/governed` passes, including the CM parity check against the generator, the MetricFlow parity check and the no-look-ahead tests. Every metric used downstream is defined in `dbt_project/models/semantic/*.yml`.

### Task 5: dbt project, staging and weekly segment mart

Use `dbt:using-dbt-for-analytics-engineering`.

**Files:**
- Create: `dbt_project/dbt_project.yml`, `dbt_project/profiles.yml` (duckdb, two outputs: `injected` → `path: "{{ env_var('MR_DB_PATH', 'data/radar_injected.duckdb') }}"`, `control` → `path: "{{ env_var('MR_DB_PATH', 'data/radar_control.duckdb') }}"`; `target: "{{ env_var('MR_TARGET', 'injected') }}"`), `models/staging/{_sources.yml,stg_homes.sql,stg_price_cuts.sql}`, `models/marts/{mart_segment_week.sql,metricflow_time_spine.sql,_marts.yml}`, `tests/dbt/{conftest.py,test_marts.py}`.
- Modify: `environment.yml` (add pinned `dbt-duckdb`, `dbt-metricflow[duckdb]`, `pyyaml`, `statsmodels`), `Makefile` (`build:` target), `common/business.py` (delete `RUN_RATE_USD` and `USD_PER_100BPS_YEAR`; add `SAMPLE_SCALE_LABEL`), `tests/test_scaffold.py`.

**Interfaces:**
- Consumes: `raw.homes` and `raw.price_cuts` in one run's database (Phase 1 as-built columns).
- Produces `mart_segment_week` in each run's database: one row per `(segment, market, band, product, week)` for all 36 segments × 78 weeks, zero-filled. `week` is the integer week index, plus a `week_start` date. Each event counts in its own event week; "state" columns use only dates ≤ the end of the week. Columns are numerators and denominators only (ratios live in the semantic layer):
  - **Offers and contracts:** `offers`, `spread_sum` (offers in week); `contracts` (contracts signed in week); `fell_through`, `company_declined` (cancellations in week); `closes`, `acquisition_usd` (offer_price of closes in week).
  - **Listings:** `awaiting_offer` (listings with `list_date` < week start and no first buyer offer before week start); `first_offers`, `dtfo_sum`, `showings_sum` (by first-offer week); `price_cuts` (cuts in week).
  - **Renovations:** `renos_completed`, `reno_estimate_sum`, `reno_actual_sum` (by completion week).
  - **Resales:** `resales`, `resale_usd`, `model_valuation_sold_sum`, `cm_usd`, `holding_cost_sum`, `hold_days_sum` (by resale week). `cm_usd` uses the generator's formula: resale − (offer − fee) − reno_actual − holding − selling.
  - **Inventory:** `unsold_inventory_usd`, which is Σ(offer − fee) of homes closed by week end and not resold by week end.
- `SAMPLE_SCALE_LABEL = "sample-scale ($ at the synthetic portfolio's ~$1.6B/yr)"` in `common/business.py`. *(user)*

- [ ] **Step 1:** Write the tests. `tests/dbt/conftest.py` has a session fixture that runs `python -m generator --seed 42 --out-dir <tmp>` and then `dbt build --target {injected,control} --target-path <tmp>/target_<run>` with `MR_DB_PATH=<tmp>/radar_<run>.duckdb`.
  - `test_mart_grain_complete`: in each database, rows == 36 × 78, and the key is unique.
  - `test_counts_reconcile`: per database, `sum(offers)` == `count(*) raw.homes` and `sum(resales)` == `count(resale_date)`.
  - `test_cm_parity_with_generator`: per database, `sum(cm_usd)` == `generator.metrics.contribution_margin_usd(parquet homes).sum()` to within 1e-6 relative.
  - `test_awaiting_offer_point_in_time`: a hand-built 3-home raw fixture gives the expected `awaiting_offer`/`first_offers`/`price_cuts` per week.
  - `test_no_lookahead` *(Review Focus 1)*: a mart built from `simulate(42, default_scenarios(), cutoff_week=40)` equals the full-data mart on every column for weeks < 40.
  - `test_sample_scale_label_is_true`: annualized resale revenue in the control database over weeks 26–77 is between $1.4B and $1.8B.
  - `test_no_9b_scaling`: no code file (`.py`, `.sql`, `.ts`, `.tsx`, `.yml`) contains `9_000_000_000`, `9e9` or `90_000_000`. Add this to `tests/test_scaffold.py`.
  - In `_marts.yml`: `unique_combination_of_columns`, `not_null`, and `accepted_values` for band and product.
- [ ] **Step 2:** Run `pytest tests/dbt tests/test_scaffold.py -v`. Expected: FAIL.
- [ ] **Step 3:** Implement the models. The time spine is day grain from 2025-01-01 to 2026-12-31.
- [ ] **Step 4:** Run. Expected: PASS, and `dbt build` reports 0 errors.
- [ ] **Step 5:** Commit `feat(dbt): staging and point-in-time weekly segment mart`.

### Task 6: Semantic layer (MetricFlow)

Use `dbt:building-dbt-semantic-layer`, with the local `mf` CLI only.

**Files:** Create `dbt_project/models/semantic/segment_week.yml` (semantic model on `mart_segment_week`: entity `segment`; dimensions `market`, `band`, `product`; time dimension `week_start`). The same YAML serves both targets. and `dbt_project/models/semantic/metrics.yml`, plus `tests/dbt/test_semantic.py`.

**Interfaces:** Produces these metrics. `role` drives the detector: **trigger** metrics can raise alerts, **context** metrics are evidence only, and **lagging** metrics never trigger.

| metric | type | definition | role |
|---|---|---|---|
| `contract_rate` | ratio | contracts / offers | trigger |
| `avg_spread_pct` | ratio | spread_sum / offers | context (explains conversion) |
| `first_offer_rate` | ratio | first_offers / awaiting_offer | trigger |
| `price_cut_rate` | ratio | price_cuts / awaiting_offer | context |
| `showing_rate_per_week` | ratio | showings_sum × 7 / dtfo_sum | context |
| `avg_days_to_first_offer` | ratio | dtfo_sum / first_offers | context |
| `reno_overrun_pct` | derived | reno_actual_sum / reno_estimate_sum − 1 | trigger |
| `fall_through_rate`, `company_decline_rate` | ratio | over contracts | context |
| `resale_vs_model_bps` | derived | (resale_usd / model_valuation_sold_sum − 1) × 1e4 | lagging |
| `contribution_margin_pct` | ratio | cm_usd / resale_usd | lagging |
| `holding_cost_bps_per_day` | derived | holding_cost_sum / hold_days_sum / (resale_usd / resales) × 1e4 | context |
| `offers`, `closes`, `acquisition_usd`, `resale_usd` | simple | sums | volume |
| `unsold_inventory_usd` | simple, non-additive over `week_start` (last) | | exposure |

- [ ] **Step 1:** Write the tests:
  - `test_mf_validate`: `mf validate-configs` exits 0.
  - `test_mf_query_cm_dip`: with `MR_TARGET=control`, `mf query --metrics contribution_margin_pct --group-by metric_time__quarter` gives 2025 Q2 − Q3 between 425 and 575 bps.
  - `test_mf_works_on_both_targets`: `mf query --metrics offers` returns the same total as the `raw.homes` row count under `MR_TARGET=injected` and `MR_TARGET=control`.
- [ ] **Step 2:** Run. Expected: FAIL.
- [ ] **Step 3:** Write the YAML.
- [ ] **Step 4:** Run. Expected: PASS.
- [ ] **Step 5:** Commit `feat(dbt): MetricFlow semantic layer`.

### Task 7: Governed, single-database query layer with query IDs

**Files:** Create `detector/__init__.py`, `detector/governed.py`, `tests/governed/test_governed.py`

**Interfaces:**
- Consumes: one run's `mart_segment_week`, plus `metrics.yml` and `segment_week.yml` parsed with PyYAML. Definitions live in one place.
- Produces:

```python
Level = Literal["segment", "market", "band", "portfolio"]

@dataclass(frozen=True)
class MetricPanel:
    query_id: str            # "Q" + sha256(run_id|metric|level|window|start|as_of_week|sql)[:10]
    metric: str
    run_id: str
    level: Level
    as_of_week: int
    window_weeks: int        # trailing sum of numerators and denominators over this many weeks
    values: pd.DataFrame     # columns: scope, week, value (None if denominator < MIN_DENOMINATOR), denominator
    sql: str

@dataclass(frozen=True)
class DerivedFact:
    fact_id: str             # "D" + sha256(formula|inputs)[:10]
    label: str; value: float; unit: Literal["usd", "bps", "pct", "count", "days", "ratio"]
    inputs: tuple[str, ...]; formula: str

class GovernedStore:
    def __init__(self, db_path: str, run_id: str, log_path: str | None = None): ...
    def panel(self, metric: str, level: Level, as_of_week: int, window_weeks: int = 4, start_week: int = 0) -> MetricPanel
    def register_derived(self, label: str, value: float, unit: str, inputs: tuple[str, ...], formula: str) -> str
    def get(self, ref_id: str) -> MetricPanel | DerivedFact
    def all(self) -> tuple[MetricPanel | DerivedFact, ...]
```
- **Run isolation:** a store opens exactly one database file, read-only. `run_id` is a label used in query IDs and outputs. Generated SQL never uses `ATTACH`, and no method opens another file. The detector and agent read data only through a store.
- `MIN_DENOMINATOR` (in `detector/governed.py`): `{"contract_rate": 30, "first_offer_rate": 20, "reno_overrun_pct": 10, default: 10}`, applied to the windowed denominator. Weeks past `as_of_week` are never returned. Unknown metric, level or run raises `ValueError`. SQL is built from whitelisted names only.

- [ ] **Step 1:** Write the tests:
  - `test_query_id_deterministic`, `test_query_id_changes_with_as_of_and_window`.
  - `test_window_sums_numerators_and_denominators`: on a fixture, a 4-week contract_rate equals Σcontracts/Σoffers.
  - `test_below_min_denominator_is_none` *(Review Focus 2)*.
  - `test_parity_with_metricflow`: 3 metrics × {market M02, band B2} × window 1, compared with `mf query` to within 1e-9.
  - `test_store_no_lookahead` *(Review Focus 1)*: `panel(..., as_of_week=39)` is equal on the cutoff-40 DB and the full DB.
  - `test_store_is_single_file_read_only`: writes through the store's connection fail, and no generated SQL contains `attach`.
  - `test_derived_traces_inputs`, `test_rejects_unknown_metric`, `test_log_written`.
- [ ] **Step 2:** Run. Expected: FAIL.
- [ ] **Step 3:** Implement.
- [ ] **Step 4:** Run `make build && pytest tests/governed tests/test_boundaries.py -v`. Expected: PASS.
- [ ] **Step 5:** Commit `feat(governed): run-scoped, ID'd metric panels with MetricFlow parity`.

---

## Phase 3: Detector (peer-relative)

**Phase DoD:** `python -m detector --db data/radar_injected.duckdb --run-id injected --as-of-week 40` writes `data/out/injected/week_40/alerts.json`, and `pytest tests/detector tests/test_boundaries.py` passes. On seed 42:
- Each scenario alerts on its own scope before its `cm_first_visible_week`: A → `demand_softening`/M02, B → `adverse_selection`/B2, C → `reno_cost_drift`/M05.
- The injected run raises no alert on any other (kind, scope).
- **The control run raises zero alerts, including portfolio alerts, at every evaluable `as_of_week` through week 77.** That covers the 2025 and 2026 spring peaks and the 2025 Q2→Q3 dip.
- `tests/test_boundaries.py` passes: nothing in `detector/` imports `generator` or `eval`, or names a run's file. *(user: no generator seasonal parameters in the detector)*

### Task 8: Peer residuals and rollups

**Files:** Create `detector/config.py`, `detector/peers.py`, `tests/detector/test_peers.py`. (`tests/test_boundaries.py` already exists from Phase 1 and starts guarding `detector/` as soon as it exists.)

**Interfaces:**
- Consumes: `MetricPanel` at `level="segment"`.
- Produces:
  - `peer_residuals(panel: MetricPanel, dimension: Literal["market", "band"]) -> pd.DataFrame`, with columns `segment, market, band, product, week, value, peer_median, n_peers, residual, weight`. *(user)*
    - Peers of a segment are the segments that share the other two dimensions and differ on `dimension`. Market tests use the same band and product in other markets (5 peers). Band tests use the same market and product in other bands (2 peers).
    - `peer_median` is the median of peer values, never including the segment itself (leave-one-out by construction).
    - `residual` is NaN when `value` is None or `n_peers < MIN_PEERS[dimension]`. `weight` is the windowed denominator, or 0 when the residual is NaN.
  - `rollup(residuals: pd.DataFrame, dimension) -> pd.DataFrame`, with columns `scope, week, residual, weight, n_segments`. Each scope's residual is the weight-weighted mean of its segments' residuals, and NaN when `n_segments < 2` or total weight is below `MIN_DENOMINATOR`. *(planner's call, from the Phase 1 data: the median segment-week has 2 sales and 51% of segment-weeks miss a 20-offer/4-week minimum, so per-segment drift tests alone can't see the injections. A pooled band residual moves B2 conversion from 0.35 to 0.45 within 6 weeks.)*
- `detector/config.py` holds the constants. Starting values: `WINDOW_WEEKS = 4`, `MIN_PEERS = {"market": 3, "band": 2}`, `HISTORY_WEEKS = 16`, `MIN_HISTORY_WEEKS = 8`, `EVAL_WEEKS = 8`, `Z_ALERT = 3.0`, `Z_CONSECUTIVE = 2`, `CUSUM_K = 0.5`, `CUSUM_H = 5.0`, `Z_EXPLAIN = 2.0`, `PORTFOLIO_Z = 4.0`, `PORTFOLIO_BASELINE_WEEKS = 8`, `FORWARD_WEEKS = 13`, and `SIGMA_FLOOR = {"contract_rate": 0.01, "first_offer_rate": 0.01, "reno_overrun_pct": 0.01, "avg_spread_pct": 0.0005}` (the minimum robust scale, so a quiet history can't produce huge z-scores). They are tuned only on seeds 1–5 (Task 14) and only by editing this file.

- [ ] **Step 1:** Write the tests, using small hand-built panels:
  - `test_peers_exclude_dimension_under_test`: band peers of `M01-B1-cash` are exactly `M01-B2-cash` and `M01-B3-cash`; market peers are `M02..M06-B1-cash`.
  - `test_leave_one_out`: a case where including the segment itself would change the median gives the median without it.
  - `test_common_shift_cancels`: adding +0.10 to every segment in week 10 leaves residuals unchanged. This is the seasonality property.
  - `test_market_shift_shows_in_rollup`: +0.10 on all M02 segments gives an M02 rollup residual ≈ +0.10 and |residual| < 0.02 for every other market.
  - `test_thin_segment_excluded` *(Review Focus 2)*: a None value gives a NaN residual and weight 0, with no crash, and the rollup ignores it.
  - `test_too_few_peers_is_nan`.
- [ ] **Step 2:** Run. Expected: FAIL.
- [ ] **Step 3:** Implement with pandas groupby. Peer medians are a groupby over the other two dimensions that excludes the row's own dimension value.
- [ ] **Step 4:** Run. Expected: PASS.
- [ ] **Step 5:** Commit `feat(detector): leave-one-out peer residuals and volume-weighted rollups`.

### Task 9: Drift scoring, portfolio check, classification

**Files:** Create `detector/drift.py`, `detector/portfolio.py`, `detector/rules.py`, `detector/models.py`, `tests/detector/{test_drift.py,test_portfolio.py,test_rules.py}`

**Interfaces:**
- `score(residual: pd.Series, as_of_week: int) -> DriftScore | Insufficient`. The series is indexed by week. *(user: against its own trailing history)*
  - The history is the last `HISTORY_WEEKS` valid residuals in weeks ≤ `as_of_week − WINDOW_WEEKS`, so it doesn't overlap the current window. Fewer than `MIN_HISTORY_WEEKS` returns `Insufficient`.
  - `z_t = (r_t − median(hist)) / max(statsmodels.robust.scale.mad(hist), SIGMA_FLOOR[metric])`.
  - A two-sided CUSUM runs over the last `EVAL_WEEKS`.
  - `DriftScore(z_latest, z_streak, cusum_pos, cusum_neg, direction, onset_week, fired: bool)`. `fired` = (|z| ≥ `Z_ALERT` for ≥ `Z_CONSECUTIVE` weeks) or (CUSUM ≥ `CUSUM_H`).
- `portfolio_check(store, metric, as_of_week) -> PortfolioScore | Insufficient`. *(user: portfolio-level check)* This is an abrupt-shift test on the portfolio-level panel: `r_t = x_t − median(x over the PORTFOLIO_BASELINE_WEEKS weeks before t)`, standardized by robust scale over the trailing history. It fires when |z| ≥ `PORTFOLIO_Z` for 2 consecutive weeks. A smooth seasonal drift moves `r` slowly; a step change doesn't. Gradual all-segment shifts stay undetectable, which goes in README as the known limitation "simultaneous all-segment shifts".
- `detector/models.py`:

```python
@dataclass(frozen=True)
class Signal:
    metric: str; dimension: str; scope: str; direction: Literal["+", "-"]
    z: float; residual: float; onset_week: int; ref_ids: tuple[str, ...]   # panel query_ids + derived residual id
@dataclass(frozen=True)
class Alert:
    alert_id: str            # "A" + sha256(run_id|kind|scope|onset_week)[:8]; stable across as_of weeks
    kind: Literal["adverse_selection", "demand_softening", "reno_cost_drift", "portfolio_shift"]
    dimension: Literal["market", "band", "portfolio"]; scope: str; onset_week: int
    signals: tuple[Signal, ...]; supporting: tuple[Signal, ...]
@dataclass(frozen=True)
class Watch:
    scope: str; metric: str; note: str; ref_ids: tuple[str, ...]
@dataclass(frozen=True)
class Abstention:
    scope: str; metric: str | None; reason: str
@dataclass(frozen=True)
class DetectorResult:
    run_id: str; as_of_week: int; alerts: tuple[Alert, ...]; watch: tuple[Watch, ...]; abstentions: tuple[Abstention, ...]
```

- `detect(store: GovernedStore, as_of_week: int) -> DetectorResult` runs, for each trigger metric × dimension, `peer_residuals` → `rollup` → `score`, then the portfolio check. The rules:
  - **adverse_selection:** `contract_rate` "+" on a scope, AND that scope's `avg_spread_pct` rollup has |z| < `Z_EXPLAIN` (conversion up at unchanged spread). If spread moved down significantly, the shift is "explained by spread" and becomes a `Watch`, not an alert.
  - **demand_softening:** `first_offer_rate` "−" on a scope. A `price_cut_rate` "+" or `showing_rate_per_week` "−" on the same scope is attached as `supporting` when present, but isn't required.
  - **reno_cost_drift:** `reno_overrun_pct` "+" on a scope.
  - **portfolio_shift:** a portfolio check fired on a trigger metric, and no dimension-level alert on the same metric and direction explains it.
  - Any other fired (metric, direction) becomes a `Watch`. `contribution_margin_pct` and `resale_vs_model_bps` never trigger.
  - If no trigger metric has enough history, return a global `Abstention(scope="all", reason=...)` and no alerts.

- [ ] **Step 1:** Write the tests:
  - **test_drift.py:**
    - `test_step_change_fires`.
    - `test_noise_does_not_fire`: 200 seeds of N(0,1) series, firing rate < 2%.
    - `test_short_history_insufficient` *(Review Focus 3)*.
    - `test_onset_week_is_first_crossing`.
  - **test_portfolio.py:**
    - `test_step_fires`: +30% step.
    - `test_smooth_seasonal_does_not_fire`: ±20% sinusoid with period 52, plus noise.
    - `test_suppressed_when_explained_by_dimension_alert`.
  - **test_rules.py:** these use a session fixture that builds seed-42 data and both dbt targets into tmp (reuse `tests/dbt/conftest.py`). The test (not the detector) reads ground-truth weeks.
    - `test_b_detected_before_cm_visible`: there is an `as_of_week` in [30, 44] with an `adverse_selection` alert on B2. 44 = B's `cm_first_visible_week` (45) − 1.
    - `test_a_detected_before_cm_visible`: `demand_softening` on M02 by week 38.
    - `test_c_detected_before_cm_visible`: `reno_cost_drift` on M05 by week 45.
    - `test_injected_alerts_only_on_true_scopes`: across all evaluable weeks, every alert's (kind, scope) is one of the three above.
    - `test_control_zero_alerts_every_week`: every evaluable `as_of_week` ≤ 77 on the control run gives `alerts == ()`.
    - `test_spread_explains_conversion`: built signals with contract_rate "+" and spread "−" give a `Watch` and no alert.
    - `test_short_history_global_abstention` *(Review Focus 3)*: `as_of_week = 6` gives no alerts and an `Abstention(scope="all")`.
    - `test_alerts_stable_under_truncation` *(Review Focus 1)*: results at `as_of_week = 44` match between the cutoff-45 and full data.
- [ ] **Step 2:** Run. Expected: FAIL.
- [ ] **Step 3:** Implement. If control alerts appear, use superpowers:systematic-debugging and change only `detector/config.py`. If a seed-42 detection target can't be met without control alerts, stop and report the trade-off to the user. Don't loosen the control gate.
- [ ] **Step 4:** Run. Expected: PASS.
- [ ] **Step 5:** Commit `feat(detector): drift scoring, portfolio check, classification rules`.

### Task 10: Impact (sample-scale $ and bps), ranking, detector CLI

**Files:** Create `detector/impact.py`, `detector/actions.py`, `detector/__main__.py`, `tests/detector/test_impact.py`. Modify the `Makefile` `detect:` target.

**Interfaces:**
- `Impact(basis: Literal["measured", "scenario_estimate", "sensitivity"], usd_low: float | None, usd_mid: float | None, usd_high: float | None, scope_bps_low/mid/high: float | None, portfolio_cm_bps_low/mid/high: float | None, usd_per_100bps: float, exposure_usd: float, label: str, status: str, ref_ids: tuple[str, ...])`. For `measured`, low = mid = high. `label` is `SAMPLE_SCALE_LABEL`, prefixed with `"scenario estimate, "` for `scenario_estimate`. Every impact is reported in both sample-scale $ and bps of CM. *(user)* Nothing is scaled to $9B.
- `RankedAction(rank, alert_id, kind, scope, impact: Impact, action: str, owner: str)`, and `rank_actions(result: DetectorResult, store) -> tuple[RankedAction, ...]`.
- **Exposure** = `unsold_inventory_usd`(scope, as_of) + `FORWARD_WEEKS` × trailing-4-week mean weekly `acquisition_usd`(scope).
- **Erosion per kind,** all from governed panels, never from generator constants:
  - **reno_cost_drift:** rollup residual of `reno_overrun_pct` × (scope `reno_estimate_sum` / `resale_usd`, trailing 13 weeks) × 1e4.
  - **demand_softening:** excess days on market = `avg_days_to_first_offer` × (peer_rate / observed_rate − 1), × `holding_cost_bps_per_day`. This is labeled a lower bound, since price-cut losses aren't modeled.
  - **adverse_selection** *(user)*: `basis="scenario_estimate"`, `status="unconfirmed until resales"`.
    - $ at risk = exposed homes × average price × resale shortfall × excess_share, at shortfall 1% / 2% / 3% (low / mid / high).
    - **Exposed homes** = homes in the scope closed since `onset_week` and not yet resold, + `FORWARD_WEEKS` × trailing-4-week mean weekly `closes`.
    - **Average price** = trailing-13-week `acquisition_usd` / `closes` for the scope.
    - **excess_share** *(user)* = share of contracts above the peer-expected rate: contract_rate rollup residual / observed rollup contract_rate, clipped to [0, 1]. Never call it, or any other number, the probability that an alert is real.
    - bps equivalent: `scope_bps` = shortfall × excess_share × 1e4, so 100–300 bps × excess_share.
    - Once the scope has ≥ `MIN_DENOMINATOR` resales of homes offered after `onset_week`, switch to `basis="measured"` and `status="confirmed by resales"`, with erosion = −(rollup residual of `resale_vs_model_bps` on that cohort).
    - `ADVERSE_SELECTION_SHORTFALL = (0.01, 0.02, 0.03)` goes in `detector/config.py`. It is a user-given planning range, not a generator parameter.
  - **portfolio_shift:** `basis="sensitivity"`. Only `usd_per_100bps` and exposure are reported.
- For `measured` kinds: `usd` = scope bps / 1e4 × exposure. For every kind: `portfolio_cm_bps` = scope bps × the scope's share of portfolio `resale_usd` over the trailing 13 weeks, and `usd_per_100bps` = exposure / 100.
- **Rank key:** `usd_mid`, which is the midpoint for scenario estimates *(user)*, or `usd_per_100bps` for `sensitivity`. Sort descending, with ties broken by `alert_id`. The table and brief state the basis of each row, and say "ranked on the midpoint of the scenario estimate" where that applies.
- Every number above is registered with `store.register_derived(...)`, with its input IDs.
- **Action catalog** (deterministic). Placeholders are filled with fact IDs, never raw numbers:
  - adverse_selection → "Widen spread or add in-person inspection for {scope}; audit model valuation inputs" (owner Pricing)
  - demand_softening → "Slow acquisitions in {scope}; reprice aged listings" (owner Resale)
  - reno_cost_drift → "Re-baseline renovation estimates in {scope}; require in-person assessment" (owner Renovation)
  - portfolio_shift → "Portfolio-wide shift in {metric}; check external drivers" (owner Analytics)
- **CLI:** `python -m detector --db PATH --run-id LABEL --as-of-week N [--out data/out]`; the caller passes one database path writes `{out}/{run_id}/week_{N:02d}/{alerts.json,queries.jsonl}`. `alerts.json` carries the banner and `SAMPLE_SCALE_LABEL`. `make detect` runs every evaluable week for both runs.

- [ ] **Step 1:** Write the tests:
  - `test_ranking_sorted_by_rank_key`.
  - `test_every_impact_number_has_ref_id`.
  - `test_impact_formula_hand_fixture`.
  - `test_adverse_selection_scenario_range`: hand fixture with 100 exposed homes, $400K price and excess_share = 0.2 gives usd low / mid / high = $80K / $160K / $240K, scope bps = 20 / 40 / 60, `basis="scenario_estimate"`, label starting `"scenario estimate, sample-scale"`, and `status="unconfirmed until resales"`.
  - `test_adverse_selection_ranks_on_midpoint`: it outranks a measured alert with a smaller $ and is outranked by a larger one.
  - `test_adverse_selection_switches_to_measured_after_resales`.
  - `test_b2_first_alert_has_scenario_estimate`: on seed 42, B2 at its first alert week has `usd_mid > 0`.
  - `test_impact_in_usd_and_bps`: every `measured` or `scenario_estimate` impact has both `usd_mid` and `portfolio_cm_bps_mid`.
  - `test_alerts_json_has_banner_and_sample_label`.
  - `test_cli_writes_outputs`.
- [ ] **Step 2:** Run. Expected: FAIL.
- [ ] **Step 3:** Implement.
- [ ] **Step 4:** Run `pytest tests/detector -v && make detect`. Expected: PASS.
- [ ] **Step 5:** Commit `feat(detector): sample-scale impact in $ and bps, ranking, CLI`.

---

## Phase 4: Claude agent + grounded briefs

Start this phase by invoking `/claude-api`. The user does this, since the skill is user-invocable only. Use it for all SDK code: tool use, prompt caching, current model IDs and pricing.

**Phase DoD:** `pytest tests/agent` passes with zero live calls. `python -m agent brief --run injected --as-of-week <B's first alert week>` run live once with the dev model writes `briefs/injected/week_<NN>.{md,json}` that passes the grounding validator. Rerunning it with `REPLAY=1` reproduces the brief byte-for-byte at $0. Then the final sample briefs are recorded with `CLAUDE_MODEL_FINAL` and committed, along with their `data/llm_cache/` entries.

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
- Consumes: `GovernedStore` (bound to one run), `DetectorResult`, `RankedAction`, `LLM`.
- Produces:
  - `Fact(fact_id: str, ref_id: str, label: str, value: float | None, unit: str)`. `fact_id = f"F{ref_id}_{k}"`, where `ref_id` is a panel `query_id` or a derived `D…` id and `k` is `{scope}_{week}` or the component name, sanitized to `[A-Za-z0-9_]`.
  - `FactSheet`: an immutable mapping fact_id → Fact, built with `FactSheet.from_detector(result, actions, store)`, plus `.extend(panel)`.
  - Tools exposed to Claude, with JSON schemas in `agent/tools.py`:
    - `get_ranked_actions()` → actions with fact IDs (exposure; sample-scale $ low / mid / high; bps of portfolio CM) plus `basis` and `status`, not numbers.
    - `get_metric_series(metric, scope, weeks<=26)` → a list of `{week_start, fact_id, peer_median_fact_id}`. `scope` is a market, band or segment ID. It calls the store with `as_of_week` fixed by the loop, never by the model.
    - `get_watch_and_abstentions()`
    - `get_feedback_summary()` (stub returns `[]` until Task 16)
    - `submit_brief(brief)`, where `brief` has the schema `{headline: str, sections: [{alert_id, title, what_moved, why_not_seasonality, impact, action, confidence: "high"|"medium"|"low"}], watchlist: [str]}`.
  - **The model sees fact IDs and their labels and units, never values** *(planner's call)*. This makes "LLM never computes numbers" structural: the model has no numbers to compute with.
  - `run_agent(llm, store, result, actions, max_turns=8) -> dict` returns the submitted brief JSON. Each loop turn is one `llm.create`. Stop on `submit_brief`. Exceeding `max_turns` raises `AgentDidNotSubmit`.
  - System prompt (in `agent/prompts.py`) states the role. It must reference numbers only as `{{fact_id}}` and never write digits except inside those tokens and scope IDs. It must not claim causes beyond the alert kind's mechanism. It explains why each alert isn't seasonality using the peer-median facts, because peers in the same week share the seasonality. It says "sample-scale" for $ facts. It presents scenario estimates as a range labeled "scenario estimate, sample-scale" and "unconfirmed until resales", and says the ranking uses the midpoint. It reports abstentions as they are, not filled in.

- [ ] **Step 1:** Write the tests, using a scripted fake LLM that returns fixture tool_use blocks.
  - `test_loop_calls_tools_then_submits`.
  - `test_tool_results_contain_no_numeric_values`: the serialized tool results match no `\d` outside fact IDs, segment IDs and ISO dates.
  - `test_as_of_not_overridable`: a model-supplied `as_of` arg is rejected by the schema.
  - `test_max_turns_raises`.
  - `test_tools_cannot_select_run`: no tool schema has a `run_id` parameter.
- [ ] **Step 2:** Run. Expected: FAIL.
- [ ] **Step 3:** Implement.
- [ ] **Step 4:** Run. Expected: PASS.
- [ ] **Step 5:** Commit `feat(agent): fact-ID tool loop`.

### Task 13: Renderer, grounding validator, abstention, brief CLI

**Files:** Create `agent/render.py`, `agent/validate.py`, `agent/__main__.py`, `tests/agent/test_render_validate.py`. Modify the `Makefile` `briefs:` target.

**Interfaces:**
- Produces:
  - `validate(brief: dict, facts: FactSheet, allowed_ids: set[str]) -> list[str]` (an empty list means valid). Errors include: a digit outside `{{…}}` that isn't an allowed scope ID (`M02`, `B2`, `M02-B2-cash`) or ISO date; an unknown fact ID; a fact whose value is `None`; a section `alert_id` not in the detector result; or a ranked alert missing from the brief.
  - `render(brief, facts, result, actions) -> tuple[str, dict]` produces markdown and JSON. Markdown layout:
    1. Banner line.
    2. Run and as-of week (week-start date).
    3. Headline.
    4. One section per alert, with number tokens rendered as `value` plus a superscript citation `[Q…]`.
    5. A deterministic "Ranked actions" table: `rank | scope | kind | $ at risk (sample-scale; range and midpoint for scenario estimates, $ per 100 bps for sensitivity) | bps of portfolio CM | basis / status | action | owner | refs`, with a note under the table: "Scenario estimates are ranked on their midpoint."
    6. A deterministic "Portfolio watch" section (portfolio_shift alerts and `Watch` items).
    7. A deterministic "Abstentions" section.
    8. A "Feedback since last brief" section (empty until Task 16).
    9. An appendix query table (query_id, metric, level, window, sql sha256[:8]), and a footer with `SAMPLE_SCALE_LABEL`.
  - Formatting by unit: usd → `$1.2M (sample-scale)` (the label appears at least on the first $ figure in each section), bps → `+312 bps`, pct → `3.4%`, count → `1,204`, days → `41 days`.
  - JSON holds the same content plus `banner`, `status: "valid"|"invalid"|"abstain"`, `model`, and `facts_used`.
  - `make_brief(run_id, db, as_of_week, purpose) -> Path`, writing `briefs/{run_id}/week_{NN}.{md,json}`:
    - If the detector result has a global abstention, write an abstain-only brief **without any LLM call**.
    - If there are no alerts, write a deterministic "No alerts; peer-relative residuals within normal range" brief with key facts. This is also no LLM call *(planner's call: saves tokens; the LLM adds nothing when there's nothing to explain)*.
    - Otherwise run the agent and validate. On errors, do one retry with the errors appended as a user message. If it still fails, write status `invalid` to `briefs/{run_id}/week_{NN}.invalid.json` and exit 2.
  - CLI: `python -m agent brief --run {injected,control} --as-of-week N [--final] [--yes]`.

- [ ] **Step 1:** Write the tests:
  - `test_banner_first_line`.
  - `test_hallucinated_number_rejected`: "acceptance rose 12%" fails *(Review Focus 5)*.
  - `test_unknown_fact_id_rejected` *(Review Focus 5)*.
  - `test_segment_ids_and_dates_allowed`.
  - `test_fails_closed_after_one_retry`: a fake LLM always returns a bad brief; exactly 2 agent runs, an `.invalid.json` is written, and no `.md` *(Review Focus 5)*.
  - `test_abstain_brief_makes_no_llm_call`: `as_of_week=6` with an LLM whose factory raises if called *(Review Focus 3)*.
  - `test_no_alert_brief_makes_no_llm_call`: the control run at week 33 (`2025-08-25`, inside the Q3 dip).
  - `test_every_rendered_number_has_citation`: in the rendered markdown, every number is followed by a `[Q…]` or `[D…]` citation, or sits in the ranked-actions table row that carries its IDs.
  - `test_missing_ranked_alert_rejected`.
  - `test_every_usd_figure_labeled_sample_scale`.
  - `test_scenario_estimate_rendered_as_range_with_midpoint_note`.
  - `test_no_9b_in_brief`: the rendered brief contains no `$9B`/`9,000,000,000`/`$90M` figure.
- [ ] **Step 2:** Run. Expected: FAIL.
- [ ] **Step 3:** Implement.
- [ ] **Step 4:** Run `pytest tests/agent -v`. Expected: PASS.
- [ ] **Step 5:** Live dev smoke test. **Ask the user first.** This is ≤ 16 calls: 1 brief × ≤ 8 turns × ≤ 2 attempts. Run `REPLAY=0 python -m agent brief --run injected --as-of-week <B's first alert week>` with the dev model. Then rerun with `REPLAY=1` and diff the output. Expected: identical, with a `replay: true` token log line.
- [ ] **Step 6:** Commit `feat(agent): grounded rendering, validator, abstention, brief CLI`. Commit the cache files created in Step 5 only if this is the final model. Dev-model cache (`data/llm_cache/dev/`) stays local and gitignored.

**Demo brief weeks** *(planner's call; fixed after Phase 3)*:
- Injected run: the first alert week of each scenario on seed 42 (read from Phase 3 output).
- Control week 33 (`2025-08-25`, inside the Q3 dip): no-alert brief, $0.
- Week 6: abstain brief, $0.

The three scenario briefs are the only LLM spend. Recording them with the final model is ≤ 48 calls, which is above 20, so the executor **must print the count and ask the user** before running `make record-final`.

---

## Phase 5: Evaluation harness

**Phase DoD:** `make eval` (REPLAY) writes `eval/reports/latest.{md,json}`.

**Deterministic detector gates, 10 seeds** *(user: the multi-seed sweep covers deterministic metrics only)*. Thresholds are tuned on seeds 1–5, and gates are reported separately on holdout seeds 6–10:
- **Control:** 0 alerts across 10 seeds × every evaluable week. Also report **false alerts per week on the control run** (alerts / evaluable weeks), per seed and pooled. *(user: talk-track number)*
- **Recall before margin:** each scenario alerts on its true scope before its seed's `cm_first_visible_week` in ≥ 8/10 seeds.
- **Precision:** ≤ 2 alerts on a wrong (kind, scope) in total across the 10 injected runs. Also report wrong alerts per week.
- **Reported, not gated:** median lead weeks and median detection delay per scenario.

**LLM brief gates, one seed (42) with `CLAUDE_MODEL_FINAL` only** *(user, BUDGET RULES)*:
- Grounding 100%.
- Abstention correct 100%.
- **Brief accuracy** *(user)*: ≥ 90% of sections accurate **and** zero direction errors; report both numbers. A section is accurate when it names its alert's scope ID, names no other alert's scope, and uses direction words consistent with the signal direction ("rose / increased / up" for "+", "fell / slowed / down" for "−"). This is checked deterministically.
- The top-ranked action names a true scope in each scenario brief.
- Every $ figure is labeled sample-scale.

If a gate fails on the holdout after honest tuning, report the numbers to the user. Don't loosen the gate.

### Task 14: Detector evaluation across seeds

**Files:** Create `eval/__init__.py`, `eval/kpis.py`, `eval/detector_eval.py`, `tests/eval/test_detector_eval.py`

**Interfaces:**
- `EXPECTED_KIND = {"days_to_first_offer": "demand_softening", "conversion": "adverse_selection", "reno_overrun": "reno_cost_drift"}`, keyed by the ground-truth `effects`.
- `lead_time(truth: dict, alerts_by_week: dict[int, DetectorResult]) -> {first_alert_week, delay_weeks, lead_weeks}`, using `truth["cm_first_visible_week"]` (combined run).
- `run_detector_eval(seeds=range(1, 11)) -> DetectorReport` with `per_seed rows, control_alerts, control_false_alerts_per_week (per seed and pooled), wrong_alerts, wrong_alerts_per_week, recall_before_cm_by_scenario, median_lead_weeks, median_delay_weeks, tuning_vs_holdout`. Each seed runs generator (`--out-dir eval/runs/seed_{n} --truth-path eval/runs/seed_{n}/ground_truth.json`) → dbt build for both targets → detector for every evaluable week of both runs. Results are cached on disk by (seed, git tree hash of generator/dbt_project/detector). Add `eval/runs/` to `.gitignore`.
- `/eval` is the only package allowed to open both databases and read ground truth (`eval/ground_truth.json` for seed 42, `eval/runs/seed_{n}/ground_truth.json` for the sweep).

- [ ] **Step 1:** Write the tests: `test_lead_time_math` (hand-built), `test_wrong_scope_counted`, `test_false_alerts_per_week_math` (hand-built: 1 alert over 40 evaluable weeks gives 0.025), and `test_report_gates_smoke` (`@pytest.mark.slow`; 2 seeds; gate fields present; control_alerts == 0).
- [ ] **Steps 2–5:** Run (FAIL), implement, run with `pytest tests/eval -m "slow or not slow"` (PASS), commit `feat(eval): multi-seed detector evaluation with tuning/holdout split`.

### Task 15: Brief evaluation, cost report, live gating

**Files:** Create `eval/brief_eval.py`, `eval/report.py`, `eval/__main__.py`, `tests/eval/test_brief_eval.py`. Modify the `Makefile` targets `eval:` (REPLAY=1) and `record-final:`.

**Interfaces:**
- Produces: `run_brief_eval(weeks, purpose, live: bool) -> BriefReport` with `grounding_rate, abstention_correct, top_action_correct, invalid_count, calls, input_tokens, output_tokens, cache_read_tokens, est_cost_usd | None`. Tokens and cost are summed from `token_log.jsonl` lines tagged with this eval's `run_tag`. `planned_calls(weeks) = n_llm_briefs × 8 × 2`.
- `python -m eval [--live] [--final] [--yes]`: when `--live` and `planned_calls > 20`, print `Planned live calls: N (model M). Proceed? [y/N]` and abort unless `y` or `--yes`.
- Brief eval runs on **seed 42 only**, at the demo brief weeks, and live recording uses `CLAUDE_MODEL_FINAL` only. The signature becomes `run_brief_eval(weeks, live: bool) -> BriefReport` (no seed or model arguments). `planned_calls` = 3 LLM briefs × 8 turns × 2 attempts = 48, so the user must confirm before recording.
- `BriefReport` also has `section_accuracy: float`, `direction_errors: int` and `sample_scale_labeled: bool`. `brief_accuracy(brief, result) -> BriefAccuracy(section_accuracy, direction_errors)` lives in `eval/brief_accuracy.py`. ("Semantic-layer accuracy" in SPEC.md is a different metric: NL questions answered via the semantic layer vs raw SQL.)
- `write_report(detector_report, brief_report, path)` produces markdown with the banner, a gates table (PASS/FAIL, tuning vs holdout seeds), KPIs, a tokens table, estimated cost, and a "Known limitations" block: simultaneous all-segment shifts; the demand-softening impact is a lower bound; adverse-selection impact is a scenario estimate until resales confirm it.

- [ ] **Step 1:** Write the tests:
  - `test_brief_accuracy_checks_scope_and_direction`: a hand-built brief with one wrong-direction section out of 2 gives section_accuracy 0.5 and direction_errors 1.
  - `test_brief_eval_is_single_seed_final_model`: the live path constructs `LLM` with `purpose="final"` only.
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
  - `GET /api/alerts?run&as_of_week` → alerts.json content
  - `GET /api/series?run&metric&scope&as_of_week` → `{weeks, values, peer_median, residual, z, query_id, alerts:[{alert_id, onset_week}]}`, from `peer_residuals`/`rollup`/`score`.
  - `GET /api/kpis?run` → lead-time table from Task 14
  - `GET /api/brief?run&as_of_week` → brief JSON + markdown, or **404** if none exists. Never generate.
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

**Files:** Create `web/` (Vite React TS template + Tailwind + Recharts): `src/banner.ts`, `src/data.ts` (fetches from `/api/*` or, when `import.meta.env.VITE_STATIC`, from `data/*.json` via the manifest), `src/components/Layout.tsx` (sticky banner on every route), `src/pages/{Overview,Scope,Brief,Lag}.tsx`, `web/tests/e2e.spec.ts` (Playwright). Add `tests/test_banner_sync.py`, which asserts `web/src/banner.ts` contains `SYNTHETIC_BANNER`.

**Pages** *(planner's call)*:
- **Overview:** a run toggle (injected/control), an as-of week slider, and the ranked-actions table (sample-scale $ and bps of CM, basis, action, owner, query-ID chips). Plus a portfolio CM chart that shows the Q3 dip with no alert. Every $ carries the sample-scale label.
- **Scope** (market or band): leading-indicator small multiples (scope value vs peer median, residual z, onset and first-alert markers) with a CM chart below, so the lag between "alert fired" and "CM moved" is visible.
- **Lag:** the headline view. Per scenario, onset → detection → CM breach on a timeline, with days labeled.
- **Brief:** rendered markdown. Clicking a citation opens a side panel with the query's metric, scope, window, values and SQL. It also has a feedback form (hidden when `VITE_STATIC`).

- [ ] **Step 1:** Write the Playwright tests. Run them against `make demo` and, separately, against `vite preview` of the static build.
  - `banner visible on /, /scope/B2, /lag, /brief`.
  - `overview lists B2 adverse_selection at B's seed-42 first alert week`.
  - `control run shows "No alerts" at week 33 (2025-08-25)`.
  - `every $ on the overview has the sample-scale label`.
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
8. Limitations: synthetic data; sample-scale dollars (~$1.6B/yr portfolio); **simultaneous all-segment shifts** (peer-relative residuals cancel them, and the portfolio check only catches abrupt ones); demand-softening impact is a lower bound; adverse-selection impact is a scenario estimate (1–3% resale shortfall × excess_share) until resales confirm it; detector scores (z, CUSUM) are uncalibrated, not probabilities; no auth or rate limiting.

- [ ] **Step 1:** Write the tests:
  - `test_readme_banner`.
  - `test_readme_results_match_report`: the numbers in the README table equal `latest.json`.
  - `test_no_secrets_committed`: `git ls-files` content matches no real-key pattern `sk-ant-[A-Za-z0-9_-]{20,}` and no `MARGIN_RADAR_API_KEY=` followed by a value. (The vendored claude-api skill docs mention the `sk-ant-` prefix with `...` placeholders, so a bare prefix match would false-positive.)
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
