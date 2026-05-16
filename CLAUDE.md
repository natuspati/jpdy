# Jeopardy Web App

## Project Overview

Hobby project: a Jeopardy game implemented as a full-stack web application.

```
root/
├── be/        # FastAPI back-end (Python 3.14, uv)
└── fe/        # React front-end (TypeScript)
```

---

## Back-End (`be/`)

### Stack

- **Runtime:** Python 3.14
- **Framework:** FastAPI
- **Database:** SQLite (local dev) / PostgreSQL (cloud/production)
- **Redis:** For storing active stage of running Jeopardy games
- **SIO:** For managing events in websockets
- **Dependency manager:** `uv`

### Running the dev server

```bash
uv run src/main.py --reload
```

### Dependency management

```bash
uv add <package>        # add a dependency
uv remove <package>     # remove a dependency
uv sync                 # install all deps from lockfile
```

### After every set of changes — always run:

```bash
ruff format src tests
ruff check --fix src tests
```

Run both commands in this exact order before considering any task complete.

### Database compatibility (SQLite + PostgreSQL)

All queries and models **must work on both** SQLite (local) and PostgreSQL (cloud). Follow these rules at all times:

- **ORM only:** Use SQLAlchemy Core or ORM expressions. Never write raw SQL strings unless absolutely unavoidable, and
  if you do, test against both dialects.
- **No database-specific types:** Avoid `JSONB`, `ARRAY`, `UUID` (use `String` instead), `SERIAL` (use `Integer` with
  `autoincrement=True`).
- **No database-specific functions:** Avoid `NOW()`, `ILIKE`, `::cast` syntax. Use SQLAlchemy's `func.now()`, `ilike()`
  method, and `cast()`.
- **Booleans:** Use SQLAlchemy `Boolean` type — SQLite stores as 0/1, Postgres as native bool; SQLAlchemy handles the
  mapping.
- **Migrations:** Use Alembic. Always generate migrations with `--autogenerate` and review them before applying.
- **Connection strings:** Injected via environment with defaults specified in `be/src/configs/settings.py`.
  The app must detect the dialect at runtime - do not hardcode either dialect.

### Code conventions

- Use `async`/`await` throughout (async SQLAlchemy sessions, async FastAPI routes).
- Pydantic v2 for all request/response schemas.
- Keep route handlers thin — business logic goes in a `services/` layer.
- Keep query logic in a `repos/` layer, separate from business logic, preferably return
  validated Pydantic models (schemas) defined in `schemas/` rather than raw SQLAlchemy models.
- Use Unit of Work convention to make operations with database and redis atomic in `datbases/own.py`.

---

## Front-End (`fe/`)

### Stack

- **Framework:** React
- **Language:** Modern TypeScript only — no `.js`/`.jsx` files
- **Node package manager:** npm

### Running the dev server

```bash
cd fe
npm run dev
```

### TypeScript conventions

- Strict mode enabled (`"strict": true` in `tsconfig.json`).
- No `any` — use `unknown` and narrow, or define proper types/interfaces.
- Prefer `interface` for object shapes, `type` for unions and utility types.
- All React components as typed function components: `const Foo: React.FC<Props> = ...` or explicit return-type
  annotations.
- Use `const` assertions and `satisfies` where appropriate.
- Co-locate component types in the same file unless shared across multiple files.

### Code conventions

- Functional components only — no class components.
- Use React hooks; keep components focused and composable.
- API calls go in dedicated service modules (e.g. `src/api/`), not inline in components.
- Use `async`/`await`, not `.then()` chains.

---

## General Guidelines

- **Commit hygiene:** One logical change per commit with a clear message.
- **No secrets in source:** All credentials and environment-specific values in `.env` files (gitignored).
- **Error handling:** All async operations (both BE and FE) must handle errors explicitly — no silent swallowing.
- **Naming:** snake_case for Python, camelCase for TypeScript variables/functions, PascalCase for components and classes
  everywhere.
