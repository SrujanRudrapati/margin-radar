PY := conda run --no-capture-output -n margin-radar python
SEED ?= 42

.PHONY: setup data test build detect briefs eval record-final decisions markers api export demo

setup:
	conda env update -n margin-radar -f environment.yml

data:
	$(PY) -m generator --seed $(SEED) --out-dir data

# File rule so `make build` from a clean clone generates data, but never regenerates existing data.
# The generator writes both databases in one run.
data/radar_injected.duckdb:
	$(PY) -m generator --seed $(SEED) --out-dir data

data/radar_control.duckdb: data/radar_injected.duckdb

DBT := conda run --no-capture-output -n margin-radar dbt
DBT_ARGS := --project-dir dbt_project --profiles-dir dbt_project

MF := conda run --no-capture-output -n margin-radar mf

# mf reads dbt_project/target/semantic_manifest.json, so run it from dbt_project after `dbt parse`.
build: data/radar_injected.duckdb data/radar_control.duckdb
	$(DBT) build $(DBT_ARGS) --target injected
	$(DBT) build $(DBT_ARGS) --target control
	cd dbt_project && MR_TARGET=injected MR_DB_PATH=../data/radar_injected.duckdb $(DBT) parse --profiles-dir . --target injected && MR_TARGET=injected MR_DB_PATH=../data/radar_injected.duckdb $(MF) validate-configs
	cd dbt_project && MR_TARGET=control MR_DB_PATH=../data/radar_control.duckdb $(DBT) parse --profiles-dir . --target control && MR_TARGET=control MR_DB_PATH=../data/radar_control.duckdb $(MF) validate-configs

test:
	$(PY) -m pytest

detect: data/radar_injected.duckdb data/radar_control.duckdb
	$(PY) -m detector --db data/radar_injected.duckdb --run-id injected --all-weeks --out data/out
	$(PY) -m detector --db data/radar_control.duckdb --run-id control --all-weeks --out data/out

# Demo briefs: always REPLAY=1 (recorded responses only; never a live call). Week 6 abstains, week 33 is inside the
# Q3 margin dip with no alerts (both deterministic, no LLM); week 40 is the recorded final-model sample brief.
briefs: data/radar_injected.duckdb
	REPLAY=1 $(PY) -m agent brief --db data/radar_injected.duckdb --as-of-week 6 --out briefs
	REPLAY=1 $(PY) -m agent brief --db data/radar_injected.duckdb --as-of-week 33 --out briefs
	REPLAY=1 $(PY) -m agent brief --db data/radar_injected.duckdb --as-of-week 40 --purpose final --out briefs

# Evaluation: replay-only (recorded LLM responses; never a live call). Writes eval/results.json + eval/results.md.
eval: data/radar_injected.duckdb
	REPLAY=1 $(PY) -m eval

# Record missing eval LLM responses with CLAUDE_MODEL_FINAL. Prints the planned call count and asks first.
record-final: data/radar_injected.duckdb
	$(PY) -m eval --live

# Decision log (feedback loop): seed example decisions and score them against realized margin (deterministic, no LLM).
decisions: data/radar_injected.duckdb
	$(PY) -m agent decisions seed --db data/radar_injected.duckdb --log data/decisions.duckdb > /dev/null
	$(PY) -m agent decisions score --db data/radar_injected.duckdb --log data/decisions.duckdb > data/decision_scores.json

# Lead-time markers for the dashboard (eval is the only reader of ground truth).
markers: data/radar_injected.duckdb
	$(PY) -m eval.markers

# Dashboard API: always replay-only (never calls Claude).
api: data/radar_injected.duckdb data/radar_control.duckdb
	REPLAY=1 conda run --no-capture-output -n margin-radar uvicorn api.main:app --port 8000

web/node_modules: web/package-lock.json
	cd web && npm ci
	touch web/node_modules

# Pre-render every API response to JSON and build the static dashboard into web/dist (no server, no Claude).
export: build decisions markers web/node_modules
	REPLAY=1 $(PY) -m api.export --out web/public/data
	cd web && npm run build:static

# Whole pipeline from a clean clone, replay-only: zero live API calls, no .env needed.
# Then serves the API on :8000 and the dashboard on http://localhost:5173 until Ctrl-C.
demo: build detect briefs decisions markers web/node_modules
	@echo "Synthetic data — not Opendoor data. Dashboard: http://localhost:5173 (API :8000, REPLAY=1)"
	trap 'kill 0' EXIT; REPLAY=1 conda run --no-capture-output -n margin-radar uvicorn api.main:app --port 8000 & \
	cd web && npx vite --port 5173 --strictPort
