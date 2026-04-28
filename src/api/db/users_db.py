"""
User Store (SQLAlchemy)
=======================
Thin wrapper over the unified `User` ORM model. Returns plain dicts so
the rest of the codebase (which was written against the old raw-sqlite3
helpers) keeps working without changes.

ON DELETE CASCADE on user_profiles / assessment_results / profile_embeddings
means `delete_user()` now wipes a user's entire data set in one statement
— no more orphaned profile rows.

Public API
----------
    init_db()
    create_user(user_id, name, email, password_hash, created_at) -> dict
    get_user_by_email(email) -> dict | None
    get_user_by_id(user_id)  -> dict | None
    update_user(user_id, **fields) -> dict | None
    delete_user(user_id) -> bool
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.exc import IntegrityError

from src.api.db.database import Base, SessionLocal, engine
from src.api.db.models import User  # noqa: F401  (registers ORM mapping)
# Import the rest so Base.metadata.create_all() picks them up.
from src.api.db.models import (  # noqa: F401
    AssessmentResult,
    ProfileEmbedding,
    UserProfile,
)


def init_db() -> None:
    """Create all tables on first boot. Safe to call repeatedly."""
    # On Postgres, ensure the pgvector extension is available before
    # CREATE TABLE runs (the embedding column references vector(384)).
    if engine.dialect.name == "postgresql":
        from sqlalchemy import text
        with engine.begin() as conn:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))

    Base.metadata.create_all(engine)


# ── Helpers ──────────────────────────────────────────────────────────────────

def _user_to_dict(u: User | None) -> dict[str, Any] | None:
    if u is None:
        return None
    return u.to_dict()


# ── CRUD ─────────────────────────────────────────────────────────────────────

def create_user(
    user_id: str,
    name: str,
    email: str,
    password_hash: str,
    created_at: str,
) -> dict:
    """Insert a new user. Raises ValueError if email already exists."""
    with SessionLocal() as session:
        user = User(
            id=user_id,
            name=name,
            email=email,
            password_hash=password_hash,
            created_at=created_at,
        )
        session.add(user)
        try:
            session.commit()
        except IntegrityError:
            session.rollback()
            raise ValueError(f"Email already registered: {email}")
        session.refresh(user)
        return _user_to_dict(user)


def get_user_by_email(email: str) -> dict | None:
    with SessionLocal() as session:
        user = session.query(User).filter(User.email == email).one_or_none()
        return _user_to_dict(user)


def get_user_by_id(user_id: str) -> dict | None:
    with SessionLocal() as session:
        user = session.get(User, user_id)
        return _user_to_dict(user)


def update_user(user_id: str, **fields) -> dict | None:
    """
    Update arbitrary user fields (name, dob, gender, height, weight,
    password_hash). Unknown field names are ignored.
    Returns the updated user dict, or None if user not found.
    """
    allowed = {"name", "dob", "gender", "height", "weight", "password_hash"}
    updates = {k: v for k, v in fields.items() if k in allowed}
    if not updates:
        return get_user_by_id(user_id)

    with SessionLocal() as session:
        user = session.get(User, user_id)
        if not user:
            return None
        for k, v in updates.items():
            setattr(user, k, v)
        session.commit()
        session.refresh(user)
        return _user_to_dict(user)


def delete_user(user_id: str) -> bool:
    """
    Delete user by ID. Returns True if a row was deleted.

    ON DELETE CASCADE on the dependent tables means this single statement
    also removes the user's profile, assessment history, and embedding row.
    """
    with SessionLocal() as session:
        user = session.get(User, user_id)
        if not user:
            return False
        session.delete(user)
        session.commit()
        return True
