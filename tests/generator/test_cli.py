import json
from pathlib import Path

import duckdb
import pandas as pd
import pytest

from generator.__main__ import _parse, main

RUNS = ("injected", "control")


def _query(db, sql):
    with duckdb.connect(str(db), read_only=True) as con:
        return con.sql(sql).fetchall()


def _rows(out, run, table="homes"):
    return len(pd.read_parquet(out / "parquet" / run / f"{table}.parquet"))


@pytest.fixture(scope="module")
def out(tmp_path_factory):
    d = tmp_path_factory.mktemp("gen")
    main(["--seed", "42", "--out-dir", str(d), "--truth-path", str(d / "eval" / "ground_truth.json")])
    return d


def test_writes_parquet_for_both_runs(out):
    for run in RUNS:
        for table in ("homes", "price_cuts"):
            assert (out / "parquet" / run / f"{table}.parquet").exists()


def test_writes_one_database_per_run(out):
    assert (out / "radar_injected.duckdb").exists()
    assert (out / "radar_control.duckdb").exists()
    assert not (out / "radar.duckdb").exists()


def test_each_database_holds_only_its_run(out):
    for run in RUNS:
        db = out / f"radar_{run}.duckdb"
        assert _query(db, "select count(*) from raw.homes")[0][0] == _rows(out, run)
        assert _query(db, "select count(*) from raw.price_cuts")[0][0] == _rows(out, run, "price_cuts")
        cols = [c for (c,) in _query(db, "select column_name from information_schema.columns "
                                         "where table_schema = 'raw' and table_name = 'homes' order by ordinal_position")]
        assert cols == list(pd.read_parquet(out / "parquet" / run / "homes.parquet").columns)


def test_raw_tables_carry_no_answer_key(out):
    for run in RUNS:
        cols = {c for (c,) in _query(
            out / f"radar_{run}.duckdb", "select column_name from information_schema.columns where table_schema = 'raw'"
        )}
        assert not {c for c in cols if any(w in c for w in ("scenario", "inject", "true_value", "truth", "run_id"))}


def test_ground_truth_written_to_truth_path_only(out):
    gt = json.loads((out / "eval" / "ground_truth.json").read_text())
    assert gt["seed"] == 42
    assert [s["scenario"] for s in gt["scenarios"]] == ["A", "B", "C"]
    assert gt["banner"] == "Synthetic data — not Opendoor data."
    assert not (out / "ground_truth.json").exists()


def test_default_truth_path_is_under_eval():
    assert _parse([]).truth_path == Path("eval/ground_truth.json")


def test_rerun_replaces_tables(out):
    main(["--seed", "42", "--out-dir", str(out), "--truth-path", str(out / "eval" / "ground_truth.json")])
    assert _query(out / "radar_control.duckdb", "select count(*) from raw.homes")[0][0] == _rows(out, "control")


def test_flags_select_and_move_injections(tmp_path):
    truth = tmp_path / "gt.json"
    main(["--seed", "42", "--out-dir", str(tmp_path), "--truth-path", str(truth), "--inject", "A",
          "--a-market", "M03", "--a-start-week", "20"])
    (a,) = json.loads(truth.read_text())["scenarios"]
    assert (a["scenario"], a["scope"], a["start_week"]) == ("A", "M03", 20)


def test_rejects_unknown_market(tmp_path):
    with pytest.raises(SystemExit):
        main(["--out-dir", str(tmp_path), "--a-market", "M99"])


def test_rejects_empty_inject(tmp_path):
    with pytest.raises(SystemExit):
        main(["--out-dir", str(tmp_path), "--inject", ""])


def test_out_dir_with_quote(tmp_path):
    d = tmp_path / "it's here"
    main(["--seed", "3", "--out-dir", str(d), "--truth-path", str(d / "gt.json"), "--inject", "C"])
    assert _query(d / "radar_injected.duckdb", "select count(*) from raw.homes")[0][0] == _rows(d, "injected")


def test_cli_logs_banner(tmp_path, caplog):
    caplog.set_level("INFO", logger="generator")
    main(["--seed", "3", "--out-dir", str(tmp_path), "--truth-path", str(tmp_path / "gt.json"), "--inject", "C"])
    assert "Synthetic data — not Opendoor data." in caplog.text
