"""Shared session fixtures: generate seed-42 data into a tmp dir and build the dbt marts there.

Never touches the repo's data/ or eval/ground_truth.json. Synthetic data — not Opendoor data.
"""
import os
import subprocess
import sys
from pathlib import Path

import duckdb
import pytest

from generator.io import load_duckdb, write_parquet
from generator.scenarios import default_scenarios
from generator.simulate import simulate

ROOT = Path(__file__).resolve().parents[1]
DBT_PROJECT = ROOT / "dbt_project"
DBT_BIN = Path(sys.executable).parent / "dbt"
SEED = 42


def dbt_build(db_path: Path, target: str, work_dir: Path) -> None:
    """Run `dbt build` against one run's database, keeping artifacts under work_dir."""
    env = {**os.environ, "MR_DB_PATH": str(db_path), "MR_TARGET": target}
    cmd = [
        str(DBT_BIN), "build", "--project-dir", str(DBT_PROJECT), "--profiles-dir", str(DBT_PROJECT),
        "--target", target, "--target-path", str(work_dir / f"target_{db_path.stem}"),
        "--log-path", str(work_dir / f"logs_{db_path.stem}"),
    ]
    result = subprocess.run(cmd, cwd=ROOT, env=env, capture_output=True, text=True)
    assert result.returncode == 0, result.stdout[-3000:] + result.stderr[-2000:]


def query(db_path: Path, sql: str) -> list[tuple]:
    with duckdb.connect(str(db_path), read_only=True) as con:
        return con.execute(sql).fetchall()


@pytest.fixture(scope="session")
def built_runs(tmp_path_factory) -> dict[str, Path]:
    work = tmp_path_factory.mktemp("dbt_runs")
    subprocess.run(
        [sys.executable, "-m", "generator", "--seed", str(SEED), "--out-dir", str(work),
         "--truth-path", str(work / "ground_truth.json")],
        cwd=ROOT, check=True, capture_output=True,
    )
    dbs = {run: work / f"radar_{run}.duckdb" for run in ("injected", "control")}
    for run, db in dbs.items():
        dbt_build(db, run, work)
    return dbs


CUTOFF_WEEK = 40


@pytest.fixture(scope="session")
def cutoff_run(tmp_path_factory) -> Path:
    """Injected-scenario run truncated at week 40 (data known as of that week), built with dbt."""
    work = tmp_path_factory.mktemp("dbt_cutoff")
    run_dir = work / "parquet"
    write_parquet(simulate(SEED, default_scenarios(), cutoff_week=CUTOFF_WEEK), run_dir)
    db = work / "radar_cutoff40.duckdb"
    load_duckdb(db, run_dir)
    dbt_build(db, "injected", work)
    return db


@pytest.fixture(autouse=True, scope="session")
def _no_live_llm_calls():
    """pytest never makes live API calls: force replay mode and hide the key."""
    mp = pytest.MonkeyPatch()
    mp.setenv("REPLAY", "1")
    mp.delenv("MARGIN_RADAR_API_KEY", raising=False)
    yield
    mp.undo()
