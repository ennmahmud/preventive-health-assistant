"""
Preventive Health Assistant API
===============================
FastAPI application entry point.
"""

import sys
from pathlib import Path
from contextlib import asynccontextmanager
import logging

# ── Load .env BEFORE importing anything that reads env vars ──────────────────
# Several modules (src.api.auth, src.chatbot.llm.claude_service, etc.) read
# os.environ at import time, so dotenv must be loaded first or those values
# will be silently None.
_PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(_PROJECT_ROOT / ".env", override=False)

from fastapi import FastAPI, Request  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402
from fastapi.responses import JSONResponse  # noqa: E402

from config.settings import API_CONFIG
from src.api.routes.auth import router as auth_router
from src.api.db.users_db import init_db
from src.api.routes.health import router as health_router
from src.api.routes.cvd import router as cvd_router
from src.api.routes.hypertension import router as hypertension_router
from src.api.routes.chatbot import router as chatbot_router
from src.api.routes.profile import router as profile_router
from src.api.routes.assessment import router as assessment_router
from src.api.services.prediction_service import prediction_service
from src.api.services.cvd_prediction_service import cvd_prediction_service
from src.api.services.hypertension_prediction_service import hypertension_prediction_service

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ============== Lifespan Management ==============

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manage application startup and shutdown.

    On startup: Load ML models
    On shutdown: Clean up resources
    """
    # === STARTUP ===
    logger.info("Starting Preventive Health Assistant API...")

    # Surface whether key env vars were picked up — makes config issues obvious.
    import os as _os
    _env_status = {
        "API_KEY":           "set" if _os.getenv("API_KEY")           else "MISSING (open mode)",
        "ELAN_SECRET_KEY":   "set" if _os.getenv("ELAN_SECRET_KEY")   else "MISSING (using dev fallback)",
        "ANTHROPIC_API_KEY": "set" if _os.getenv("ANTHROPIC_API_KEY") else "MISSING (Claude disabled)",
    }
    for _k, _v in _env_status.items():
        logger.info("  env  %-18s %s", _k, _v)

    # Initialise the database. On Postgres this is just a CREATE EXTENSION
    # vector + create_all that no-ops if Alembic has already run; on SQLite
    # (local dev fallback) it creates data/elan.db on first boot.
    try:
        init_db()
        logger.info("✓ Database initialised")
    except Exception as e:
        logger.error(f"✗ Failed to initialise database: {e}")

    # Load the diabetes risk model
    try:
        success = prediction_service.load_model()
        if success:
            logger.info("✓ Diabetes risk model loaded successfully")
        else:
            logger.warning("⚠ Failed to load diabetes risk model")
    except Exception as e:
        logger.error(f"✗ Error loading diabetes model: {e}")

    # Load the CVD risk model (optional — trains separately)
    try:
        success = cvd_prediction_service.load_model()
        if success:
            logger.info("✓ CVD risk model loaded successfully")
        else:
            logger.warning("⚠ CVD model not found — run train_cvd.py to train it")
    except Exception as e:
        logger.error(f"✗ Error loading CVD model: {e}")

    # Load the hypertension risk model (optional — trains separately)
    try:
        success = hypertension_prediction_service.load_model()
        if success:
            logger.info("✓ Hypertension risk model loaded successfully")
        else:
            logger.warning("⚠ Hypertension model not found — run train_hypertension.py to train it")
    except Exception as e:
        logger.error(f"✗ Error loading hypertension model: {e}")

    yield  # Application runs here

    # === SHUTDOWN ===
    logger.info("Shutting down Preventive Health Assistant API...")


# ============== Create Application ==============

app = FastAPI(
    title="Preventive Health Assistant API",
    description="AI-powered health risk assessment with explainable AI",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",  # Swagger UI
    redoc_url="/redoc",  # ReDoc
)

# ============== Middleware ==============

# CORS - Allow frontend to call the API (origins defined in config/settings.py)
app.add_middleware(
    CORSMiddleware,
    allow_origins=API_CONFIG["cors_origins"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request logging
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all incoming requests."""
    logger.info(f"{request.method} {request.url.path}")
    response = await call_next(request)
    return response


# ============== Exception Handlers ==============

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handle unexpected exceptions gracefully."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": "internal_error",
            "message": "An unexpected error occurred."
        }
    )


# ============== Include Routers ==============

app.include_router(auth_router)
app.include_router(health_router)
app.include_router(cvd_router)
app.include_router(hypertension_router)
app.include_router(chatbot_router)
app.include_router(profile_router)
app.include_router(assessment_router)


# ============== Root Endpoint ==============

@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "name": "Preventive Health Assistant API",
        "version": "1.0.0",
        "documentation": "/docs",
        "endpoints": {
            "diabetes_assessment":       "/api/v1/health/diabetes/assess",
            "diabetes_quick_check":      "/api/v1/health/diabetes/quick-check",
            "cvd_assessment":            "/api/v1/health/cvd/assess",
            "cvd_quick_check":           "/api/v1/health/cvd/quick-check",
            "hypertension_assessment":   "/api/v1/health/hypertension/assess",
            "hypertension_quick_check":  "/api/v1/health/hypertension/quick-check",
            "chat":                      "/api/v1/chat",
        }
    }


@app.get("/health")
async def health_check():
    """Simple health check."""
    return {"status": "healthy", "model_loaded": prediction_service.is_ready()}


# ============== Run with Uvicorn ==============

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)