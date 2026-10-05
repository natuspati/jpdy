# Jeopardy contributor guide

## Stack and deployment

- `be/`: FastAPI, Python 3.14, Pydantic v2, SQLAlchemy, uv.
- `fe/`: React, strict TypeScript, Bun.
- Run the app with Docker Compose and PostgreSQL. SQLite is used only for tests.
- Redis owns live-game state and timers; Socket.IO delivers updates.
- Follow [`README.md`](README.md) for startup and Tailscale configuration.
  Public sessions require MagicDNS, HTTPS, Funnel permissions, and an auth key.
- The game-night stack uses `deployment/prod.env`, project `jpdy-prod`, and
  no demo accounts. Keep secrets and environment files untracked.
- The host may be offline between sessions; do not add automatic deployment
  without an explicit request.
- [`GAME_FLOW.md`](GAME_FLOW.md) defines the authoritative gameplay contract.

## Backend

- Use async routes, services, and SQLAlchemy sessions.
- Keep handlers thin, business logic in `services/`, queries in `repos/`, and
  validated Pydantic models in `schemas/`.
- Use `database/uow.py` for SQL commit/rollback and repository access.
  Redis transitions are atomic within Redis; SQL projections follow separately.
- Manage dependencies with `uv add`, `uv remove`, and `uv sync`.

### Database compatibility

**All queries, models, and Alembic migrations must work with both SQLite (tests) and PostgreSQL (runtime).**

- Use SQLAlchemy Core/ORM expressions, not raw SQL. If raw SQL is unavoidable,
  test it against both dialects.
- Avoid dialect-specific types (`JSONB`, `ARRAY`, `UUID`, `SERIAL`); use portable
  types such as `String`, `Integer`, and `Boolean`.
- Use SQLAlchemy expressions such as `func.now()`, `.ilike()`, and `cast()`,
  not database-specific SQL syntax.
- Generate Alembic migrations with `--autogenerate`, review before applying,
  and keep schema changes compatible with both dialects.
- Read connections from environment settings in `be/src/configs/settings.py`;
  do not hardcode a dialect.

### Linting and testing

Before pushing

If there are changes to back-end, run from `be/`:

```bash
uv run ruff format src tests
uv run ruff check --fix src tests
uv run pytest
```

If there are changes to front-end, run lints and tests.

## Frontend

- Use functional components and hooks, with `React.FC<Props>` or explicit
  return types. No `.js`/`.jsx` files or `any`; narrow `unknown` instead.
- Prefer `interface` for object shapes and `type` for unions/utilities.
  Use `satisfies` and const assertions where appropriate.
- Co-locate component types unless shared; keep components focused.
- Put API calls in service modules, not components. Use async/await, not
  `.then()` chains.

## General

- Handle async errors explicitly; do not silently swallow failures.
- Use snake_case in Python, camelCase in TypeScript, and PascalCase for classes
  and components.
- Keep credentials in gitignored environment files.
- Make one logical change per commit with a clear message.
