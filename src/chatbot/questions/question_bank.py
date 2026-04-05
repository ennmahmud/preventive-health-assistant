"""
Question Bank
=============
Validated lifestyle consultation questions for each health condition.

A normal person won't know their HbA1c or cholesterol — all questions
here are answerable without laboratory tests or clinical knowledge.

Questions are organised into three layers:
  Layer 0 (shared demographics): age, sex, height/weight
  Layer 1 (shared lifestyle):    activity, smoking, sleep, diet, alcohol, stress, salt
  Layer 2 (condition-specific):  4-6 additional questions per condition

Each question maps to intermediate lifestyle keys (not raw model feature names).
The LifestyleFeatureMapper translates these keys into the exact feature dicts
that each prediction service's prepare_features() expects.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class QuestionDef:
    id: str                              # e.g. "Q-LS-1", "Q-DM-2"
    text: str                            # conversational prompt shown to user
    response_type: str                   # "choice" | "yes_no" | "numeric" | "scale" | "text"
    options: Optional[List[str]] = None  # for choice/yes_no; shown as hint in chat
    option_keys: Optional[List[str]] = None  # canonical keys matching options list
    maps_to: List[str] = field(default_factory=list)   # intermediate lifestyle keys
    skip_if_profile_has: List[str] = field(default_factory=list)  # skip if profile has these
    required: bool = True
    layer: int = 1                       # 0=demographics, 1=shared lifestyle, 2=condition-specific
    unit_hint: Optional[str] = None      # e.g. "cm" or "kg" for numeric inputs


# ── Layer 0: Universal Demographics ──────────────────────────────────────────

DEMOGRAPHIC_QUESTIONS: List[QuestionDef] = [
    QuestionDef(
        id="Q-D-1",
        text="How old are you?",
        response_type="numeric",
        maps_to=["age"],
        skip_if_profile_has=["age"],
        unit_hint="years",
        layer=0,
    ),
    QuestionDef(
        id="Q-D-2",
        text="What is your biological sex?",
        response_type="choice",
        options=["Male", "Female"],
        option_keys=["male", "female"],
        maps_to=["gender"],
        skip_if_profile_has=["gender"],
        layer=0,
    ),
    QuestionDef(
        id="Q-D-3",
        text="Roughly how tall are you and how much do you weigh? (This lets me estimate your BMI.)",
        response_type="text",
        maps_to=["height", "weight"],
        skip_if_profile_has=["bmi"],
        required=False,
        layer=0,
    ),
]


# ── Layer 1: Shared Lifestyle Questions ──────────────────────────────────────

LIFESTYLE_QUESTIONS: List[QuestionDef] = [
    QuestionDef(
        id="Q-LS-1",
        text=(
            "How physically active are you on a typical day?\n"
            "• **Mostly sitting** — desk job, mostly watching TV or resting\n"
            "• **Light** — occasional walks, light household chores\n"
            "• **Moderate** — regular walks, cycling, gym 2-3×/week\n"
            "• **Very active** — daily vigorous exercise or physically demanding job"
        ),
        response_type="choice",
        options=["Mostly sitting", "Light activity", "Moderate", "Very active"],
        option_keys=["sedentary", "light", "moderate", "active"],
        maps_to=["activity_level"],
        skip_if_profile_has=["activity_level"],
        layer=1,
    ),
    QuestionDef(
        id="Q-LS-2",
        text="Do you smoke, or have you ever smoked?",
        response_type="choice",
        options=["Never smoked", "I quit smoking", "I currently smoke"],
        option_keys=["never", "former", "current"],
        maps_to=["smoking_status"],
        skip_if_profile_has=["smoking_status"],
        layer=1,
    ),
    QuestionDef(
        id="Q-LS-3",
        text=(
            "How would you describe your typical diet?\n"
            "• **Healthy** — mostly vegetables, fruits, whole grains, lean proteins\n"
            "• **Mixed** — a balance of healthy and less healthy foods\n"
            "• **Poor** — mostly processed food, fast food, or sugary snacks"
        ),
        response_type="choice",
        options=["Healthy", "Mixed / average", "Poor / lots of processed food"],
        option_keys=["healthy", "mixed", "poor"],
        maps_to=["diet_quality"],
        skip_if_profile_has=["diet_quality"],
        layer=1,
    ),
    QuestionDef(
        id="Q-LS-4",
        text="On average, how many hours of sleep do you get per night?",
        response_type="choice",
        options=["Less than 5 hours", "5–6 hours", "7–8 hours", "More than 8 hours"],
        option_keys=["under5", "5to6", "7to8", "over8"],
        maps_to=["sleep_hours"],
        skip_if_profile_has=["sleep_hours"],
        required=False,
        layer=1,
    ),
    QuestionDef(
        id="Q-LS-5",
        text="How many alcoholic drinks (beer, wine, spirits) do you have in a typical week?",
        response_type="choice",
        options=["None", "1–7 drinks", "8–14 drinks", "More than 14 drinks"],
        option_keys=["none", "light", "moderate", "heavy"],
        maps_to=["alcohol_weekly"],
        skip_if_profile_has=["alcohol_weekly"],
        required=False,
        layer=1,
    ),
    QuestionDef(
        id="Q-LS-6",
        text=(
            "How stressed do you typically feel day-to-day?\n"
            "1 = Very calm  →  5 = Very stressed"
        ),
        response_type="scale",
        maps_to=["stress_level"],
        skip_if_profile_has=["stress_level"],
        required=False,
        layer=1,
    ),
]


# ── Layer 2: Condition-Specific Questions ────────────────────────────────────

DIABETES_QUESTIONS: List[QuestionDef] = [
    QuestionDef(
        id="Q-DM-1",
        text="Does diabetes run in your family? (parent, brother, sister, or grandparent)",
        response_type="yes_no",
        options=["Yes", "No", "Not sure"],
        option_keys=["yes", "no", "unknown"],
        maps_to=["family_diabetes"],
        skip_if_profile_has=["family_diabetes"],
        layer=2,
    ),
    QuestionDef(
        id="Q-DM-2",
        text="Have you ever been told you have pre-diabetes, insulin resistance, or borderline blood sugar?",
        response_type="yes_no",
        options=["Yes", "No", "Not sure"],
        option_keys=["yes", "no", "unknown"],
        maps_to=["prediabetes_flag"],
        required=False,
        layer=2,
    ),
    QuestionDef(
        id="Q-DM-3",
        text=(
            "How many sugary drinks do you have on a typical day?\n"
            "(soda, juice, energy drinks, sweet tea)"
        ),
        response_type="choice",
        options=["None or rarely", "1–2 per week", "1 per day", "2 or more per day"],
        option_keys=["none", "occasional", "daily", "heavy"],
        maps_to=["sugar_intake"],
        skip_if_profile_has=["sugar_intake"],
        required=False,
        layer=2,
    ),
    QuestionDef(
        id="Q-DM-4",
        text="Do you often feel unusually thirsty, tired, or need to urinate frequently?",
        response_type="yes_no",
        options=["Yes", "No"],
        option_keys=["yes", "no"],
        maps_to=["diabetes_symptoms"],
        required=False,
        layer=2,
    ),
]

CVD_QUESTIONS: List[QuestionDef] = [
    QuestionDef(
        id="Q-CVD-1",
        text="Has anyone in your close family (parents or siblings) had a heart attack or stroke, especially before age 60?",
        response_type="yes_no",
        options=["Yes", "No", "Not sure"],
        option_keys=["yes", "no", "unknown"],
        maps_to=["family_cvd"],
        skip_if_profile_has=["family_cvd"],
        layer=2,
    ),
    QuestionDef(
        id="Q-CVD-2",
        text=(
            "How would you describe your salt intake?\n"
            "• Low — rarely add salt, avoid salty snacks\n"
            "• Moderate — sometimes add salt or eat salty foods\n"
            "• High — often add salt, eat lots of processed/fast food"
        ),
        response_type="choice",
        options=["Low", "Moderate", "High"],
        option_keys=["low", "moderate", "high"],
        maps_to=["salt_intake"],
        skip_if_profile_has=["salt_intake"],
        required=False,
        layer=2,
    ),
    QuestionDef(
        id="Q-CVD-3",
        text="Have you ever been told by a doctor that you have high blood pressure or high cholesterol?",
        response_type="yes_no",
        options=["Yes — high blood pressure", "Yes — high cholesterol", "Both", "Neither"],
        option_keys=["hbp", "hchol", "both", "neither"],
        maps_to=["self_reported_hbp", "self_reported_hchol"],
        required=False,
        layer=2,
    ),
    QuestionDef(
        id="Q-CVD-4",
        text="Do you ever experience any of these: chest tightness or pain, shortness of breath on mild exertion, or irregular heartbeat?",
        response_type="yes_no",
        options=["Yes", "No"],
        option_keys=["yes", "no"],
        maps_to=["cardiac_symptoms"],
        required=False,
        layer=2,
    ),
    QuestionDef(
        id="Q-CVD-5",
        text="Do you have diabetes or have you been told your blood sugar is high?",
        response_type="yes_no",
        options=["Yes", "No", "Not sure"],
        option_keys=["yes", "no", "unknown"],
        maps_to=["diabetes"],
        skip_if_profile_has=["diabetes"],
        required=False,
        layer=2,
    ),
]

HYPERTENSION_QUESTIONS: List[QuestionDef] = [
    QuestionDef(
        id="Q-HTN-1",
        text="Does high blood pressure run in your family? (parents or siblings)",
        response_type="yes_no",
        options=["Yes", "No", "Not sure"],
        option_keys=["yes", "no", "unknown"],
        maps_to=["family_htn"],
        skip_if_profile_has=["family_htn"],
        layer=2,
    ),
    QuestionDef(
        id="Q-HTN-2",
        text=(
            "How would you describe your salt and sodium intake?\n"
            "• Low — rarely salt food, avoid processed meals\n"
            "• Moderate — sometimes eat processed or salty food\n"
            "• High — frequently eat processed food, fast food, or add salt to meals"
        ),
        response_type="choice",
        options=["Low", "Moderate", "High"],
        option_keys=["low", "moderate", "high"],
        maps_to=["salt_intake"],
        skip_if_profile_has=["salt_intake"],
        layer=2,
    ),
    QuestionDef(
        id="Q-HTN-3",
        text="Have you ever been told your blood pressure was high or on the high side?",
        response_type="yes_no",
        options=["Yes", "No", "Not sure"],
        option_keys=["yes", "no", "unknown"],
        maps_to=["self_reported_hbp"],
        required=False,
        layer=2,
    ),
    QuestionDef(
        id="Q-HTN-4",
        text="Do you have diabetes or a history of kidney problems?",
        response_type="yes_no",
        options=["Yes", "No", "Not sure"],
        option_keys=["yes", "no", "unknown"],
        maps_to=["diabetes"],
        skip_if_profile_has=["diabetes"],
        required=False,
        layer=2,
    ),
]


# ── Full question sets per condition ─────────────────────────────────────────

CONDITION_QUESTIONS: Dict[str, List[QuestionDef]] = {
    "diabetes": DEMOGRAPHIC_QUESTIONS + LIFESTYLE_QUESTIONS + DIABETES_QUESTIONS,
    "cvd": DEMOGRAPHIC_QUESTIONS + LIFESTYLE_QUESTIONS + CVD_QUESTIONS,
    "hypertension": DEMOGRAPHIC_QUESTIONS + LIFESTYLE_QUESTIONS + HYPERTENSION_QUESTIONS,
}

# Minimum required fields to trigger a prediction (all others get lifestyle defaults)
MINIMUM_REQUIRED: Dict[str, List[str]] = {
    "diabetes": ["age", "gender"],
    "cvd": ["age", "gender"],
    "hypertension": ["age", "gender"],
}

# Fields that strengthen prediction significantly — ask if not answered
STRONGLY_RECOMMENDED: Dict[str, List[str]] = {
    "diabetes": ["activity_level", "diet_quality", "family_diabetes"],
    "cvd": ["activity_level", "smoking_status", "family_cvd"],
    "hypertension": ["activity_level", "salt_intake", "family_htn"],
}
