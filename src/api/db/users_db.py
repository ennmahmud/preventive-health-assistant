"""
SQLite User Store
=================
Persistent user storage backed by SQLite (stdlib sqlite3 — no extra deps).

The database file lives at PROJECT_ROOT/data/users.db and is created
automatically on first use. Thread-safe via check_same_thread=False +
a module-level lock.

Public API
----------
    init_db()
    create_user(name, email, password_hash) -> dict
    get_user_by_email(email) -> dict | None
    get_user_by_id(user_id) -> dict | None
    update_user(user_id, **fields) -> dict | None
    delete_user(user_id) -> bool
"""

import sqlite3
import threading
from pathlib import Path

_DB_PATH = Path(__file__).parent.parent.parent.parent / "data" / "users.db"
_lock = threading.Lock()


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(str(_DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Create the users table if it doesn't exist. Called once at startup."""
    _DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with _lock, _connect() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id            TEXT PRIMARY KEY,
                name          TEXT NOT NULL,
                email         TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                dob           TEXT DEFAULT '',
                gender        TEXT DEFAULT '',
                height        TEXT DEFAULT '',
                weight        TEXT DEFAULT '',
                created_at    TEXT NOT NULL
            )
        """)
        conn.commit()


def _row_to_dict(row: sqlite3.Row | None) -> dict | None:
    if row is None:
        return None
    return dict(row)


def create_user(
    user_id: str,
    name: str,
    email: str,
    password_hash: str,
    created_at: str,
) -> dict:
    """Insert a new user. Raises ValueError if email already exists."""
    with _lock, _connect() as conn:
        try:
            conn.execute(
                """
                INSERT INTO users (id, name, email, password_hash, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (user_id, name, email, password_hash, created_at),
            )
            conn.commit()
        except sqlite3.IntegrityError:
            raise ValueError(f"Email already registered: {email}")
    return get_user_by_id(user_id)


def get_user_by_email(email: str) -> dict | None:
    with _lock, _connect() as conn:
        row = conn.execute(
            "SELECT * FROM users WHERE email = ?", (email,)
        ).fetchone()
    return _row_to_dict(row)


def get_user_by_id(user_id: str) -> dict | None:
    with _lock, _connect() as conn:
        row = conn.execute(
            "SELECT * FROM users WHERE id = ?", (user_id,)
        ).fetchone()
    return _row_to_dict(row)


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

    set_clause = ", ".join(f"{k} = ?" for k in updates)
    values = list(updates.values()) + [user_id]

    with _lock, _connect() as conn:
        conn.execute(
            f"UPDATE users SET {set_clause} WHERE id = ?", values
        )
        conn.commit()

    return get_user_by_id(user_id)


def delete_user(user_id: str) -> bool:
    """Delete user by ID. Returns True if a row was deleted."""
    with _lock, _connect() as conn:
        cursor = conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
        conn.commit()
    return cursor.rowcount > 0
