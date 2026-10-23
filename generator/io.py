"""Write simulation output to Parquet and load it into DuckDB (schema `raw`)."""
from pathlib import Path

import duckdb

from generator.simulate import SimOutput

TABLES = ("homes", "price_cuts")


def write_parquet(out: SimOutput, run_dir: Path) -> None:
    run_dir.mkdir(parents=True, exist_ok=True)
    out.homes.to_parquet(run_dir / "homes.parquet", index=False)
    out.price_cuts.to_parquet(run_dir / "price_cuts.parquet", index=False)


def load_duckdb(db_path: Path, run_dirs: dict[str, Path]) -> None:
    """Replace raw.<table> with the union of all runs, tagged by run_id."""
    with duckdb.connect(str(db_path)) as con:
        con.execute("create schema if not exists raw")
        for table in TABLES:
            selects = [
                f"select '{run_id}' as run_id, * from read_parquet('{run_dir / f'{table}.parquet'}')"
                for run_id, run_dir in run_dirs.items()
            ]
            con.execute(f"create or replace table raw.{table} as " + " union all by name ".join(selects))
