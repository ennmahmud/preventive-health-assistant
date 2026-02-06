"""
Preventive Health Assistant API
===============================
FastAPI application entry point.
"""

import sys
from pathlib import Path
from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.api.routes.health import router as health_router
from src.api.services.prediction_service import prediction_service

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

    # Load the diabetes risk model
    try:
        success = prediction_service.load_model()
        if success:
            logger.info("✓ Diabetes risk model loaded successfully")
        else:
            logger.warning("⚠ Failed to load diabetes risk model")
    except Exception as e:
        logger.error(f"✗ Error loading model: {e}")

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

# CORS - Allow frontend to call the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # React dev server
        "http://localhost:5173",  # Vite dev server
    ],
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

app.include_router(health_router)


# ============== Root Endpoint ==============

@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "name": "Preventive Health Assistant API",
        "version": "1.0.0",
        "documentation": "/docs",
        "endpoints": {
            "diabetes_assessment": "/api/v1/health/diabetes/assess",
            "quick_check": "/api/v1/health/diabetes/quick-check",
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