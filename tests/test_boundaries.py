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
