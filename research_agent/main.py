"""
NEXUS Research Agent — FastAPI Application Entry Point.

Configures CORS, mounts the API router, sets up structured logging,
and provides the uvicorn entry point.

Start the server:
    python main.py
    # or
    uvicorn main:app --host 0.0.0.0 --port 8000 --reload
"""

import sys
import os

# Ensure the project root is on the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import router
from api.auth_routes import router as auth_router
from api.history_routes import router as history_router
from config import settings
from db import init_db
from services.logger import configure_logging

import structlog

# ── Configure structured logging ──
configure_logging(log_level="INFO")
log = structlog.get_logger()

# ── Create FastAPI app ──
app = FastAPI(
    title="NEXUS Research Agent API",
    description=(
        "Autonomous AI Research Agent with ReAct reasoning, "
        "multi-source search, self-correcting confidence evaluation, "
        "and streamed thinking steps via SSE."
    ),
    version="2.4.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

# ── CORS middleware ──
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_origin_regex=settings.allowed_origin_regex,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Mount API routes ──
app.include_router(router)
app.include_router(auth_router)
app.include_router(history_router)


# ── Startup event ──
@app.on_event("startup")
async def startup() -> None:
    """Initialise DB and log agent configuration on server startup."""
    await init_db()
    log.info(
        "nexus.startup",
        model_fast=settings.gemini_model_fast,
        model_pro=settings.gemini_model_pro,
        max_iterations=settings.max_iterations,
        confidence_threshold=settings.confidence_threshold,
        min_sources=settings.min_sources_required,
        cors_origins=settings.allowed_origins,
        database=settings.database_url.split("://", 1)[0],
    )


# ── Shutdown event ──
@app.on_event("shutdown")
async def shutdown() -> None:
    """Log graceful shutdown."""
    log.info("nexus.shutdown")


# ── Direct execution entry point ──
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )
