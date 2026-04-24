"""
Hypertension Prediction Service
================================
Service layer for loading the hypertension risk model and generating predictions.

Blood pressure readings are NOT accepted as features — the model is designed
for preventive screening where BP may not be known.
"""

import sys
import uuid
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT))

from src.ml.models.hypertension_model import HypertensionRiskModel
from src.ml.explainability import SHAPExplainer
from src.api.schemas.hypertension import HypertensionMetricsInput
from config import MODELS_DIR

logger = logging.getLogger(__name__)


class HypertensionPredictionService:
    """Service for loading and querying the hypertension risk model."""

    def __init__(self):
        self.model: Optional[HypertensionRiskModel] = None
        self.explainer: Optional[SHAPExplainer] = None
        self.model_path: Optional[Path] = None
        self.model_version: str = "unknown"
        self._ready: bool = False

    # ── Model loading ──────────────────────────────────────────────────────────

    def load_model(self, model_path: Optional[Path] = None) -> bool:
        """Load the latest hypertension model or a specified one."""
        try:
            if model_path is None:
                model_path = self._find_latest_model()

            if model_path is None:
                logger.warning(
                    "No hypertension model file found. Train first: "
                    "python src/ml/training/train_hypertension.py"
                )
                return False

            logger.info(f"Loading hypertension model from {model_path}")
            self.model = HypertensionRiskModel.load(model_path)
            self.model_path = model_path
            self.model_version = model_path.stem.replace("hypertension_model_", "")

            self.explainer = SHAPExplainer(
                self.model.model, feature_names=self.model.feature_names
            )
            self._initialize_explainer()
            self._ready = True

            logger.info(f"Hypertension model loaded (version={self.model_version})")
            return True

        except Exception as exc:
            logger.exception(f"Failed to load hypertension model: {exc}")
            self._ready = False
            return False

    def _find_latest_model(self) -> Optional[Path]:
        """Return the most recent hypertension model file."""
        for candidate_dir in [MODELS_DIR / "saved", MODELS_DIR]:
            if candidate_dir.exists():
                files = list(candidate_dir.glob("hypertension_model_*.joblib"))
                if files:
                    return max(files, key=lambda p: p.stat().st_mtime)
        return None

    def is_ready(self) -> bool:
        return self._ready and self.model is not None

    def _initialize_explainer(self) -> None:
        """Initialize SHAP explainer with synthetic background data."""
        if not self.model or not self.model.feature_names:
            return
        try:
            n = 100
            bg: Dict[str, np.ndarray] = {}
            for feat in self.model.feature_names:
                if feat == "age":
                    bg[feat] = np.random.uniform(25, 75, n)
                elif feat == "gender":
                    bg[feat] = np.random.choice([0.0, 1.0], n)
                elif feat == "bmi":
                    bg[feat] = np.random.uniform(18.5, 38, n)
                elif feat == "hba1c":
                    bg[feat] = np.random.uniform(4.5, 7.5, n)
                elif feat == "fasting_glucose":
                    bg[feat] = np.random.uniform(70, 150, n)
                elif feat == "total_cholesterol":
                    bg[feat] = np.random.uniform(150, 250, n)
                elif feat == "hdl_cholesterol":
                    bg[feat] = np.random.uniform(30, 80, n)
                elif feat == "systolic_bp":
                    # Mix of known (80%) and NaN (20%) to match training distribution
                    vals = np.random.uniform(100, 160, n)
                    vals[np.random.choice(n, n // 5, replace=False)] = np.nan
                    bg[feat] = vals
                elif feat == "diastolic_bp":
                    vals = np.random.uniform(60, 100, n)
                    vals[np.random.choice(n, n // 5, replace=False)] = np.nan
                    bg[feat] = vals
                elif feat == "diabetes_indicator":
                    bg[feat] = np.random.choice([0.0, 1.0], n, p=[0.85, 0.15])
                elif any(feat.startswith(p) for p in [
                    "race_ethnicity_", "smoking_status_", "activity_level_",
                    "bmi_category_", "age_group_",
                ]):
                    bg[feat] = np.random.choice([0.0, 1.0], n, p=[0.8, 0.2])
                else:
                    bg[feat] = np.random.uniform(0, 100, n)

            bg_df = pd.DataFrame(bg)[self.model.feature_names]
            self.explainer.initialize(bg_df)
            logger.info("Hypertension SHAP explainer initialized")
        except Exception as e:
            logger.warning(f"SHAP explainer init failed: {e}")

    # ── Helpers ────────────────────────────────────────────────────────────────

    @staticmethod
    def _get_float(d: Dict, key: str, default: float) -> float:
        v = d.get(key)
        return default if v is None else float(v)

    @staticmethod
    def _get_bool(d: Dict, key: str, default: bool = False) -> bool:
        v = d.get(key)
        return default if v is None else bool(v)

    @staticmethod
    def _get_bmi_category(bmi: float) -> str:
        if bmi < 18.5:   return "Underweight"
        if bmi < 25.0:   return "Normal"
        if bmi < 30.0:   return "Overweight"
        if bmi < 35.0:   return "Obese_I"
        if bmi < 40.0:   return "Obese_II"
        return "Obese_III"

    @staticmethod
    def _get_age_group(age: float) -> str:
        if age < 36:  return "18-35"
        if age < 46:  return "36-45"
        if age < 56:  return "46-55"
        if age < 66:  return "56-65"
        return "65+"

    # ── Feature preparation ────────────────────────────────────────────────────

    def prepare_features(
        self, metrics: Union[Dict[str, Any], "HypertensionMetricsInput"]
    ) -> pd.DataFrame:
        """
        Transform API input into the feature DataFrame expected by the hypertension model.

        Blood pressure columns are deliberately absent — they are not features,
        they are only used to define the training target.
        """
        if hasattr(metrics, "model_dump"):
            metrics = metrics.model_dump()

        age = float(metrics["age"])
        gender = 0.0 if str(metrics["gender"]).lower() == "male" else 1.0

        bmi = metrics.get("bmi")
        if bmi is None:
            w, h = metrics.get("weight"), metrics.get("height")
            bmi = (w / ((h / 100) ** 2)) if (w and h) else 25.0
        bmi = float(bmi)

        waist     = self._get_float(metrics, "waist_circumference", 90.0)
        hba1c     = self._get_float(metrics, "hba1c",             5.5)
        glucose   = self._get_float(metrics, "fasting_glucose",   90.0)
        total_chol= self._get_float(metrics, "total_cholesterol", 200.0)
        hdl_chol  = self._get_float(metrics, "hdl_cholesterol",    50.0)
        education = self._get_float(metrics, "education",          3.0)
        income    = self._get_float(metrics, "income_ratio",       2.0)
        sedentary = self._get_float(metrics, "sedentary_minutes",480.0)

        # Diabetes indicator
        known_diab = self._get_bool(metrics, "diabetes", False)
        diabetes_indicator = 1.0 if (
            known_diab or hba1c >= 6.5 or glucose >= 126
        ) else 0.0

        # Smoking
        smoking = str(metrics.get("smoking_status") or "never").lower()
        smoked_100    = 1.0 if smoking in ("former", "current") else 0.0
        current_smoke = 1.0 if smoking == "current" else 0.0

        features: Dict[str, float] = {
            "age": age,
            "gender": gender,
            "education": education,
            "income_ratio": income,
            "bmi": bmi,
            "waist_circumference": waist,
            "hba1c": hba1c,
            "fasting_glucose": glucose,
            "total_cholesterol": total_chol,
            "hdl_cholesterol": hdl_chol,
            "diabetes_indicator": diabetes_indicator,
            "smoked_100": smoked_100,
            "current_smoker": current_smoke,
            "vigorous_work": 0.0,
            "moderate_work": 0.0,
            "vigorous_rec": 0.0,
            "moderate_rec": 0.0,
            "sedentary_minutes": sedentary,
            # BP is handled as a clinical override in predict(), not as a model feature,
            # to avoid circularity (target is defined from the same BP readings).
        }

        # One-hot: race_ethnicity
        for cat in ["2.0", "3.0", "4.0", "6.0", "7.0"]:
            features[f"race_ethnicity_{cat}"] = 0.0

        # One-hot: smoking_status (drop_first → 'Current' is reference)
        features["smoking_status_Former"] = 1.0 if smoking == "former" else 0.0
        features["smoking_status_Never"]  = 1.0 if smoking == "never"  else 0.0

        # One-hot: activity_level (drop_first → 'High' is reference)
        features["activity_level_Low"]       = 0.0
        features["activity_level_Moderate"]  = 0.0
        features["activity_level_Sedentary"] = 1.0

        # One-hot: bmi_category (drop_first → 'Normal' is reference)
        bmi_cat = self._get_bmi_category(bmi)
        features["bmi_category_Obese_I"]     = 1.0 if bmi_cat == "Obese_I"    else 0.0
        features["bmi_category_Obese_II"]    = 1.0 if bmi_cat == "Obese_II"   else 0.0
        features["bmi_category_Obese_III"]   = 1.0 if bmi_cat == "Obese_III"  else 0.0
        features["bmi_category_Overweight"]  = 1.0 if bmi_cat == "Overweight" else 0.0
        features["bmi_category_Underweight"] = 1.0 if bmi_cat == "Underweight"else 0.0

        # One-hot: age_group (drop_first → '18-35' is reference)
        age_grp = self._get_age_group(age)
        features["age_group_36-45"] = 1.0 if age_grp == "36-45" else 0.0
        features["age_group_46-55"] = 1.0 if age_grp == "46-55" else 0.0
        features["age_group_56-65"] = 1.0 if age_grp == "56-65" else 0.0
        features["age_group_65+"]   = 1.0 if age_grp == "65+"   else 0.0

        df = pd.DataFrame([features])

        if self.model and self.model.feature_names:
            for col in self.model.feature_names:
                if col not in df.columns:
                    df[col] = 0.0
            df = df[self.model.feature_names]

        return df

    # ── Prediction ─────────────────────────────────────────────────────────────

    def predict(
        self,
        metrics: Union[Dict[str, Any], "HypertensionMetricsInput"],
        include_explanation: bool = True,
    ) -> Dict[str, Any]:
        """Generate a hypertension risk prediction."""
        if not self.is_ready():
            raise RuntimeError("Hypertension model not loaded.")

        if hasattr(metrics, "model_dump"):
            metrics = metrics.model_dump()

        features_df = self.prepare_features(metrics)

        proba = self.model.predict_proba(features_df)[0]
        risk_probability = float(proba[1])
        prediction = int(self.model.predict(features_df)[0])
        confidence = float(max(proba))

        # Clinical BP override — applied on top of the lifestyle model score.
        # The model is trained without BP to avoid circularity (target = BP threshold),
        # so when the user provides a known reading we apply direct clinical thresholds
        # (AHA 2017: Stage 2 ≥ 140/90, Stage 1 ≥ 130/80).
        systolic_bp  = metrics.get("systolic_bp")
        diastolic_bp = metrics.get("diastolic_bp")
        bp_note: Optional[str] = None
        if systolic_bp is not None or diastolic_bp is not None:
            sbp = float(systolic_bp or 0)
            dbp = float(diastolic_bp or 0)
            if sbp >= 140 or dbp >= 90:
                risk_probability = max(risk_probability, 0.88)
                prediction = 1
                bp_note = f"Stage 2 hypertension confirmed (BP {sbp:.0f}/{dbp:.0f} mmHg)"
            elif sbp >= 130 or dbp >= 80:
                risk_probability = max(risk_probability, 0.55)
                prediction = 1 if risk_probability >= 0.5 else prediction
                bp_note = f"Stage 1 / elevated BP ({sbp:.0f}/{dbp:.0f} mmHg)"
            else:
                bp_note = f"BP within normal range ({sbp:.0f}/{dbp:.0f} mmHg)"

        if risk_probability < 0.15:      category = "Low"
        elif risk_probability < 0.30:    category = "Moderate"
        elif risk_probability < 0.50:    category = "High"
        else:                            category = "Very High"

        result = {
            "assessment_id": (
                f"htn_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
            ),
            "timestamp": datetime.utcnow().isoformat(),
            "risk": {
                "risk_probability": round(risk_probability, 4),
                "risk_percentage":  round(risk_probability * 100, 1),
                "risk_category":    category,
                "prediction":       prediction,
                "confidence":       round(confidence, 4),
                **({"bp_note": bp_note} if bp_note else {}),
            },
            "model_version": self.model_version,
        }

        if include_explanation and self.explainer:
            result["explanation"] = self.explainer.explain_prediction(
                features_df, self.model.feature_names
            )

        return result

    # ── Recommendations ────────────────────────────────────────────────────────

    def generate_recommendations(
        self, metrics: Dict[str, Any], result: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Generate hypertension-specific health recommendations."""
        recs = []
        risk_cat = result.get("risk", {}).get("risk_category", "Low")

        bmi = metrics.get("bmi")
        if bmi is None:
            w, h = metrics.get("weight"), metrics.get("height")
            if w and h:
                bmi = w / ((h / 100) ** 2)

        smoking   = str(metrics.get("smoking_status") or "never").lower()
        sedentary = metrics.get("sedentary_minutes")
        hba1c     = metrics.get("hba1c")

        # Weight — strongest modifiable hypertension risk factor
        if bmi and bmi >= 25:
            recs.append({
                "category": "weight",
                "priority": "high" if bmi >= 30 else "medium",
                "recommendation": "Reduce weight through a calorie-controlled diet and regular exercise",
                "rationale": (
                    f"BMI of {bmi:.1f}. Losing even 5 kg can reduce systolic BP by 3-5 mmHg."
                ),
                "source": "DASH Diet / JNC 8 Guidelines",
            })

        # DASH diet — always relevant for hypertension prevention
        if risk_cat in ("Moderate", "High", "Very High"):
            recs.append({
                "category": "diet",
                "priority": "medium",
                "recommendation": (
                    "Follow the DASH diet: increase fruits, vegetables, low-fat dairy; "
                    "limit sodium to <2.3 g/day"
                ),
                "rationale": "The DASH diet reduces systolic BP by 8-14 mmHg on average.",
                "source": "NHLBI DASH Diet Evidence",
            })

        # Physical activity
        if sedentary and sedentary > 480:
            recs.append({
                "category": "exercise",
                "priority": "medium",
                "recommendation": "Reduce sedentary time; aim for ≥30 min brisk walking 5 days/week",
                "rationale": "Regular aerobic exercise reduces systolic BP by 4-9 mmHg.",
                "source": "AHA Physical Activity Guidelines",
            })
        elif risk_cat in ("Moderate", "High", "Very High"):
            recs.append({
                "category": "exercise",
                "priority": "medium",
                "recommendation": "Aim for ≥150 minutes of moderate aerobic activity per week",
                "rationale": "Regular physical activity lowers blood pressure and reduces CVD risk.",
                "source": "AHA Physical Activity Guidelines",
            })

        # Smoking
        if smoking == "current":
            recs.append({
                "category": "smoking",
                "priority": "high",
                "recommendation": "Quit smoking — each cigarette causes a temporary BP spike",
                "rationale": "Smoking damages blood vessel walls and accelerates hypertension progression.",
                "source": "WHO",
            })

        # Diabetes control
        if hba1c and hba1c >= 5.7:
            recs.append({
                "category": "blood_sugar",
                "priority": "high" if hba1c >= 6.5 else "medium",
                "recommendation": "Manage blood glucose levels — diabetes significantly raises hypertension risk",
                "rationale": (
                    f"HbA1c of {hba1c:.1f}% indicates {'diabetes' if hba1c >= 6.5 else 'prediabetes'}, "
                    "which doubles hypertension risk."
                ),
                "source": "ADA / AHA Joint Guidelines",
            })

        # Sodium reduction (always relevant for HTN)
        recs.append({
            "category": "diet",
            "priority": "low",
            "recommendation": "Limit added salt and processed food; aim for <2,300 mg sodium/day",
            "rationale": "Reducing sodium intake by 1 g/day lowers systolic BP by ~2 mmHg.",
            "source": "WHO",
        })

        # Medical screening
        if risk_cat in ("High", "Very High"):
            recs.append({
                "category": "medical",
                "priority": "high",
                "recommendation": "Get your blood pressure measured by a healthcare provider",
                "rationale": (
                    f"Your {risk_cat.lower()} hypertension risk suggests BP monitoring is important. "
                    "Early detection enables effective management."
                ),
                "source": "NICE Guidelines / JNC 8",
            })

        # ── Baseline wellness recommendations (all risk levels) ──────────────
        if not any(r["category"] == "activity" for r in recs):
            recs.append({
                "category": "activity",
                "priority": "low",
                "recommendation": "Stay physically active — 150 min/week of moderate exercise lowers blood pressure by 5-8 mmHg",
                "rationale": "Regular aerobic activity is one of the most effective non-drug BP-lowering strategies.",
                "source": "AHA / ESC Guidelines",
            })

        if not any(r["category"] == "stress" for r in recs):
            recs.append({
                "category": "stress",
                "priority": "low",
                "recommendation": "Practice stress management — chronic stress can raise blood pressure over time",
                "rationale": "Relaxation techniques (deep breathing, meditation, yoga) can reduce systolic BP by 3-5 mmHg.",
                "source": "AHA",
            })

        if not any(r["category"] == "medical" for r in recs):
            recs.append({
                "category": "medical",
                "priority": "low",
                "recommendation": "Check your blood pressure at least once a year — home monitors are inexpensive and accurate",
                "rationale": "Hypertension is often symptom-free; regular checks are the only way to catch it early.",
                "source": "NICE Guidelines",
            })

        return recs

    # ── Model info ─────────────────────────────────────────────────────────────

    def get_model_info(self) -> Dict[str, Any]:
        if not self.is_ready():
            return {"error": "Hypertension model not loaded"}

        meta = getattr(self.model, "metadata", {}) or {}
        trained_at = meta.get("trained_at", self.model_version)
        perf = meta.get("metrics", {})
        performance_metrics = {
            "accuracy":  perf.get("accuracy",  0.0),
            "roc_auc":   perf.get("roc_auc",   0.0),
            "precision": perf.get("precision", 0.0),
            "recall":    perf.get("recall",    0.0),
            "f1_score":  perf.get("f1_score",  0.0),
        }

        return {
            "model_name": "Hypertension Risk Prediction Model",
            "version": self.model_version,
            "trained_at": trained_at,
            "n_features": len(self.model.feature_names),
            "feature_names": self.model.feature_names,
            "performance_metrics": performance_metrics,
        }


# Singleton instance
hypertension_prediction_service = HypertensionPredictionService()
