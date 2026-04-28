"""
Database Engine + Session
=========================
Shared SQLAlchemy engine for the whole app. Reads DATABASE_URL from the
environment (set in docker-compose / .env). Falls back to a local SQLite
file when no URL is set so unit tests and ad-hoc scripts still run.

Anything that needs a session should call `get_session()` (FastAPI
dependency) or use `SessionLocal()` directly inside a `with` block.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

logger = logging.getLogger(__name__)

# ── Resolve database URL ─────────────────────────────────────────────────────
_PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
_SQLITE_FALLBACK = f"sqlite:///{_PROJECT_ROOT / 'data' / 'elan.db'}"

DATABASE_URL = os.getenv("DATABASE_URL", _SQLITE_FALLBACK)

# Render (and some other hosts) issue postgres:// URLs; SQLAlchemy 2 requires postgresql://
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# Make sure the SQLite parent dir exists (no-op for Postgres URLs)
if DATABASE_URL.startswith("sqlite"):
    (_PROJECT_ROOT / "data").mkdir(parents=True, exist_ok=True)

# ── Engine ───────────────────────────────────────────────────────────────────
_connect_args: dict = {}
if DATABASE_URL.startswith("sqlite"):
    # Allow connection sharing across threads (FastAPI is multi-threaded)
    _connect_args["check_same_thread"] = False

engine = create_engine(
    DATABASE_URL,
    connect_args=_connect_args,
    pool_pre_ping=True,   # Recycle stale Postgres connections automatically
    future=True,
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


# ── Declarative base ─────────────────────────────────────────────────────────
class Base(DeclarativeBase):
    """All ORM models in this app inherit from this single Base."""
    pass


# ── FastAPI dependency ───────────────────────────────────────────────────────
def get_session() -> Generator[Session, None, None]:
    """Yield a session, ensuring it's always closed."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def db_dialect() -> str:
    """Return the active dialect name ('postgresql' | 'sqlite')."""
    return engine.dialect.name


def supports_pgvector() -> bool:
    return db_dialect() == "postgresql"
