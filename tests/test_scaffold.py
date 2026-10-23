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
    assert business.RUN_RATE_USD == 9_000_000_000
    assert business.CM_FLOOR_PCT == 0.045
    assert business.USD_PER_100BPS_YEAR == 90_000_000


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
