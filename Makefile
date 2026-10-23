PY := conda run --no-capture-output -n margin-radar python
SEED ?= 42

.PHONY: setup data test build

setup:
	conda env update -n margin-radar -f environment.yml

data:
	$(PY) -m generator --seed $(SEED) --out-dir data

DBT := conda run --no-capture-output -n margin-radar dbt
DBT_ARGS := --project-dir dbt_project --profiles-dir dbt_project

MF := conda run --no-capture-output -n margin-radar mf

# mf reads dbt_project/target/semantic_manifest.json, so run it from dbt_project after `dbt parse`.
build:
	$(DBT) build $(DBT_ARGS) --target injected
	$(DBT) build $(DBT_ARGS) --target control
	cd dbt_project && MR_TARGET=injected MR_DB_PATH=../data/radar_injected.duckdb $(DBT) parse --profiles-dir . --target injected && MR_TARGET=injected MR_DB_PATH=../data/radar_injected.duckdb $(MF) validate-configs
	cd dbt_project && MR_TARGET=control MR_DB_PATH=../data/radar_control.duckdb $(DBT) parse --profiles-dir . --target control && MR_TARGET=control MR_DB_PATH=../data/radar_control.duckdb $(MF) validate-configs

test:
	$(PY) -m pytest
