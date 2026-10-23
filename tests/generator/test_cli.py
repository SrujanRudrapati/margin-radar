import json

import duckdb
import pandas as pd
import pytest

from generator.__main__ import main


def _query(db, sql):
    with duckdb.connect(str(db), read_only=True) as con:
        return con.sql(sql).fetchall()


@pytest.fixture(scope="module")
def out(tmp_path_factory):
    d = tmp_path_factory.mktemp("gen")
    main(["--seed", "42", "--out-dir", str(d)])
    return d


def test_writes_parquet_for_both_runs(out):
    for run in ("injected", "control"):
        for table in ("homes", "price_cuts"):
            assert (out / "parquet" / run / f"{table}.parquet").exists()


def test_loads_both_runs_into_radar_duckdb(out):
    rows = dict(_query(out / "radar.duckdb", "select run_id, count(*) from raw.homes group by 1"))
    parquet_rows = len(pd.read_parquet(out / "parquet" / "control" / "homes.parquet"))
    assert set(rows) == {"injected", "control"}
    assert rows["control"] == parquet_rows
    assert _query(out / "radar.duckdb", "select count(*) from raw.price_cuts")[0][0] > 0


def test_raw_tables_carry_no_answer_key(out):
    cols = {c for (c,) in _query(
        out / "radar.duckdb", "select column_name from information_schema.columns where table_schema = 'raw'"
    )}
    assert not {c for c in cols if any(w in c for w in ("scenario", "inject", "true_value", "truth"))}


def test_ground_truth_json(out):
    gt = json.loads((out / "ground_truth.json").read_text())
    assert gt["seed"] == 42
    assert [s["scenario"] for s in gt["scenarios"]] == ["A", "B", "C"]
    assert gt["banner"] == "Synthetic data — not Opendoor data."


def test_rerun_replaces_tables(out):
    main(["--seed", "42", "--out-dir", str(out)])
    parquet_rows = len(pd.read_parquet(out / "parquet" / "control" / "homes.parquet"))
    n = _query(out / "radar.duckdb", "select count(*) from raw.homes where run_id = 'control'")[0][0]
    assert n == parquet_rows


def test_flags_select_and_move_injections(tmp_path):
    main(["--seed", "42", "--out-dir", str(tmp_path), "--inject", "A",
          "--a-market", "M03", "--a-start-week", "20"])
    (a,) = json.loads((tmp_path / "ground_truth.json").read_text())["scenarios"]
    assert (a["scenario"], a["scope"], a["start_week"]) == ("A", "M03", 20)


def test_rejects_unknown_market(tmp_path):
    with pytest.raises(SystemExit):
        main(["--out-dir", str(tmp_path), "--a-market", "M99"])


def test_rejects_empty_inject(tmp_path):
    with pytest.raises(SystemExit):
        main(["--out-dir", str(tmp_path), "--inject", ""])


def test_out_dir_with_quote(tmp_path):
    d = tmp_path / "it's here"
    main(["--seed", "3", "--out-dir", str(d), "--inject", "C"])
    assert _query(d / "radar.duckdb", "select count(distinct run_id) from raw.homes")[0][0] == 2


def test_cli_logs_banner(tmp_path, caplog):
    caplog.set_level("INFO", logger="generator")
    main(["--seed", "3", "--out-dir", str(tmp_path), "--inject", "C"])
    assert "Synthetic data — not Opendoor data." in caplog.text
