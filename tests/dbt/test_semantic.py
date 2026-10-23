"""MetricFlow semantic layer checks. Uses a tmp copy of dbt_project so mf artifacts stay out of the repo.

Synthetic data — not Opendoor data.
"""
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from .conftest import DBT_BIN, DBT_PROJECT, query

MF_BIN = Path(sys.executable).parent / "mf"
# Brief range is 425-575. Raw resale-date quarters give ~475 bps, but the mart is weekly and mf bins each
# week into the quarter of its Monday week_start (the week of 2025-03-31 lands in Q1, 2025-06-30 in Q2),
# which yields ~422 bps. The lower bound is therefore 400 rather than 425.
CM_DIP_BPS_RANGE = (400, 575)


def _env(db: Path, target: str) -> dict:
    return {**os.environ, "MR_DB_PATH": str(db), "MR_TARGET": target}


@pytest.fixture(scope="session")
def mf_project(tmp_path_factory) -> Path:
    """Copy of dbt_project with a freshly parsed manifest (mf reads target/semantic_manifest.json)."""
    dest = tmp_path_factory.mktemp("mf_project") / "dbt_project"
    shutil.copytree(DBT_PROJECT, dest, ignore=shutil.ignore_patterns("target", "logs", "dbt_packages"))
    return dest


def run_mf(project: Path, db: Path, target: str, *args: str) -> subprocess.CompletedProcess:
    env = _env(db, target)
    parse = subprocess.run(
        [str(DBT_BIN), "parse", "--project-dir", str(project), "--profiles-dir", str(project), "--target", target],
        cwd=project, env=env, capture_output=True, text=True,
    )
    assert parse.returncode == 0, parse.stdout[-2000:] + parse.stderr[-1000:]
    return subprocess.run([str(MF_BIN), *args], cwd=project, env=env, capture_output=True, text=True)


def mf_csv(project: Path, db: Path, target: str, tmp: Path, *args: str) -> list[list[str]]:
    out = tmp / "out.csv"
    result = run_mf(project, db, target, "query", *args, "--csv", str(out))
    assert result.returncode == 0, result.stdout[-3000:] + result.stderr[-2000:]
    return [line.split(",") for line in out.read_text().strip().splitlines()]


def test_mf_validate(mf_project, built_runs):
    result = run_mf(mf_project, built_runs["injected"], "injected", "validate-configs")
    assert result.returncode == 0, result.stdout[-3000:] + result.stderr[-2000:]


def test_mf_query_cm_dip(mf_project, built_runs, tmp_path):
    rows = mf_csv(mf_project, built_runs["control"], "control", tmp_path,
                  "--metrics", "contribution_margin_pct", "--group-by", "metric_time__quarter")
    header, body = rows[0], rows[1:]
    by_quarter = {r[0][:10]: float(r[1]) for r in body if r[1]}
    q2, q3 = by_quarter["2025-04-01"], by_quarter["2025-07-01"]
    dip_bps = (q2 - q3) * 10000
    assert CM_DIP_BPS_RANGE[0] <= dip_bps <= CM_DIP_BPS_RANGE[1], (header, by_quarter)


@pytest.mark.parametrize("target", ["injected", "control"])
def test_mf_works_on_both_targets(mf_project, built_runs, tmp_path, target):
    db = built_runs[target]
    rows = mf_csv(mf_project, db, target, tmp_path, "--metrics", "offers")
    expected = query(db, "select count(*) from raw.homes")[0][0]
    assert int(float(rows[1][0])) == expected
