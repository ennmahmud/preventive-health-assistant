"""
Profile RAG Store
=================
ChromaDB-based semantic retrieval of user health profiles.

Each profile is stored as a natural-language text document in ChromaDB.
When a returning user starts a new conversation, we retrieve their profile
and inject it as context — skipping questions they've already answered.

Uses sentence-transformers (all-MiniLM-L6-v2, ~22MB) for local embeddings.
Falls back to ChromaDB's default embedding function if torch isn't available.
"""

import logging
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

_CHROMA_PATH = str(Path(__file__).parent.parent.parent / "data" / "profiles" / "chroma")


@dataclass
class ProfileContext:
    """Context injected into a conversation for a returning user."""
    pre_populated_fields: Dict[str, Any] = field(default_factory=dict)
    welcome_message: str = ""
    questions_to_skip: List[str] = field(default_factory=list)  # question IDs
    last_risk_summary: Optional[str] = None


def _build_profile_text(profile: Any) -> str:
    """Convert a UserProfile to a natural-language description for embedding."""
    parts = []

    age_sex = []
    if profile.age:
        age_sex.append(f"{profile.age}-year-old")
    if profile.biological_sex:
        age_sex.append(profile.biological_sex)
    if age_sex:
        parts.append(" ".join(age_sex))

    if profile.bmi:
        parts.append(f"BMI {profile.bmi:.1f}")
    elif profile.height_cm and profile.weight_kg:
        bmi = profile.weight_kg / ((profile.height_cm / 100) ** 2)
        parts.append(f"BMI approximately {bmi:.1f}")

    activity_labels = {
        "sedentary": "mostly sedentary",
        "light": "lightly active",
        "moderate": "moderately active",
        "active": "very active",
    }
    if profile.activity_level:
        parts.append(activity_labels.get(profile.activity_level, profile.activity_level))

    smoking_labels = {
        "never": "never smoked",
        "former": "ex-smoker",
        "current": "current smoker",
    }
    if profile.smoking_status:
        parts.append(smoking_labels.get(profile.smoking_status, profile.smoking_status))

    diet_labels = {
        "healthy": "healthy diet",
        "mixed": "mixed diet",
        "poor": "poor diet with lots of processed food",
    }
    if profile.diet_quality:
        parts.append(diet_labels.get(profile.diet_quality, profile.diet_quality))

    sleep_labels = {
        "under5": "sleeps under 5 hours",
        "5to6": "sleeps 5–6 hours",
        "7to8": "sleeps 7–8 hours",
        "over8": "sleeps over 8 hours",
    }
    if profile.sleep_hours:
        parts.append(sleep_labels.get(profile.sleep_hours, ""))

    if profile.stress_level:
        stress_words = {1: "low", 2: "low-moderate", 3: "moderate", 4: "high", 5: "very high"}
        parts.append(f"{stress_words.get(profile.stress_level, 'moderate')} stress")

    if profile.alcohol_weekly:
        alcohol_labels = {
            "none": "doesn't drink alcohol",
            "light": "light drinker",
            "moderate": "moderate drinker",
            "heavy": "heavy drinker",
        }
        parts.append(alcohol_labels.get(profile.alcohol_weekly, ""))

    family_hx = []
    if profile.family_diabetes:
        family_hx.append("diabetes")
    if profile.family_cvd:
        family_hx.append("heart disease")
    if profile.family_htn:
        family_hx.append("hypertension")
    if family_hx:
        parts.append(f"family history of {', '.join(family_hx)}")

    risk_parts = []
    if profile.last_diabetes_risk is not None:
        risk_parts.append(f"diabetes risk {profile.last_diabetes_risk*100:.0f}%")
    if profile.last_cvd_risk is not None:
        risk_parts.append(f"CVD risk {profile.last_cvd_risk*100:.0f}%")
    if profile.last_htn_risk is not None:
        risk_parts.append(f"hypertension risk {profile.last_htn_risk*100:.0f}%")
    if risk_parts:
        parts.append("Previous assessments: " + ", ".join(risk_parts))

    return "Health profile: " + ". ".join(p for p in parts if p) + "."


class ProfileRAGStore:
    """Stores and retrieves user profiles using ChromaDB + sentence-transformers."""

    def __init__(self, persist_dir: str = _CHROMA_PATH):
        self._persist_dir = persist_dir
        self._collection = None
        self._ef = None
        self._initialized = False

    def _ensure_initialized(self) -> bool:
        """Lazy initialization — only load heavy dependencies when first used."""
        if self._initialized:
            return True
        try:
            import chromadb
            Path(self._persist_dir).mkdir(parents=True, exist_ok=True)
            client = chromadb.PersistentClient(path=self._persist_dir)

            # Try sentence-transformers first, fall back to default
            try:
                from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
                self._ef = SentenceTransformerEmbeddingFunction(
                    model_name="all-MiniLM-L6-v2"
                )
                logger.info("RAG: using sentence-transformers all-MiniLM-L6-v2")
            except Exception:
                # Fall back to chromadb's default (onnxruntime-based)
                self._ef = None
                logger.warning("RAG: sentence-transformers unavailable, using default embeddings")

            self._collection = client.get_or_create_collection(
                name="user_health_profiles",
                metadata={"hnsw:space": "cosine"},
                embedding_function=self._ef,
            )
            self._initialized = True
            return True
        except Exception as e:
            logger.warning("RAG store unavailable: %s", e)
            return False

    def index_profile(self, profile: Any) -> Optional[str]:
        """Embed profile and upsert into ChromaDB. Returns doc_id."""
        if not self._ensure_initialized():
            return None
        try:
            doc_id = f"{profile.user_id}_v{int(profile.updated_at.timestamp())}"
            text = _build_profile_text(profile)
            self._collection.upsert(
                documents=[text],
                ids=[doc_id],
                metadatas=[{
                    "user_id": profile.user_id,
                    "updated_at": profile.updated_at.isoformat(),
                }],
            )
            return doc_id
        except Exception as e:
            logger.error("RAG index_profile failed: %s", e)
            return None

    def get_context(
        self,
        user_id: str,
        condition: Optional[str] = None,
        n_results: int = 1,
    ) -> Optional[ProfileContext]:
        """
        Retrieve the user's profile context.
        Returns None if no profile found.
        """
        if not self._ensure_initialized():
            return None
        try:
            # Query using metadata filter (exact user match)
            results = self._collection.query(
                query_texts=[f"health profile {condition or 'general'} risk factors lifestyle"],
                n_results=max(n_results, 1),
                where={"user_id": user_id},
            )
            if not results["documents"] or not results["documents"][0]:
                return None

            # We have a result — we'll use the stored profile from SQLite directly
            # (RAG confirms existence; structured data comes from SQLite)
            return ProfileContext(welcome_message=f"profile_found:{user_id}")
        except Exception as e:
            logger.error("RAG get_context failed: %s", e)
            return None

    def delete_profile(self, user_id: str) -> None:
        """Remove all ChromaDB documents for a user."""
        if not self._ensure_initialized():
            return
        try:
            self._collection.delete(where={"user_id": user_id})
        except Exception as e:
            logger.error("RAG delete_profile failed: %s", e)


# Singleton
profile_rag = ProfileRAGStore()
