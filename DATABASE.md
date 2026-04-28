# Database — Tier 2 architecture

A single Postgres database (with the `pgvector` extension) holds every
piece of relational state in the app.

## Schema

| Table                | Notes                                                  |
| -------------------- | ------------------------------------------------------ |
| `users`              | Account credentials + basic demographics               |
| `user_profiles`      | One health profile per user (FK → users)               |
| `assessment_results` | Every completed assessment (FK → users)                |
| `profile_embeddings` | RAG vector(384) per user (FK → users)                  |

All foreign keys use `ON DELETE CASCADE`, so deleting a row in `users`
wipes the user's profile, history, and embedding in one transaction.
JSON blobs (`raw_result`, `lifestyle_inputs`, `symptom_flags`) are
stored as `JSONB` on Postgres for indexable querying.

## Local development

The simplest path is docker-compose, which boots Postgres alongside the
app:

```bash
cp .env.example .env
docker compose --profile dev up
```

The `backend-dev` service runs `alembic upgrade head` before starting
uvicorn, so the schema is created automatically on first boot.

If you need to run migrations by hand:

```bash
# inside the backend container, or with a venv that has the requirements installed
alembic upgrade head           # apply all pending migrations
alembic revision --autogenerate -m "describe change"   # generate a new revision
alembic downgrade -1           # roll back one revision
```

## Running without Docker

If `DATABASE_URL` is not set, the app falls back to a SQLite file at
`data/elan.db`. This is fine for unit tests and ad-hoc scripts but
disables the pgvector embedding column (it falls back to a JSON list).

## Migrating from the old SQLite files

The previous architecture used two separate SQLite files
(`data/users.db` + `data/profiles/profiles.db`) accessed through
different drivers. Tier 2 replaces both with a single Postgres
database. There is no automatic data migration — the upgrade path is
to start with a clean Postgres volume and re-create accounts.
