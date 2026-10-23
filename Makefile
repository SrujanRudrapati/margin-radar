PY := conda run --no-capture-output -n margin-radar python
SEED ?= 42

.PHONY: setup data test build

setup:
	conda env update -n margin-radar -f environment.yml

data:
	$(PY) -m generator --seed $(SEED) --out-dir data

DBT := conda run --no-capture-output -n margin-radar dbt
DBT_ARGS := --project-dir dbt_project --profiles-dir dbt_project

build:
	$(DBT) build $(DBT_ARGS) --target injected
	$(DBT) build $(DBT_ARGS) --target control

test:
	$(PY) -m pytest
