import subprocess
from pathlib import Path

from common.banner import SYNTHETIC_BANNER
from common import business

ROOT = Path(__file__).resolve().parents[1]
CODE_SUFFIXES = {".py", ".ts", ".tsx", ".yml", ".yaml", ".toml", ".sql", ".json", ".sh"}
SKIP_DIRS = {".git", ".claude", "node_modules", ".venv", "data", "dbt_project/target"}


def test_banner_exact():
    assert SYNTHETIC_BANNER == "Synthetic data — not Opendoor data."


def test_business_constants():
    assert business.CM_FLOOR_PCT == 0.045
    assert business.SAMPLE_SCALE_LABEL == "sample-scale ($ at the synthetic portfolio's ~$1.6B/yr)"


def test_env_is_gitignored():
    result = subprocess.run(["git", "check-ignore", ".env"], cwd=ROOT, capture_output=True)
    assert result.returncode == 0


def test_no_forbidden_key_name_in_code():
    forbidden = "ANTHROPIC_" + "API_KEY"
    hits = [
        p for p in ROOT.rglob("*")
        if p.is_file() and p.suffix in CODE_SUFFIXES
        and not any(part in SKIP_DIRS for part in p.relative_to(ROOT).parts)
        and forbidden in p.read_text(errors="ignore")
    ]
    assert hits == []


SCALED_CODE_SUFFIXES = {".py", ".sql", ".ts", ".tsx", ".yml"}
FORBIDDEN_SCALING = ("9_000" + "_000_000", "9e" + "9", "90_000" + "_000")


def test_no_9b_scaling():
    hits = []
    for p in ROOT.rglob("*"):
        rel = p.relative_to(ROOT)
        if not p.is_file() or p.suffix not in SCALED_CODE_SUFFIXES:
            continue
        if any(part in SKIP_DIRS for part in rel.parts) or rel.as_posix().startswith("dbt_project/target"):
            continue
        text = p.read_text(errors="ignore")
        if any(token in text for token in FORBIDDEN_SCALING):
            hits.append(rel.as_posix())
    assert hits == []
