"""A clean clone must be able to `make setup` then `make export` / `make demo`. Synthetic data — not Opendoor data."""
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_environment_pins_the_api_stack():
    env = (ROOT / "environment.yml").read_text()
    for package in ("fastapi", "uvicorn", "httpx"):
        assert re.search(rf"^\s*-\s*{package}==\S+", env, re.MULTILINE), f"{package} not pinned in environment.yml"


def test_environment_pins_playwright_as_dev_dependency():
    env = (ROOT / "environment.yml").read_text()
    assert re.search(r"^\s*-\s*playwright==\S+\s*#.*dev", env, re.MULTILINE), "playwright not pinned as a dev dependency"


def test_export_builds_the_governed_mart_first():
    # without `build`, decisions/markers run against a database with no dbt mart and the export aborts
    plan = subprocess.run(["make", "-n", "export"], cwd=ROOT, capture_output=True, text=True, check=True).stdout
    assert "dbt build" in plan or " dbt " in plan


def test_every_target_that_reads_the_mart_builds_it_first():
    for target in ("eval", "briefs", "markers", "decisions"):
        plan = subprocess.run(["make", "-n", target], cwd=ROOT, capture_output=True, text=True, check=True).stdout
        assert " dbt " in plan or "dbt build" in plan, f"make {target} does not build the governed mart"
