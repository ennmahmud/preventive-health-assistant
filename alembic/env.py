"""
Alembic environment configuration.

Loads DATABASE_URL from .env (same as the FastAPI app), wires the
shared `Base.metadata` so autogenerate works, and ensures the pgvector
extension is created before any vector columns are referenced.
"""

from __future__ import annotations

import os
import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from dotenv import load_dotenv
from sqlalchemy import engine_from_config, pool, text

# ── Make src/ importable ─────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# ── Load .env so DATABASE_URL is available ───────────────────────────────────
load_dotenv(PROJECT_ROOT / ".env", override=False)

# ── Import the unified ORM so Base.metadata sees every table ─────────────────
from src.api.db.database import Base, DATABASE_URL  # noqa: E402
import src.api.db.models  # noqa: F401, E402  (registers all mappings)

# Alembic Config object
config = context.config

# Inject the runtime DATABASE_URL — overrides the placeholder in alembic.ini
config.set_main_option("sqlalchemy.url", DATABASE_URL)

# Logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def _ensure_pgvector(connection) -> None:
    """Make sure the vector extension exists before applying migrations."""
    if connection.dialect.name == "postgresql":
        connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))


def run_migrations_offline() -> None:
    """Generate SQL without a live connection."""
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Apply migrations against a live database connection."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        _ensure_pgvector(connection)
        connection.commit()

        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
