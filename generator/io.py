"""Write simulation output to Parquet and load each run into its own DuckDB file (schema `raw`)."""
from pathlib import Path

import duckdb

from generator.simulate import SimOutput

TABLES = ("homes", "price_cuts")


def write_parquet(out: SimOutput, run_dir: Path) -> None:
    run_dir.mkdir(parents=True, exist_ok=True)
    out.homes.to_parquet(run_dir / "homes.parquet", index=False)
    out.price_cuts.to_parquet(run_dir / "price_cuts.parquet", index=False)


def load_duckdb(db_path: Path, run_dir: Path) -> None:
    """Replace raw.<table> in this run's own database. One database per run, so runs can't be joined."""
    with duckdb.connect(str(db_path)) as con:
        con.execute("begin transaction")
        con.execute("create schema if not exists raw")
        for table in TABLES:
            source = _literal(str(run_dir / f"{table}.parquet"))
            con.execute(f"create or replace table raw.{table} as select * from read_parquet({source})")
        con.execute("commit")


def _literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"
