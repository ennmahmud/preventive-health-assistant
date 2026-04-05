# AI-Powered Preventive Health Chat Assistant

An intelligent health risk assessment system combining machine learning prediction with conversational AI to provide personalized preventive health guidance.

## Project Overview

This dissertation project addresses preventable deaths from non-communicable diseases (NCDs) by integrating:

- **Machine Learning Risk Prediction** — XGBoost models trained on NHANES (2015–2018) data
- **Explainable AI** — SHAP TreeExplainer for transparent, per-prediction risk factor explanations
- **Conversational Interface** — Multi-turn chatbot that collects health metrics and delivers results in plain language
- **Evidence-Based Recommendations** — Guidelines aligned with WHO/CDC/ADA standards

## Architecture

```
┌─────────────────────────────────────────────┐
│           Frontend (React + Vite)           │
│   Chat UI · Risk cards · SHAP bar charts    │
└──────────────────┬──────────────────────────┘
                   │  /api  (proxy → :8000)
┌──────────────────▼──────────────────────────┐
│             Backend (FastAPI)               │
│  /health/diabetes  /health/cvd  /health/    │
│  hypertension  /chat  — Pydantic schemas    │
└──────────────────┬──────────────────────────┘
                   │
┌──────────────────▼──────────────────────────┐
│              ML Engine                      │
│  XGBoost · SHAP · Scikit-learn pipelines   │
└─────────────────────────────────────────────┘
```

## Project Structure

```
preventive-health-assistant/
├── src/
│   ├── api/
│   │   ├── routes/          # diabetes, cvd, hypertension, chatbot
│   │   ├── schemas/         # Pydantic request/response models
│   │   └── services/        # Singleton model services
│   ├── chatbot/
│   │   ├── intents/         # Rule-based classifier + regex entity extractor
│   │   ├── handlers/        # Session store (in-memory, 30-min TTL) + conversation manager
│   │   └── responses/       # Conversational response templates
│   └── ml/
│       ├── data/            # NHANES preprocessors (diabetes, CVD, hypertension)
│       ├── models/          # XGBoost model wrappers
│       ├── training/        # 6-step training pipelines
│       └── explainability/  # SHAP integration
├── frontend/                # Vite + React app (port 5173)
├── notebooks/               # Jupyter notebooks 01–05 (EDA → SHAP analysis)
├── data/
│   ├── raw/                 # Downloaded NHANES .XPT files (2015–2018)
│   └── processed/           # Cleaned, feature-engineered datasets
├── models/saved/            # Serialised .joblib models + evaluation JSON
├── tests/
│   ├── unit/                # Chatbot modules, prediction service, schemas
│   ├── integration/         # API endpoints (diabetes, CVD, HTN, chatbot)
│   └── ml/                  # Model loading and inference
└── config/                  # settings.py — API config, CORS origins, thresholds
```

## Getting Started

### Prerequisites

- Python 3.10+
- Node.js 18+

### Backend setup

```bash
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### Train models

```bash
# Diabetes (NHANES data auto-downloaded on first run)
python src/ml/training/train_diabetes.py

# Cardiovascular disease
python src/ml/training/train_cvd.py

# Hypertension
python src/ml/training/train_hypertension.py
```

### Run the API

```bash
venv/bin/python -m uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
```

Interactive docs: http://localhost:8000/docs

### Run the frontend

```bash
cd frontend
npm install
npm run dev          # http://localhost:5173  (proxies /api → :8000)
```

### Run tests

```bash
venv/bin/pytest tests/ -q
```

## API Reference

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/health/diabetes/assess` | Full diabetes risk assessment |
| POST | `/api/v1/health/diabetes/quick-check` | Diabetes quick check (age + BMI) |
| POST | `/api/v1/health/cvd/assess` | Full CVD risk assessment |
| POST | `/api/v1/health/cvd/quick-check` | CVD quick check |
| POST | `/api/v1/health/hypertension/assess` | Full hypertension risk assessment |
| POST | `/api/v1/health/hypertension/quick-check` | Hypertension quick check |
| POST | `/api/v1/chat` | Multi-turn chatbot (session-aware) |
| GET  | `/api/v1/chat/session/{id}` | Inspect session state |
| DELETE | `/api/v1/chat/session/{id}` | Clear session |

All assessment responses include `risk_probability`, `risk_category`, optional SHAP `explanation`, and prioritised `recommendations`.

## ML Models

### Data source

NHANES (National Health and Nutrition Examination Survey) — CDC, cycles 2015–2016 and 2017–2018. Data is downloaded automatically by the training scripts using the NHANES Python package.

### Model performance

| Condition | Accuracy | AUC-ROC | Precision | Recall | F1 |
|-----------|----------|---------|-----------|--------|----|
| Diabetes | **94.85%** | **0.967** | 99.7% | 72.7% | 84.1% |
| Hypertension | 77.9% | 0.770 | 50.0% | 8.8% | 15.0% |
| CVD | 89.2% | 0.848 | 91.3% | 86.7% | 88.9% |

### Risk thresholds

| Condition | Low | Moderate | High | Reference |
|-----------|-----|----------|------|-----------|
| Diabetes | < 20% | 20–50% | > 50% | ADA risk guidelines |
| CVD | < 10% | 10–20% | > 20% | Framingham Risk Score |
| Hypertension | < 15% | 15–35% | > 35% | JNC 8 / AHA 2017 |

### Design notes

- **Hypertension model** is a *preventive* model — blood pressure readings are intentionally excluded as features. The model predicts future hypertension risk from lifestyle/demographic factors so users without a BP reading can be screened.
- **CVD model** includes BP (systolic/diastolic) as optional features; BP is a validated Framingham risk factor and does not cause circularity since the target is doctor-diagnosed CVD, not BP itself.
- All models return `503` at inference time if not yet trained, with a message directing to the relevant training script.

## Chatbot

The conversational interface is a rule-based multi-turn system (no LLM dependency):

- **Intent classification** — regex patterns distinguish `assess_diabetes`, `assess_cvd`, `assess_hypertension`, `ask_about_result`, `ask_for_recommendation`, and small-talk intents
- **Entity extraction** — regex extraction of 14 health fields from natural language (age, BMI, cholesterol, HbA1c, BP, smoking status, etc.)
- **Session management** — in-memory store with 30-minute TTL and probabilistic cleanup; no external dependency
- **Conversation flow** — collects required fields across turns, calls the prediction service, then returns an inline risk result

## Ethical Considerations

- Risk assessment only — no diagnostic claims
- Clear uncertainty communication on every response
- No personally identifiable data stored (sessions are ephemeral, in-memory only)
- Evidence-based recommendations aligned with WHO/CDC/ADA guidelines

## Author

**Abubakar** — BSc Computer Science, University of Wolverhampton

Supervisor: Salman Arif

## License

This project is part of an academic dissertation and is subject to university guidelines.
