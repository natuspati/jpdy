# Jeopardy backend

FastAPI, Python 3.14, SQLAlchemy, Redis, and Socket.IO; dependencies managed
with uv. Run through Docker Compose as described in [`README.md`](../README.md).
PostgreSQL is the runtime database; SQLite is used only for tests. Queries and
Alembic migrations must support both.

Compose applies migrations before startup. Only the development stack seeds
demo users and categories. See [`GAME_FLOW.md`](../GAME_FLOW.md) for gameplay
and [`AGENTS.md`](../AGENTS.md) for contributor conventions.

## Runtime and configuration

- PostgreSQL stores accounts, categories, lobby setup, and completion projections.
  Redis owns live-game state and timers.
- Configure the development stack in `deployment/local.env`; public-session
  configuration is documented in the root [deployment guide](../README.md#deployment).
  Always pass the appropriate `--env-file` to Compose.
- PostgreSQL (`localhost:5432`) and Redis (`localhost:6379`) are available for
  IDE access. The backend is private to Compose; use Nginx for browser requests.
- `BE_ALLOWED_HOSTS` must match browser origins, including ports.
- Database, Redis state, and uploads persist in Docker volumes. FastAPI validates
  uploaded bytes; Nginx serves files from a read-only media mount.
- To check shared Socket.IO delivery, set `BE_WORKERS_COUNT=2` in
  `deployment/local.env` and rerun Compose startup. `BE_SOCKETIO_REDIS_URL`
  is already configured. Check reconnects, host-private answers, bans, timers,
  and completion; restore `BE_WORKERS_COUNT=1` afterwards.

## Checks

After changes, run from this directory:

```bash
ruff format src tests
ruff check --fix src tests
```

Do not run the integration-heavy pytest suite unless explicitly requested.
