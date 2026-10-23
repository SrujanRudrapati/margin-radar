"""Pre-render every API response the dashboard needs into static JSON (docs/SPEC.md: `make export`).

python -m api.export --out web/public/data   (replay-only; never calls Claude). Synthetic data — not Opendoor data.
"""
import argparse
import json
import os
from pathlib import Path

os.environ["REPLAY"] = "1"

from api.services import COHORT_WEEKS, DIMENSIONS, RUNS, Services  # noqa: E402
from detector.rules import TRIGGERS  # noqa: E402

FIRST_WEEK = 12  # earlier weeks are all abstentions (burn-in + minimum history)


def export(services: Services, out: Path, weeks: list[int] | None = None, runs: list[str] | None = None) -> dict:
    out = Path(out)
    files = []

    def write(rel: str, payload: dict) -> None:
        path = out / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, default=str))
        files.append(rel)

    meta = services.meta()
    weeks = weeks or list(range(FIRST_WEEK, meta["max_week"] + 1))
    runs = runs or list(RUNS)
    write("meta.json", {**meta, "static": True, "export_weeks": weeks})
    for run in runs:
        for week in weeks:
            write(f"radar/{run}/{week}.json", services.radar(run, week))
            for metric in TRIGGERS:
                write(f"heatmap/{run}/{week}/{metric}.json", services.heatmap(run, week, metric))
        for metric in TRIGGERS:
            for dimension in DIMENSIONS:
                for scope in meta["markets" if dimension == "market" else "bands"]:
                    write(f"drilldown/{run}/{metric}/{dimension}/{scope}.json",
                          services.drilldown(run, metric, dimension, scope))
        for level, scopes in (("market", meta["markets"]), ("band", meta["bands"])):
            for scope in scopes:
                write(f"cohort/{run}/{level}/{scope}.json",
                      services.cohort(run, meta["max_week"], level, scope, *COHORT_WEEKS))
    write("briefs.json", services.briefs())
    for item in services.briefs()["briefs"]:
        write(f"brief/{item['week']}.json", services.brief(item["week"]))
    write("eval.json", services.evaluation())
    write("decisions.json", services.decisions_view())
    manifest = {"banner": meta["banner"], "files": files}
    (out / "manifest.json").write_text(json.dumps(manifest))
    return manifest


if __name__ == "__main__":
    from api.main import create_app
    parser = argparse.ArgumentParser(description="Synthetic data — not Opendoor data.")
    parser.add_argument("--out", type=Path, default=Path("web/public/data"))
    args = parser.parse_args()
    manifest = export(create_app().state.services, args.out)
    print(f"wrote {len(manifest['files'])} files to {args.out}")
