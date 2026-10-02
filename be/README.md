# Jeopardy backend

FastAPI, Python 3.14, SQLAlchemy, Redis, and Socket.IO; dependencies managed
with uv. Run through Docker Compose as described in [`README.md`](../README.md).
PostgreSQL is the runtime database; SQLite is used only for tests. Queries and
Alembic migrations must support both.

Compose applies migrations before startup. Only the development stack seeds
demo users and categories. See [`GAME_FLOW.md`](../GAME_FLOW.md) for gameplay
and [`AGENTS.md`](../AGENTS.md) for contributor conventions.

After changes, run from this directory:

```bash
ruff format src tests
ruff check --fix src tests
```

Do not run the integration-heavy pytest suite unless explicitly requested.
