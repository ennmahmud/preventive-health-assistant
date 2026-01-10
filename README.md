# AI-Powered Preventive Health Chat Assistant

An intelligent health risk assessment system combining machine learning prediction with conversational AI to provide personalized preventive health guidance.

## 🎯 Project Overview

This dissertation project addresses preventable deaths from non-communicable diseases (NCDs) by integrating:
- **Machine Learning Risk Prediction** using XGBoost models trained on NHANES data
- **Explainable AI** with SHAP for transparent risk factor explanations
- **Conversational Interface** for accessible, personalized health guidance
- **Evidence-Based Recommendations** aligned with WHO/CDC guidelines

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Frontend (React)                         │
│              Conversational Chat Interface                  │
└─────────────────────┬───────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────┐
│                   Backend (FastAPI)                         │
│         API Routes │ Services │ Authentication              │
└─────────────────────┬───────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────┐
│                    ML Engine                                │
│   XGBoost Models │ SHAP Explainer │ Risk Assessment         │
└─────────────────────────────────────────────────────────────┘
```

## 📁 Project Structure

```
preventive-health-assistant/
├── src/
│   ├── ml/                    # Machine Learning module
│   │   ├── data/              # Data loading and preprocessing
│   │   ├── models/            # Model definitions
│   │   ├── training/          # Training pipelines
│   │   ├── evaluation/        # Model evaluation metrics
│   │   ├── explainability/    # SHAP integration
│   │   └── utils/             # ML utilities
│   ├── api/                   # FastAPI backend
│   │   ├── routes/            # API endpoints
│   │   ├── services/          # Business logic
│   │   ├── schemas/           # Pydantic models
│   │   └── middleware/        # Auth, logging, etc.
│   ├── chatbot/               # Conversational AI
│   │   ├── intents/           # Intent recognition
│   │   ├── responses/         # Response generation
│   │   └── handlers/          # Conversation handlers
│   └── frontend/              # React application
│       ├── components/        # UI components
│       ├── pages/             # Page components
│       ├── hooks/             # Custom React hooks
│       └── utils/             # Frontend utilities
├── data/
│   ├── raw/                   # Original NHANES datasets
│   ├── processed/             # Cleaned, transformed data
│   └── external/              # External reference data
├── models/
│   └── saved/                 # Serialized trained models
├── notebooks/                 # Jupyter notebooks for exploration
├── tests/
│   ├── unit/                  # Unit tests
│   ├── integration/           # Integration tests
│   └── ml/                    # ML model tests
├── docs/                      # Documentation
├── config/                    # Configuration files
└── scripts/                   # Utility scripts
```

## 🚀 Getting Started

### Prerequisites

- Python 3.10+
- Node.js 18+
- pip or conda

### Installation

1. Clone the repository:
```bash
git clone https://github.com/YOUR_USERNAME/preventive-health-assistant.git
cd preventive-health-assistant
```

2. Create and activate virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Download NHANES data:
```bash
python scripts/download_nhanes.py
```

## 🔬 ML Models

### Supported Health Conditions

| Condition | Status | Target Accuracy |
|-----------|--------|-----------------|
| Diabetes | 🚧 In Progress | ≥80% |
| Cardiovascular Disease | 📋 Planned | ≥80% |
| Hypertension | 📋 Planned | ≥80% |

### Data Source

Models are trained on [NHANES (National Health and Nutrition Examination Survey)](https://www.cdc.gov/nchs/nhanes/index.htm) data from the CDC.

## 📊 Validation Framework

- **Data Quality**: Missing value analysis, outlier detection, distribution checks
- **Model Performance**: Accuracy, AUC-ROC, Precision, Recall, F1-Score
- **Calibration**: Reliability diagrams, Brier score
- **Explainability**: SHAP values, feature importance

## 🛡️ Ethical Considerations

- No diagnostic claims - risk assessment only
- Clear communication of limitations
- Privacy-preserving design
- Evidence-based recommendations only

## 📚 References

- WHO Guidelines on NCDs
- CDC NHANES Documentation
- ADA Diabetes Risk Factors

## 👤 Author

**Abubakar** - BSc Computer Science, University of Wolverhampton

Supervisor: Salman Arif

## 📄 License

This project is part of an academic dissertation and is subject to university guidelines.
