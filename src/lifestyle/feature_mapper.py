"""
Lifestyle Feature Mapper
========================
Translates lifestyle consultation answers (intermediate keys) into the exact
feature dictionaries each prediction service's prepare_features() expects.

Design principle:
- Lifestyle answers give us medically-grounded defaults for features users
  cannot know (HbA1c, cholesterol, etc.)
- If a user happens to know a clinical value, it always overrides the lifestyle default
- All derived values are conservative (toward normal/healthy) — we never
  over-estimate risk from missing data alone

The mapper covers:
  activity_level   → sedentary_minutes, vigorous_rec, moderate_rec, activity flags
  smoking_status   → smoked_100, current_smoker, smoking_status enum
  diet_quality     → fasting_glucose default, hba1c default
  sleep_hours      → sedentary adjustment, stress factor
  alcohol_weekly   → hdl_cholesterol default, total_cholesterol default
  stress_level     → systolic_bp default modifier
  salt_intake      → systolic_bp default
  family_diabetes  → family_diabetes flag
  family_cvd       → triggers risk category adjustment
  family_htn       → triggers risk category adjustment
  sugar_intake     → fasting_glucose / hba1c adjustment
  self_reported_hbp / hchol → triggers clinical defaults adjustment
"""

import math
from typing import Any, Dict, Optional


# ── Activity Level Mapping ────────────────────────────────────────────────────

_ACTIVITY_MAP: Dict[str, Dict[str, Any]] = {
    "sedentary": {
        "sedentary_minutes": 600,
        "vigorous_work": 0,
        "moderate_work": 0,
        "vigorous_rec": 0,
        "moderate_rec": 0,
        "activity_level": "sedentary",
        "physical_activity_minutes": 0,
    },
    "light": {
        "sedentary_minutes": 420,
        "vigorous_work": 0,
        "moderate_work": 1,
        "vigorous_rec": 0,
        "moderate_rec": 1,
        "activity_level": "low",
        "physical_activity_minutes": 60,
    },
    "moderate": {
        "sedentary_minutes": 240,
        "vigorous_work": 0,
        "moderate_work": 1,
        "vigorous_rec": 0,
        "moderate_rec": 1,
        "activity_level": "moderate",
        "physical_activity_minutes": 150,
    },
    "active": {
        "sedentary_minutes": 120,
        "vigorous_work": 1,
        "moderate_work": 1,
        "vigorous_rec": 1,
        "moderate_rec": 1,
        "activity_level": "high",
        "physical_activity_minutes": 300,
    },
}

# ── Smoking Mapping ───────────────────────────────────────────────────────────

_SMOKING_MAP: Dict[str, Dict[str, Any]] = {
    "never": {
        "smoking_status": "never",
        "smoked_100": 0,
        "current_smoker": 0,
        "smoking_status_Former Smoker": 0,
        "smoking_status_Never Smoked": 1,
        "smoking_status_Now Smokes Cigarettes": 0,
    },
    "former": {
        "smoking_status": "former",
        "smoked_100": 1,
        "current_smoker": 0,
        "smoking_status_Former Smoker": 1,
        "smoking_status_Never Smoked": 0,
        "smoking_status_Now Smokes Cigarettes": 0,
    },
    "current": {
        "smoking_status": "current",
        "smoked_100": 1,
        "current_smoker": 1,
        "smoking_status_Former Smoker": 0,
        "smoking_status_Never Smoked": 0,
        "smoking_status_Now Smokes Cigarettes": 1,
    },
}

# ── Diet Quality → Clinical Defaults ─────────────────────────────────────────
# These are conservative population-level estimates used ONLY when the user
# has not provided actual clinical values.

_DIET_GLUCOSE: Dict[str, float] = {
    "healthy": 88.0,
    "mixed": 98.0,
    "poor": 106.0,
}
_DIET_HBA1C: Dict[str, float] = {
    "healthy": 5.2,
    "mixed": 5.5,
    "poor": 5.8,
}

# ── Sugar Intake → Glucose/HbA1c Adjustment ──────────────────────────────────

_SUGAR_GLUCOSE_DELTA: Dict[str, float] = {
    "none": 0.0,
    "occasional": 2.0,
    "daily": 5.0,
    "heavy": 10.0,
}

# ── Sleep → Sedentary/Stress Adjustment ──────────────────────────────────────

_SLEEP_ADJUSTMENTS: Dict[str, Dict[str, float]] = {
    "under5": {"sedentary_delta": 90, "stress_factor": 1.3},
    "5to6":   {"sedentary_delta": 30, "stress_factor": 1.1},
    "7to8":   {"sedentary_delta": 0,  "stress_factor": 1.0},
    "over8":  {"sedentary_delta": 45, "stress_factor": 1.0},
}

# ── Alcohol → Cholesterol Defaults ───────────────────────────────────────────

_ALCOHOL_CHOL: Dict[str, Dict[str, float]] = {
    "none":     {"hdl_cholesterol": 50.0, "total_cholesterol": 195.0},
    "light":    {"hdl_cholesterol": 54.0, "total_cholesterol": 195.0},   # moderate benefit
    "moderate": {"hdl_cholesterol": 50.0, "total_cholesterol": 208.0},
    "heavy":    {"hdl_cholesterol": 45.0, "total_cholesterol": 220.0},
}

# ── Salt Intake → Systolic BP Default ────────────────────────────────────────

_SALT_SYSTOLIC: Dict[str, float] = {
    "low":      112.0,
    "moderate": 122.0,
    "high":     132.0,
}

# ── Stress Level → Systolic BP Modifier ──────────────────────────────────────

def _stress_systolic_delta(stress: int) -> float:
    """Returns additional mmHg based on self-reported stress (1–5)."""
    deltas = {1: -3.0, 2: 0.0, 3: 3.0, 4: 7.0, 5: 12.0}
    return deltas.get(stress, 0.0)


class LifestyleFeatureMapper:
    """
    Converts lifestyle answer dicts into model-ready feature dicts.

    Lifecycle:
      1. AnswerNormalizer produces canonical intermediate keys
      2. LifestyleFeatureMapper translates those to model feature dicts
      3. Prediction service's prepare_features() merges with model defaults

    Priority (highest to lowest):
      a. Explicit clinical values provided by user (e.g. actual HbA1c)
      b. Lifestyle-derived defaults from this mapper
      c. Model's own internal missing-value handling (XGBoost)
    """

    # ── Public API ────────────────────────────────────────────────────────────

    def map_for_diabetes(
        self,
        answers: Dict[str, Any],
        profile: Optional[Any] = None,
    ) -> Dict[str, Any]:
        features: Dict[str, Any] = {}

        self._apply_demographics(features, answers, profile)
        self._apply_activity(features, answers)
        self._apply_smoking(features, answers)
        self._apply_bmi(features, answers, profile)

        # Diet → glucose / HbA1c defaults (only if user hasn't given actual values)
        diet = answers.get("diet_quality", "mixed")
        sugar = answers.get("sugar_intake", "none")
        features.setdefault("fasting_glucose",
            _DIET_GLUCOSE.get(diet, 98.0) + _SUGAR_GLUCOSE_DELTA.get(sugar, 0.0))
        features.setdefault("hba1c",
            _DIET_HBA1C.get(diet, 5.5) + (_SUGAR_GLUCOSE_DELTA.get(sugar, 0.0) * 0.05))

        # Family history
        fam = answers.get("family_diabetes")
        if fam is not None:
            features["family_diabetes"] = bool(fam) if isinstance(fam, bool) else (fam == "yes")

        # Pre-diabetes flag boosts glucose estimate
        if answers.get("prediabetes_flag") in (True, "yes"):
            features["fasting_glucose"] = max(features.get("fasting_glucose", 98.0), 105.0)
            features["hba1c"] = max(features.get("hba1c", 5.5), 5.7)

        # Cholesterol defaults (from alcohol)
        self._apply_alcohol_cholesterol(features, answers)

        # Sleep adjustment on sedentary minutes
        self._apply_sleep(features, answers)

        # Any explicitly provided clinical values win over defaults
        self._apply_explicit_clinical(features, answers)

        return features

    def map_for_cvd(
        self,
        answers: Dict[str, Any],
        profile: Optional[Any] = None,
    ) -> Dict[str, Any]:
        features: Dict[str, Any] = {}

        self._apply_demographics(features, answers, profile)
        self._apply_activity(features, answers)
        self._apply_smoking(features, answers)
        self._apply_bmi(features, answers, profile)

        # BP defaults from salt + stress
        self._apply_bp_defaults(features, answers)

        # Cholesterol from alcohol
        self._apply_alcohol_cholesterol(features, answers)

        # Diabetes flag
        self._apply_diabetes_flag(features, answers)

        # Family CVD history → risk category note (stored in features as flag)
        fam_cvd = answers.get("family_cvd")
        if fam_cvd is not None:
            features["family_cvd"] = (fam_cvd in (True, "yes"))

        # Self-reported high BP → raise systolic default
        if answers.get("self_reported_hbp") in (True, "yes", "hbp", "both"):
            features["systolic_bp"] = max(features.get("systolic_bp", 120.0), 140.0)
            features["diastolic_bp"] = max(features.get("diastolic_bp", 80.0), 90.0)

        # Self-reported high cholesterol → raise cholesterol default
        if answers.get("self_reported_hchol") in (True, "yes", "hchol", "both"):
            features["total_cholesterol"] = max(features.get("total_cholesterol", 195.0), 230.0)
            features["hdl_cholesterol"] = min(features.get("hdl_cholesterol", 50.0), 42.0)

        # Sleep
        self._apply_sleep(features, answers)

        self._apply_explicit_clinical(features, answers)
        return features

    def map_for_hypertension(
        self,
        answers: Dict[str, Any],
        profile: Optional[Any] = None,
    ) -> Dict[str, Any]:
        features: Dict[str, Any] = {}

        self._apply_demographics(features, answers, profile)
        self._apply_activity(features, answers)
        self._apply_smoking(features, answers)
        self._apply_bmi(features, answers, profile)

        # Cholesterol from alcohol
        self._apply_alcohol_cholesterol(features, answers)

        # Diabetes flag
        self._apply_diabetes_flag(features, answers)

        # NOTE: systolic/diastolic BP intentionally excluded from HTN model
        # (circularity prevention — see hypertension_preprocessor.py)

        # Sleep
        self._apply_sleep(features, answers)

        # Family HTN history flag
        fam_htn = answers.get("family_htn")
        if fam_htn is not None:
            features["family_htn"] = (fam_htn in (True, "yes"))

        self._apply_explicit_clinical(features, answers)
        return features

    # ── Private helpers ───────────────────────────────────────────────────────

    def _apply_demographics(
        self,
        features: Dict[str, Any],
        answers: Dict[str, Any],
        profile: Optional[Any],
    ) -> None:
        # Age
        age = answers.get("age") or (profile.age if profile else None)
        if age:
            features["age"] = int(age)

        # Gender — support "male"/"female" and "Male"/"Female"
        gender = answers.get("gender") or (profile.biological_sex if profile else None)
        if gender:
            features["gender"] = str(gender).lower()

    def _apply_activity(
        self, features: Dict[str, Any], answers: Dict[str, Any]
    ) -> None:
        level = answers.get("activity_level", "moderate")
        mapping = _ACTIVITY_MAP.get(level, _ACTIVITY_MAP["moderate"])
        for k, v in mapping.items():
            features.setdefault(k, v)

    def _apply_smoking(
        self, features: Dict[str, Any], answers: Dict[str, Any]
    ) -> None:
        status = answers.get("smoking_status", "never")
        mapping = _SMOKING_MAP.get(status, _SMOKING_MAP["never"])
        for k, v in mapping.items():
            features.setdefault(k, v)

    def _apply_bmi(
        self,
        features: Dict[str, Any],
        answers: Dict[str, Any],
        profile: Optional[Any],
    ) -> None:
        # Explicit BMI from answers
        bmi = answers.get("bmi")
        if bmi:
            features["bmi"] = float(bmi)
            return

        # Derive from height + weight
        h = answers.get("height") or (profile.height_cm if profile else None)
        w = answers.get("weight") or (profile.weight_kg if profile else None)
        if h and w and float(h) > 0:
            derived = round(float(w) / ((float(h) / 100) ** 2), 1)
            if 10.0 <= derived <= 80.0:
                features["bmi"] = derived
                features.setdefault("height", float(h))
                features.setdefault("weight", float(w))

    def _apply_bp_defaults(
        self, features: Dict[str, Any], answers: Dict[str, Any]
    ) -> None:
        salt = answers.get("salt_intake", "moderate")
        base_systolic = _SALT_SYSTOLIC.get(salt, 122.0)

        stress = answers.get("stress_level")
        if stress:
            base_systolic += _stress_systolic_delta(int(stress))

        features.setdefault("systolic_bp", base_systolic)
        features.setdefault("diastolic_bp", base_systolic * 0.63)  # approx diastolic

    def _apply_alcohol_cholesterol(
        self, features: Dict[str, Any], answers: Dict[str, Any]
    ) -> None:
        alcohol = answers.get("alcohol_weekly", "none")
        mapping = _ALCOHOL_CHOL.get(alcohol, _ALCOHOL_CHOL["none"])
        for k, v in mapping.items():
            features.setdefault(k, v)

    def _apply_sleep(
        self, features: Dict[str, Any], answers: Dict[str, Any]
    ) -> None:
        sleep = answers.get("sleep_hours", "7to8")
        adj = _SLEEP_ADJUSTMENTS.get(sleep, _SLEEP_ADJUSTMENTS["7to8"])
        if "sedentary_minutes" in features:
            features["sedentary_minutes"] = min(
                720, features["sedentary_minutes"] + adj["sedentary_delta"]
            )
        if "stress_level" not in answers and adj["stress_factor"] != 1.0:
            # Adjust BP slightly for poor sleep
            if "systolic_bp" in features:
                features["systolic_bp"] = features["systolic_bp"] * adj["stress_factor"]

    def _apply_diabetes_flag(
        self, features: Dict[str, Any], answers: Dict[str, Any]
    ) -> None:
        has_dm = answers.get("diabetes")
        if has_dm is not None:
            features["diabetes"] = (has_dm in (True, "yes"))

    @staticmethod
    def _apply_explicit_clinical(
        features: Dict[str, Any], answers: Dict[str, Any]
    ) -> None:
        """Any real clinical values provided by the user override lifestyle defaults."""
        clinical_keys = [
            "hba1c", "fasting_glucose", "total_cholesterol", "hdl_cholesterol",
            "systolic_bp", "diastolic_bp", "waist_circumference",
            "bmi", "triglycerides",
        ]
        for k in clinical_keys:
            if k in answers and answers[k] is not None:
                features[k] = answers[k]


# Singleton
lifestyle_mapper = LifestyleFeatureMapper()
