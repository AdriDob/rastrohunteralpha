import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database import db
from api.routers import (
    targets,
    endpoints,
    findings,
    evidence,
    opportunities,
    attack_surface,
    pipeline,
    reports,
    hypotheses,
    roi,
)

logger = logging.getLogger("rastro.api")

app = FastAPI(title="Rastro API", version="0.3")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(targets.router)
app.include_router(endpoints.router)
app.include_router(findings.router)
app.include_router(evidence.router)
app.include_router(opportunities.router)
app.include_router(attack_surface.router)
app.include_router(pipeline.router)
app.include_router(reports.router)
app.include_router(hypotheses.router)
app.include_router(roi.router)


@app.on_event("startup")
async def startup():
    db.init_db()
    logger.info("Database initialized")


@app.get("/api/health")
async def health():
    return {"status": "ok", "app": "Rastro API"}
