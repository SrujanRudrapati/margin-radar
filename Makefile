PY := conda run --no-capture-output -n margin-radar python
SEED ?= 42

.PHONY: setup data test

setup:
	conda env update -n margin-radar -f environment.yml

data:
	$(PY) -m generator --seed $(SEED) --out-dir data

test:
	$(PY) -m pytest
