PY := conda run --no-capture-output -n margin-radar python
SEED ?= 42

.PHONY: setup data test build detect briefs

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
