# Jeopardy back-end

See the repository [local-play guide](../README.md) for Redis, environment,
migration, startup, and database-reset instructions.

From this directory, the development server command is:

```bash
uv run src/main.py
```

Before handing off back-end changes, run:

```bash
ruff format src tests
ruff check --fix src tests
```

Do not run the integration-heavy pytest suite unless explicitly requested.
