"""
CVD Prediction Service
======================
Service layer for loading the CVD risk model and generating predictions.
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

from src.ml.models.cvd_model import CVDRiskModel
from src.ml.explainability import SHAPExplainer
from src.api.schemas.cvd import CVDMetricsInput
from config import MODELS_DIR

logger = logging.getLogger(__name__)


class CVDPredictionService:
    """Service for loading and querying the CVD risk model."""

    def __init__(self):
        self.model: Optional[CVDRiskModel] = None
        self.explainer: Optional[SHAPExplainer] = None
        self.model_path: Optional[Path] = None
        self.model_version: str = "unknown"
        self._ready: bool = False

    # ── Model loading ──────────────────────────────────────────────────────────

    def load_model(self, model_path: Optional[Path] = None) -> bool:
        """Load the latest CVD model or a specified one."""
        try:
            if model_path is None:
                model_path = self._find_latest_model()

            if model_path is None:
                logger.warning("No CVD model file found. Train the model first: "
                               "python src/ml/training/train_cvd.py")
                return False

            logger.info(f"Loading CVD model from {model_path}")
            self.model = CVDRiskModel.load(model_path)
            self.model_path = model_path
            self.model_version = model_path.stem.replace("cvd_model_", "")

            self.explainer = SHAPExplainer(
                self.model.model, feature_names=self.model.feature_names
            )
            self._initialize_explainer()
            self._ready = True

            logger.info(f"CVD model loaded (version={self.model_version})")
            return True

        except Exception as exc:
            logger.exception(f"Failed to load CVD model: {exc}")
            self._ready = False
            return False

    def _find_latest_model(self) -> Optional[Path]:
        """Return the most recent CVD model file."""
        for candidate_dir in [MODELS_DIR / "saved", MODELS_DIR]:
            if candidate_dir.exists():
                files = list(candidate_dir.glob("cvd_model_*.joblib"))
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
                elif feat == "systolic_bp":
                    bg[feat] = np.random.uniform(100, 160, n)
                elif feat == "diastolic_bp":
                    bg[feat] = np.random.uniform(60, 100, n)
                elif feat == "hba1c":
                    bg[feat] = np.random.uniform(4.5, 7.5, n)
                elif feat == "fasting_glucose":
                    bg[feat] = np.random.uniform(70, 150, n)
                elif feat == "total_cholesterol":
                    bg[feat] = np.random.uniform(150, 250, n)
                elif feat == "hdl_cholesterol":
                    bg[feat] = np.random.uniform(30, 80, n)
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
            logger.info("CVD SHAP explainer initialized")
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
        self, metrics: Union[Dict[str, Any], "CVDMetricsInput"]
    ) -> pd.DataFrame:
        """
        Transform API input into the feature DataFrame expected by the CVD model.

        Mirrors the CVDPreprocessor encoding:
        - gender: 0=Male, 1=Female
        - one-hot: race_ethnicity, smoking_status, activity_level, bmi_category, age_group
          (all with drop_first=True, so the first category is the reference)
        - diabetes_indicator derived from diabetes field / hba1c / fasting_glucose
        """
        if hasattr(metrics, "model_dump"):
            metrics = metrics.model_dump()

        age = float(metrics["age"])
        gender = 0.0 if str(metrics["gender"]).lower() == "male" else 1.0

        # BMI
        bmi = metrics.get("bmi")
        if bmi is None:
            w, h = metrics.get("weight"), metrics.get("height")
            bmi = (w / ((h / 100) ** 2)) if (w and h) else 25.0
        bmi = float(bmi)

        systolic_bp  = self._get_float(metrics, "systolic_bp",  120.0)
        diastolic_bp = self._get_float(metrics, "diastolic_bp",  80.0)
        waist        = self._get_float(metrics, "waist_circumference", 90.0)
        hba1c        = self._get_float(metrics, "hba1c",          5.5)
        glucose      = self._get_float(metrics, "fasting_glucose", 90.0)
        total_chol   = self._get_float(metrics, "total_cholesterol", 200.0)
        hdl_chol     = self._get_float(metrics, "hdl_cholesterol",   50.0)
        education    = self._get_float(metrics, "education",    3.0)
        income_ratio = self._get_float(metrics, "income_ratio", 2.0)
        sedentary    = self._get_float(metrics, "sedentary_minutes", 480.0)

        # Derived: diabetes_indicator
        known_diabetes = self._get_bool(metrics, "diabetes", False)
        diabetes_indicator = 1.0 if (
            known_diabetes or hba1c >= 6.5 or glucose >= 126
        ) else 0.0

        # Smoking raw variables (as produced by preprocessor)
        smoking = str(metrics.get("smoking_status") or "never").lower()
        smoked_100    = 1.0 if smoking in ("former", "current") else 0.0
        current_smoke = 1.0 if smoking == "current" else 0.0

        features: Dict[str, float] = {
            "age": age,
            "gender": gender,
            "education": education,
            "income_ratio": income_ratio,
            "bmi": bmi,
            "waist_circumference": waist,
            "systolic_bp": systolic_bp,
            "diastolic_bp": diastolic_bp,
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
        }

        # One-hot: race_ethnicity (drop_first → category 1.0 is reference)
        for cat in ["2.0", "3.0", "4.0", "6.0", "7.0"]:
            features[f"race_ethnicity_{cat}"] = 0.0

        # One-hot: smoking_status (drop_first → 'Current' is reference)
        features["smoking_status_Former"] = 1.0 if smoking == "former" else 0.0
        features["smoking_status_Never"]  = 1.0 if smoking == "never"  else 0.0

        # One-hot: activity_level (drop_first → 'High' is reference)
        features["activity_level_Low"]      = 0.0
        features["activity_level_Moderate"] = 0.0
        features["activity_level_Sedentary"] = 1.0  # default

        # One-hot: bmi_category (drop_first → 'Normal' is reference)
        bmi_cat = self._get_bmi_category(bmi)
        features["bmi_category_Obese_I"]    = 1.0 if bmi_cat == "Obese_I"    else 0.0
        features["bmi_category_Obese_II"]   = 1.0 if bmi_cat == "Obese_II"   else 0.0
        features["bmi_category_Obese_III"]  = 1.0 if bmi_cat == "Obese_III"  else 0.0
        features["bmi_category_Overweight"] = 1.0 if bmi_cat == "Overweight" else 0.0
        features["bmi_category_Underweight"]= 1.0 if bmi_cat == "Underweight"else 0.0

        # One-hot: age_group (drop_first → '18-35' is reference)
        age_grp = self._get_age_group(age)
        features["age_group_36-45"] = 1.0 if age_grp == "36-45" else 0.0
        features["age_group_46-55"] = 1.0 if age_grp == "46-55" else 0.0
        features["age_group_56-65"] = 1.0 if age_grp == "56-65" else 0.0
        features["age_group_65+"]   = 1.0 if age_grp == "65+"   else 0.0

        df = pd.DataFrame([features])

        # Align to model's expected feature set if model is loaded
        if self.model and self.model.feature_names:
            for col in self.model.feature_names:
                if col not in df.columns:
                    df[col] = 0.0
            df = df[self.model.feature_names]

        return df

    # ── Prediction ─────────────────────────────────────────────────────────────

    def predict(
        self,
        metrics: Union[Dict[str, Any], "CVDMetricsInput"],
        include_explanation: bool = True,
    ) -> Dict[str, Any]:
        """Generate a CVD risk prediction."""
        if not self.is_ready():
            raise RuntimeError("CVD model not loaded.")

        if hasattr(metrics, "model_dump"):
            metrics = metrics.model_dump()

        features_df = self.prepare_features(metrics)

        proba = self.model.predict_proba(features_df)[0]
        risk_probability = float(proba[1])
        prediction = int(self.model.predict(features_df)[0])
        confidence = float(max(proba))

        # CVD risk thresholds (Framingham-calibrated)
        if risk_probability < 0.10:      category = "Low"
        elif risk_probability < 0.20:    category = "Moderate"
        elif risk_probability < 0.40:    category = "High"
        else:                            category = "Very High"

        result = {
            "assessment_id": (
                f"cvd_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
            ),
            "timestamp": datetime.utcnow().isoformat(),
            "risk": {
                "risk_probability": round(risk_probability, 4),
                "risk_percentage":  round(risk_probability * 100, 1),
                "risk_category":    category,
                "prediction":       prediction,
                "confidence":       round(confidence, 4),
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
        """Generate CVD-specific health recommendations."""
        recs = []
        risk_cat = result.get("risk", {}).get("risk_category", "Low")

        bmi = metrics.get("bmi")
        if bmi is None:
            w, h = metrics.get("weight"), metrics.get("height")
            if w and h:
                bmi = w / ((h / 100) ** 2)

        total_chol  = metrics.get("total_cholesterol")
        hdl_chol    = metrics.get("hdl_cholesterol")
        systolic_bp = metrics.get("systolic_bp")
        smoking     = str(metrics.get("smoking_status") or "never").lower()
        hba1c       = metrics.get("hba1c")

        # Blood pressure
        if systolic_bp and systolic_bp >= 130:
            priority = "high" if systolic_bp >= 140 else "medium"
            recs.append({
                "category": "blood_pressure",
                "priority": priority,
                "recommendation": "Work with your doctor to control blood pressure",
                "rationale": (
                    f"Systolic BP of {systolic_bp:.0f} mmHg raises CVD risk. "
                    "Target: below 130/80 mmHg."
                ),
                "source": "ACC/AHA Hypertension Guidelines 2017",
            })

        # Cholesterol
        if total_chol and total_chol >= 200:
            recs.append({
                "category": "cholesterol",
                "priority": "high" if total_chol >= 240 else "medium",
                "recommendation": "Reduce saturated fat intake and discuss lipid-lowering therapy with your doctor",
                "rationale": (
                    f"Total cholesterol of {total_chol:.0f} mg/dL increases CVD risk. "
                    "Target: below 200 mg/dL."
                ),
                "source": "AHA/ACC Cholesterol Guidelines",
            })

        if hdl_chol and hdl_chol < 40:
            recs.append({
                "category": "cholesterol",
                "priority": "medium",
                "recommendation": "Increase HDL through aerobic exercise and healthy fats",
                "rationale": (
                    f"Low HDL cholesterol ({hdl_chol:.0f} mg/dL) is an independent CVD risk factor."
                ),
                "source": "AHA",
            })

        # Smoking — most impactful modifiable CVD risk factor
        if smoking == "current":
            recs.append({
                "category": "smoking",
                "priority": "high",
                "recommendation": "Quit smoking immediately — consider NRT, varenicline, or a cessation programme",
                "rationale": "Smoking doubles CVD risk. Quitting within 1 year halves that excess risk.",
                "source": "WHO",
            })

        # BMI
        if bmi and bmi >= 30:
            recs.append({
                "category": "weight",
                "priority": "high" if bmi >= 35 else "medium",
                "recommendation": "Achieve a healthy weight through diet and physical activity",
                "rationale": (
                    f"BMI of {bmi:.1f} increases cardiac workload and CVD risk. "
                    "Even 5-10% weight loss is clinically significant."
                ),
                "source": "WHO / ACC/AHA Guidelines",
            })

        # Diabetes / blood sugar
        if hba1c and hba1c >= 6.5:
            recs.append({
                "category": "blood_sugar",
                "priority": "high",
                "recommendation": "Manage diabetes actively — optimise HbA1c to below 7%",
                "rationale": (
                    f"HbA1c of {hba1c:.1f}% indicates diabetes, which 2-3× CVD risk."
                ),
                "source": "ADA / AHA",
            })

        # Exercise for all elevated-risk patients
        if risk_cat in ("Moderate", "High", "Very High"):
            recs.append({
                "category": "exercise",
                "priority": "medium",
                "recommendation": "Aim for ≥150 minutes of moderate aerobic exercise per week",
                "rationale": "Regular aerobic activity reduces CVD risk by 20-35%.",
                "source": "AHA Physical Activity Guidelines",
            })

        # Medical follow-up
        if risk_cat in ("High", "Very High"):
            recs.append({
                "category": "medical",
                "priority": "high",
                "recommendation": "Consult a cardiologist or GP for a comprehensive CVD risk evaluation",
                "rationale": (
                    f"Your {risk_cat.lower()} CVD risk warrants professional clinical assessment."
                ),
                "source": "ACC/AHA Prevention Guidelines",
            })

        # ── Baseline wellness recommendations (all risk levels) ──────────────
        if not any(r["category"] == "exercise" for r in recs):
            recs.append({
                "category": "exercise",
                "priority": "low",
                "recommendation": "Keep up at least 150 min/week of moderate aerobic activity — it's your strongest heart protector",
                "rationale": "Regular exercise reduces CVD risk by 20-35% regardless of baseline risk.",
                "source": "AHA Physical Activity Guidelines",
            })

        if not any(r["category"] in ("cholesterol", "diet") for r in recs):
            recs.append({
                "category": "diet",
                "priority": "low",
                "recommendation": "Eat a heart-healthy diet: more fish, nuts, olive oil, vegetables; less red meat and saturated fat",
                "rationale": "A Mediterranean-style diet reduces CVD events by ~30%.",
                "source": "PREDIMED Trial / AHA",
            })

        if not any(r["category"] == "stress" for r in recs):
            recs.append({
                "category": "stress",
                "priority": "low",
                "recommendation": "Manage stress through regular physical activity, adequate sleep (7–8 hrs), and relaxation techniques",
                "rationale": "Chronic stress raises cortisol, blood pressure, and inflammation — all CVD risk factors.",
                "source": "AHA",
            })

        if not any(r["category"] == "medical" for r in recs):
            recs.append({
                "category": "medical",
                "priority": "low",
                "recommendation": "Have your blood pressure and cholesterol checked at least every 5 years (or annually if over 40)",
                "rationale": "Silent risk factors like hypertension and high cholesterol have no symptoms until damage occurs.",
                "source": "ACC/AHA Prevention Guidelines",
            })

        return recs

    # ── Model info ─────────────────────────────────────────────────────────────

    def get_model_info(self) -> Dict[str, Any]:
        if not self.is_ready():
            return {"error": "CVD model not loaded"}

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
            "model_name": "CVD Risk Prediction Model",
            "version": self.model_version,
            "trained_at": trained_at,
            "n_features": len(self.model.feature_names),
            "feature_names": self.model.feature_names,
            "performance_metrics": performance_metrics,
        }


# Singleton instance
cvd_prediction_service = CVDPredictionService()
