"""
Entity Extractor
================
Regex-based extraction of health metric values from natural language.

Examples handled:
  "I'm 45 years old"          → age=45
  "my BMI is 28.5"            → bmi=28.5
  "I weigh 80 kg"             → weight=80
  "I'm 175 cm tall"           → height=175
  "my cholesterol is 210"     → total_cholesterol=210
  "HDL 55"                    → hdl_cholesterol=55
  "HbA1c of 6.2%"            → hba1c=6.2
  "fasting glucose 105 mg"    → fasting_glucose=105
  "I smoke"                   → smoking_status="current"
  "I used to smoke"           → smoking_status="former"
  "non smoker"                → smoking_status="never"
  "I have diabetes"           → diabetes=True
  "I'm male"                  → gender="male"
  "sedentary 480 min"         → sedentary_minutes=480
  "systolic 130"              → systolic_bp=130
  "diastolic 85"              → diastolic_bp=85
  "waist 92 cm"               → waist_circumference=92
"""

import re
from typing import Dict, Any, Optional


# ── Helpers ──────────────────────────────────────────────────────────────────

def _num(s: str) -> float:
    """Parse string → float."""
    return float(s.replace(",", "."))


# ── Extraction patterns ───────────────────────────────────────────────────────

_AGE_RE = re.compile(
    r"\b(?:i'?m|i am|age[d]?|aged?|years? old[:]?)?\s*(\d{1,3})\s*(?:years?(?: old)?|yr|yrs)?\b",
    re.IGNORECASE,
)
_AGE_EXPLICIT_RE = re.compile(
    r"\b(?:my\s+)?age\s+(?:is\s+)?(\d{1,3})\b",
    re.IGNORECASE,
)

_BMI_RE = re.compile(
    r"\bbmi\s*(?:is|of|:)?\s*([\d.]+)\b",
    re.IGNORECASE,
)

_WEIGHT_RE = re.compile(
    # keyword-prefixed ("I weigh 95 kg") OR bare unit ("95kg")
    r"\b(?:(?:weigh(?:t|s)?|weight\s+is)\s*([\d.]+)\s*(?:kg|kilograms?|lbs?|pounds?)?\b"
    r"|([\d.]+)\s*(?:kg|kilograms?))\b",
    re.IGNORECASE,
)

_HEIGHT_RE = re.compile(
    # keyword-before ("I am 178 cm") OR "X cm tall" OR bare unit ("178cm")
    r"\b(?:(?:height|tall|i'?m|am)\s*([\d.]+)\s*(?:cm|centimetres?|centimeters?|m|meters?)"
    r"|([\d.]+)\s*(?:cm|centimetres?|centimeters?)\s+tall"
    r"|([\d.]+)\s*cm)\b",
    re.IGNORECASE,
)

_CHOLESTEROL_RE = re.compile(
    r"\b(?:total\s+)?cholesterol\s*(?:is|of|level[s]?|:)?\s*([\d.]+)\b",
    re.IGNORECASE,
)

_HDL_RE = re.compile(
    r"\bhdl\s*(?:cholesterol|is|of|level[s]?|:)?\s*([\d.]+)\b",
    re.IGNORECASE,
)

_HBA1C_RE = re.compile(
    r"\b(?:hba1c|a1c|glycated\s+haemoglobin|hemoglobin\s+a1c)\s*(?:is|of|:)?\s*([\d.]+)\s*%?\b",
    re.IGNORECASE,
)

_GLUCOSE_RE = re.compile(
    r"\b(?:fasting\s+)?(?:blood\s+)?glucose\s*(?:is|of|level[s]?|:)?\s*([\d.]+)\b",
    re.IGNORECASE,
)

_SYSTOLIC_RE = re.compile(
    r"\b(?:systolic(?:\s+bp|\s+blood\s+pressure)?)\s*(?:is|of|:)?\s*([\d.]+)\b",
    re.IGNORECASE,
)

_DIASTOLIC_RE = re.compile(
    r"\b(?:diastolic(?:\s+bp|\s+blood\s+pressure)?)\s*(?:is|of|:)?\s*([\d.]+)\b",
    re.IGNORECASE,
)

_BP_PAIR_RE = re.compile(
    r"\b(?:bp|blood\s*pressure)\s*(?:is|of|:)?\s*(\d+)\s*/\s*(\d+)\b",
    re.IGNORECASE,
)

_WAIST_RE = re.compile(
    r"\b(?:waist(?:\s+circumference)?)\s*(?:is|of|:)?\s*([\d.]+)\s*(?:cm|centimetres?)?\b",
    re.IGNORECASE,
)

_SEDENTARY_RE = re.compile(
    r"\b(?:sedentary|sitting|inactive)\s*(?:for\s+)?([\d.]+)\s*(?:min(?:utes?)?|hrs?|hours?)?\b",
    re.IGNORECASE,
)

_GENDER_MALE_RE = re.compile(
    r"\b(?:i'?m\s+)?(?:male|man|boy|gentleman|he|his)\b",
    re.IGNORECASE,
)
_GENDER_FEMALE_RE = re.compile(
    r"\b(?:i'?m\s+)?(?:female|woman|girl|lady|she|her)\b",
    re.IGNORECASE,
)

_SMOKING_CURRENT_RE = re.compile(
    r"\b(?:i\s+)?(?:smoke[sd]?|smoker|currently\s+smok(?:e|ing)|am\s+a\s+smoker)\b",
    re.IGNORECASE,
)
_SMOKING_FORMER_RE = re.compile(
    r"\b(?:used\s+to\s+smoke|ex[\s-]?smoker|former\s+smoker|quit\s+smoking|stopped\s+smoking)\b",
    re.IGNORECASE,
)
_SMOKING_NEVER_RE = re.compile(
    r"\b(?:non[\s-]?smoker|never\s+smoked?|don'?t\s+smoke|do\s+not\s+smoke|no\s+smoking)\b",
    re.IGNORECASE,
)

_DIABETES_TRUE_RE = re.compile(
    r"\b(?:i\s+have\s+)?(?:diabet(?:es|ic)|type\s*[12]\s*diabet(?:es|ic)|diagnosed\s+with\s+diabetes)\b",
    re.IGNORECASE,
)
_DIABETES_FALSE_RE = re.compile(
    r"\b(?:no\s+diabetes|not\s+diabetic|don'?t\s+have\s+diabetes|no\s+history\s+of\s+diabetes)\b",
    re.IGNORECASE,
)


# ── Public API ────────────────────────────────────────────────────────────────

def extract_entities(message: str) -> Dict[str, Any]:
    """
    Extract health metric entities from a natural-language message.

    Returns a dict of {field_name: value} for any entities found.
    Returns an empty dict if nothing is recognised.
    """
    entities: Dict[str, Any] = {}
    msg = message.strip()

    # Age — explicit "my age is X" takes priority
    m = _AGE_EXPLICIT_RE.search(msg)
    if m:
        val = int(m.group(1))
        if 1 <= val <= 120:
            entities["age"] = val
    elif (m := _AGE_RE.search(msg)):
        val = int(m.group(1))
        if 1 <= val <= 120:
            entities["age"] = val

    # Gender
    if _GENDER_FEMALE_RE.search(msg):
        entities["gender"] = "female"
    elif _GENDER_MALE_RE.search(msg):
        entities["gender"] = "male"

    # BMI
    if (m := _BMI_RE.search(msg)):
        entities["bmi"] = _num(m.group(1))

    # Weight — g1: keyword-prefixed, g2: bare unit ("95kg")
    if (m := _WEIGHT_RE.search(msg)):
        val = _num(m.group(1) or m.group(2))
        if 20.0 <= val <= 500.0:
            entities["weight"] = val

    # Height — g1: keyword-before, g2: "X cm tall", g3: bare unit ("178cm")
    # For bare-unit (g3 only), skip if a waist keyword is also present to avoid collision
    _has_waist_kw = bool(re.search(r"\bwaist\b", msg, re.IGNORECASE))
    if (m := _HEIGHT_RE.search(msg)):
        raw = m.group(1) or m.group(2) or (None if _has_waist_kw else m.group(3))
        if raw is not None:
            val = _num(raw)
            if 50.0 <= val <= 250.0:
                entities["height"] = val

    # Cholesterol (check HDL before total to avoid double-match)
    if (m := _HDL_RE.search(msg)):
        entities["hdl_cholesterol"] = _num(m.group(1))
    if (m := _CHOLESTEROL_RE.search(msg)):
        # Avoid re-capturing HDL number as total
        if "hdl_cholesterol" not in entities or _num(m.group(1)) != entities.get("hdl_cholesterol"):
            entities["total_cholesterol"] = _num(m.group(1))

    # HbA1c
    if (m := _HBA1C_RE.search(msg)):
        entities["hba1c"] = _num(m.group(1))

    # Fasting glucose
    if (m := _GLUCOSE_RE.search(msg)):
        entities["fasting_glucose"] = _num(m.group(1))

    # Blood pressure — pair first, then individual
    if (m := _BP_PAIR_RE.search(msg)):
        entities["systolic_bp"] = float(m.group(1))
        entities["diastolic_bp"] = float(m.group(2))
    else:
        if (m := _SYSTOLIC_RE.search(msg)):
            entities["systolic_bp"] = _num(m.group(1))
        if (m := _DIASTOLIC_RE.search(msg)):
            entities["diastolic_bp"] = _num(m.group(1))

    # Waist
    if (m := _WAIST_RE.search(msg)):
        entities["waist_circumference"] = _num(m.group(1))

    # Sedentary minutes
    if (m := _SEDENTARY_RE.search(msg)):
        entities["sedentary_minutes"] = int(float(m.group(1)))

    # Smoking status (order matters — former before current)
    if _SMOKING_NEVER_RE.search(msg):
        entities["smoking_status"] = "never"
    elif _SMOKING_FORMER_RE.search(msg):
        entities["smoking_status"] = "former"
    elif _SMOKING_CURRENT_RE.search(msg):
        entities["smoking_status"] = "current"

    # Diabetes
    if _DIABETES_FALSE_RE.search(msg):
        entities["diabetes"] = False
    elif _DIABETES_TRUE_RE.search(msg):
        entities["diabetes"] = True

    return entities
