"""FastAPI app for the dashboard. Always replay-only: it never calls Claude (CLAUDE.md BUDGET RULE 4).
Synthetic data — not Opendoor data.

uvicorn api.main:app --port 8000
"""
import os
import threading
from contextlib import asynccontextmanager

os.environ["REPLAY"] = "1"  # before anything that could construct an LLM client

from pathlib import Path  # noqa: E402

from fastapi import FastAPI, HTTPException, Request  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402
from fastapi.responses import JSONResponse  # noqa: E402
from pydantic import BaseModel, Field  # noqa: E402

import duckdb  # noqa: E402

from api.services import Services  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]


class DecisionIn(BaseModel):
    alert_id: str = Field(max_length=32)
    decision: str
    reason: str = Field(max_length=500)
    decided_week: int


def create_app(data_dir: Path = ROOT / "data", briefs_dirs: list[Path] | None = None, eval_dir: Path = ROOT / "eval",
               decisions_db: Path = ROOT / "data" / "decisions.duckdb") -> FastAPI:
    services = Services(data_dir, briefs_dirs or [ROOT / "briefs", ROOT / "eval" / "briefs"], eval_dir, decisions_db)
    @asynccontextmanager
    async def lifespan(_: FastAPI):
        services.warming.set()  # before the thread starts, so no early request slips past the wait
        threading.Thread(target=services.warm, name="warm-episodes", daemon=True).start()
        yield
        services.close()

    app = FastAPI(title="Margin Radar API", description="Synthetic data — not Opendoor data.", lifespan=lifespan)
    app.state.services = services
    app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
                       allow_methods=["GET", "POST"], allow_headers=["*"])

    @app.exception_handler(ValueError)
    async def bad_request(_: Request, exc: ValueError):
        return JSONResponse(status_code=422, content={"detail": str(exc)})

    @app.get("/api/meta")
    def meta():
        return services.meta()

    @app.get("/api/radar")
    def radar(run: str, week: int):
        return services.radar(run, week)

    @app.get("/api/heatmap")
    def heatmap(run: str, week: int, metric: str):
        return services.heatmap(run, week, metric)

    @app.get("/api/drilldown")
    def drilldown(run: str, metric: str, dimension: str, scope: str):
        return services.drilldown(run, metric, dimension, scope)

    @app.get("/api/cohort")
    def cohort(run: str, week: int, level: str, scope: str, start: int, end: int):
        return services.cohort(run, week, level, scope, start, end)

    @app.get("/api/briefs")
    def briefs():
        return services.briefs()

    @app.get("/api/brief")
    def brief(week: int):
        found = services.brief(week)
        if found is None:
            raise HTTPException(status_code=404, detail=f"no brief for week {week}")
        return found

    @app.get("/api/eval")
    def evaluation():
        return services.evaluation()

    @app.get("/api/decisions")
    def decisions(decision: str | None = None, kind: str | None = None, scope: str | None = None):
        return services.decisions_view(decision, kind, scope)

    @app.post("/api/decisions")
    def add_decision(body: DecisionIn):
        try:
            return services.add_decision(body.model_dump())
        except duckdb.Error as exc:  # the decision log is busy (another writer): ask the client to retry
            raise HTTPException(status_code=503, detail="decision log is busy; try again") from exc

    return app


app = create_app()
