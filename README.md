# Preventive Health Assistant

An AI-powered health risk assessment platform combining XGBoost machine learning, explainable AI (SHAP), and a Claude-backed conversational interface to help users understand and reduce their risk of diabetes, cardiovascular disease, and hypertension.

---

## Features

| Feature | Description |
|---------|-------------|
| **Risk assessment wizard** | Step-by-step questionnaire for diabetes, CVD, and hypertension; no lab values required |
| **ML risk scores** | XGBoost models trained on NHANES 2015–2018 data; probability + risk category (Low / Moderate / High / Very High) |
| **SHAP explanations** | Per-prediction feature contributions shown as a ranked bar chart |
| **Cohort comparison** | "You are 4.3× higher risk than the average 56–65-year-old male" — population context from NHANES prevalence data |
| **What-If simulator** | Drag lifestyle sliders to see how risk changes with behaviour modification |
| **Trend dashboard** | SVG sparklines tracking risk trajectory across previous assessments |
| **Conversational chat** | Multi-turn chatbot with Claude LLM integration; falls back to templates without an API key |
| **User accounts** | JWT auth, persistent profiles (SQLite), assessment history |
| **Personalised recommendations** | Evidence-based lifestyle recommendations ranked by modifiability |

---

## Quick start (Docker)

### Prerequisites
- Docker ≥ 24 and Docker Compose V2
- Trained model files in `models/saved/` (see [Training](#training))
- A `.env` file (see [Configuration](#configuration))

```bash
# 1 — Clone and configure
git clone https://github.com/ennmahmud/preventive-health-assistant.git
cd preventive-health-assistant
cp .env.example .env
# Edit .env — set API_KEY, ELAN_SECRET_KEY, and optionally ANTHROPIC_API_KEY

# 2 — Train models (one-time, ~5 min each)
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python src/ml/training/train_diabetes.py
python src/ml/training/train_cvd.py
python src/ml/training/train_hypertension.py

# 3 — Launch
docker compose up --build
```

| Service | URL |
|---------|-----|
| Frontend | http://localhost:3000 |
| Backend API | http://localhost:8000 |
| API docs (Swagger) | http://localhost:8000/docs |

---

## Quick start (local dev)

```bash
# Backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
venv/bin/python -m uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000

# Frontend (separate terminal)
cd frontend
npm install
npm run dev       # http://localhost:5173 — proxies /api → :8000
```

```bash
# Tests
venv/bin/pytest tests/ -q    # 199 tests, ~8 s
```

---

## Configuration

Copy `.env.example` to `.env`:

```env
# Required — protects all /api/v1/ endpoints
API_KEY=your-secret-key

# Required — signs user session JWTs (must be ≥ 32 chars)
ELAN_SECRET_KEY=your-jwt-secret-32-chars-minimum

# Optional — enables Claude LLM explanations and smart chat responses
# Without this, the app uses template-based responses (fully functional)
ANTHROPIC_API_KEY=sk-ant-api03-...
```

---

## Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                   Frontend  (React 19 + Vite)                    │
│  Dashboard · Assessment Wizard · Chat · Progress · Profile       │
│  FloatingNav · RiskRing · ShapBar · CohortComparison · WhatIf    │
└────────────────────────────┬─────────────────────────────────────┘
                             │  /api/  (nginx proxy in prod)
                             │  Vite proxy in dev
┌────────────────────────────▼─────────────────────────────────────┐
│                    Backend  (FastAPI + uvicorn)                   │
│                                                                  │
│  /auth         JWT register / login / profile / change-password  │
│  /assessment   Lifestyle wizard endpoint + cohort comparison     │
│  /health       Diabetes / CVD / HTN direct-metric endpoints      │
│  /chat         Multi-turn conversational interface               │
│  /profile      User health profile CRUD                          │
│                                                                  │
│  Auth: Bearer token (API_KEY) + Élan JWT                         │
└─────────┬───────────────────────────┬────────────────────────────┘
          │                           │
┌─────────▼──────────┐   ┌────────────▼───────────────────────────┐
│   ML Engine        │   │   Chatbot Layer                        │
│                    │   │                                        │
│  XGBoostClassifier │   │  Intent classifier (regex)             │
│  SHAP TreeExplainer│   │  Entity extractor (14 health fields)   │
│  Feature pipelines │   │  Session store (in-memory, 30-min TTL) │
│  Threshold tuning  │   │  Claude LLM (with template fallback)   │
└────────────────────┘   └────────────────────────────────────────┘
          │
┌─────────▼──────────┐
│   Persistence      │
│                    │
│  data/users.db     │  SQLite — user accounts
│  data/profiles/    │  JSON — assessment history per user
│  models/saved/     │  joblib — trained XGBoost models
└────────────────────┘
```

---

## ML Models

### Data source

NHANES (National Health and Nutrition Examination Survey) — CDC. Cycles 2015–2016 and 2017–2018, ~19,000 participants combined.

### Performance

| Model | AUC-ROC | Recall | Precision | Threshold | Notes |
|-------|---------|--------|-----------|-----------|-------|
| **Diabetes** | **0.967** | 72.7% | 99.7% | 0.50 | Standard F1 threshold |
| **CVD** | **0.847** | **83.4%** | 28.4% | 0.30 | F₂-optimised (recall-weighted) |
| **Hypertension** | 0.769 | **93.4%** | 32.9% | 0.30 | F₂-optimised; BP excluded from features |

CVD and HTN use **F-beta (β=2) threshold optimisation** on the held-out test set — the same strategy used in cardiovascular screening tools where a false negative (missed case) is far more costly than a false positive.

### Training

```bash
# Each script downloads NHANES data on first run (skip with --skip-download)
python src/ml/training/train_diabetes.py
python src/ml/training/train_cvd.py       [--skip-download]
python src/ml/training/train_hypertension.py [--skip-download]
```

### Design notes

- **Hypertension** — blood pressure readings are **intentionally excluded** as features. The model predicts future hypertension risk from lifestyle/demographic factors so users without a BP cuff can be screened. BP is only used to define the training target.
- **CVD** — includes systolic/diastolic BP as optional features; they are validated Framingham Risk Score inputs and do not cause circularity (target is doctor-diagnosed CVD events, not BP).
- **Class imbalance** — CVD and HTN use `scale_pos_weight = n_neg / n_pos` (auto-computed at fit time) + `eval_metric = aucpr` (PR-AUC, more sensitive to minority class than ROC-AUC).

---

## API Reference

All endpoints require `Authorization: Bearer <API_KEY>` (or a valid user JWT).

### Auth
| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/auth/register` | Create account → returns JWT |
| POST | `/api/v1/auth/login` | Sign in → returns JWT |
| GET | `/api/v1/auth/me` | Current user info |
| PUT | `/api/v1/auth/profile` | Update name, DOB, gender, height, weight |
| PUT | `/api/v1/auth/change-password` | Change password |
| DELETE | `/api/v1/auth/account` | Delete account |

### Assessment
| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/assessment` | Lifestyle-based risk assessment (wizard payload) |
| GET | `/api/v1/assessment/cohort` | Population comparison for user's age/gender cohort |
| POST | `/api/v1/assessment/simulate` | What-if: delta risk for lifestyle change |
| GET | `/api/v1/assessment/questions/{condition}` | Question bank for wizard |

### Direct metric endpoints
| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/health/diabetes/assess` | Full diabetes assessment (lab values) |
| POST | `/api/v1/health/cvd/assess` | Full CVD assessment |
| POST | `/api/v1/health/hypertension/assess` | Full HTN assessment |

### Chat & Profile
| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/chat` | Multi-turn conversational interface |
| GET/POST/DELETE | `/api/v1/profile/{user_id}` | User health profile CRUD |
| GET | `/api/v1/profile/{user_id}/history` | Assessment history |

Full interactive docs: **http://localhost:8000/docs**

---

## Project structure

```
preventive-health-assistant/
├── src/
│   ├── api/
│   │   ├── db/              # SQLite user store (users_db.py)
│   │   ├── routes/          # auth, assessment, health, cvd, hypertension, chatbot, profile
│   │   ├── schemas/         # Pydantic request/response models
│   │   └── services/        # Singleton model loaders (diabetes, CVD, HTN)
│   ├── chatbot/
│   │   ├── intents/         # Rule-based classifier + regex entity extractor (14 fields)
│   │   ├── handlers/        # Session store (30-min TTL) + conversation manager
│   │   ├── llm/             # Claude service with graceful fallback
│   │   └── questions/       # Question bank + wizard flow
│   ├── lifestyle/           # Lifestyle → model feature mapper
│   ├── profile/             # User profile service (JSON persistence)
│   └── ml/
│       ├── data/            # NHANES preprocessors
│       ├── models/          # XGBoost wrappers (diabetes, CVD, HTN)
│       ├── training/        # 6-step training pipelines
│       └── explainability/  # SHAP TreeExplainer wrapper
├── frontend/                # Vite + React 19
│   └── src/
│       ├── pages/           # Dashboard, Assess, Chat, Progress, Profile, Settings, Auth
│       ├── components/      # RiskRing, ShapBar, CohortComparison, WhatIfSimulator, TrendDashboard
│       ├── contexts/        # AuthContext (JWT-backed)
│       ├── hooks/           # useChat, useAssessment
│       └── api/             # Axios client (auto-attaches Bearer token)
├── data/
│   ├── cohort_averages.json # Pre-computed NHANES population prevalence (age × gender × condition)
│   └── profiles/            # Per-user assessment history (JSON, gitignored)
├── models/saved/            # Trained .joblib models (gitignored — train locally)
├── notebooks/               # Jupyter notebooks 01–05 (EDA → SHAP analysis)
├── tests/                   # 199 tests (unit + integration + ML)
├── config/settings.py       # Model hyperparameters, feature lists, API config
├── Dockerfile               # Backend production image (python:3.13-slim)
├── frontend/Dockerfile      # Frontend multi-stage image (node:20 build → nginx:1.27 serve)
├── docker-compose.yml       # Orchestration (prod + dev profiles)
├── requirements.txt         # Full deps (includes training + dev tools)
└── requirements.prod.txt    # Slim runtime deps only (used in Docker image)
```

---

## Ethical considerations

- **Screening tool only** — all responses carry explicit "not a substitute for medical advice" disclaimers
- **Transparent uncertainty** — every risk score shows confidence and the key factors driving it
- **Evidence-based** — recommendations aligned with WHO, CDC, ADA, and AHA guidelines
- **GDPR-aware** — `DELETE /api/v1/auth/account` permanently removes all user data; `DELETE /api/v1/profile/{user_id}` clears health history independently

---

## Author

**Abubakar** — BSc Computer Science, University of Wolverhampton  
Supervisor: Salman Arif
