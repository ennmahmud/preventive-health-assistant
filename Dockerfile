# ── Backend Dockerfile ────────────────────────────────────────────────────────
# Python 3.13 slim — production API only (no training tools, notebooks, or dev deps)

FROM python:3.13-slim AS base

# System deps needed by some Python packages (numpy, pandas, shap, xgboost)
RUN apt-get update && apt-get install -y --no-install-recommends \
        gcc \
        g++ \
        libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# ── Dependency layer (cached unless requirements change) ──────────────────────
COPY requirements.prod.txt .
RUN pip install --no-cache-dir -r requirements.prod.txt

# ── Application code ──────────────────────────────────────────────────────────
COPY config/   config/
COPY src/      src/
COPY data/cohort_averages.json data/cohort_averages.json

# Runtime directories (populated by volumes or init_db at startup)
RUN mkdir -p data/profiles data/processed models/saved

# Non-root user for security
RUN useradd --no-create-home --shell /bin/false appuser \
    && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

CMD ["uvicorn", "src.api.main:app", \
     "--host", "0.0.0.0", \
     "--port", "8000", \
     "--workers", "2"]
