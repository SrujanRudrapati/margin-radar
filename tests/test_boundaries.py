"""/detector and /agent see one run through a database path they are given; only /eval sees both runs."""
import ast
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
GUARDED = ("detector", "agent")
FORBIDDEN_IMPORTS = ("generator", "eval")
FORBIDDEN_LITERALS = ("radar_injected", "radar_control", "ground_truth")


def boundary_violations(package_dir: Path) -> list[str]:
    found = []
    for path in sorted(package_dir.rglob("*.py")):
        tree = ast.parse(path.read_text(), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                modules = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                modules = [node.module or ""]
            else:
                modules = []
            found += [f"{path}: imports {m}" for m in modules if m.split(".")[0] in FORBIDDEN_IMPORTS]
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                found += [f"{path}: references {lit}" for lit in FORBIDDEN_LITERALS if lit in node.value]
    return found


@pytest.mark.parametrize("package", GUARDED)
def test_guarded_packages_respect_run_boundary(package):
    assert boundary_violations(ROOT / package) == []


def test_scanner_catches_violations(tmp_path):
    (tmp_path / "bad.py").write_text(
        "from generator.config import PRICE_SEASON_BY_MONTH\nimport eval.kpis\nDB = 'data/radar_control.duckdb'\n"
    )
    found = boundary_violations(tmp_path)
    assert len(found) == 3


def test_governed_store_cannot_reach_another_run(built_runs):
    """/detector and /agent read data only through GovernedStore; its connection can't attach or scan other files."""
    import duckdb

    from detector.governed import GovernedStore
    control = built_runs["control"]
    with GovernedStore(str(built_runs["injected"]), "injected") as store:
        attached = [r[0] for r in store._con.execute(
            "select path from duckdb_databases() where not internal and path is not null").fetchall()]
        assert attached == [str(built_runs["injected"])]
        for sql in (f"attach '{control}' as other (read_only)",
                    f"select count(*) from read_parquet('{control.parent / 'parquet' / 'control' / '*.parquet'}')"):
            # blocked by the store's configuration, not merely a missing path
            with pytest.raises(duckdb.PermissionException, match="disabled by configuration"):
                store._con.execute(sql)


def test_agent_tools_take_no_path_or_run_argument():
    """The model's tools can't name a database, file or run: the brief's store is fixed by the CLI's --db."""
    from agent.tools import SCHEMAS
    for schema in SCHEMAS:
        props = set(schema["input_schema"]["properties"])
        assert not {p for p in props if any(w in p for w in ("db", "path", "file", "run"))}, schema["name"]
        assert schema["input_schema"]["additionalProperties"] is False
