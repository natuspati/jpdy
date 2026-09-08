# Jeopardy back-end

See the repository [local-play guide](../README.md) for Compose startup,
seeding, Redis, environment, migration, and database-reset instructions.
The desired server-authoritative gameplay contract is documented in
[`GAME_FLOW.md`](../GAME_FLOW.md). Gameplay uses the implemented voice-answer and answer-reveal contract described
in [`GAME_FLOW.md`](../GAME_FLOW.md).

From this directory, the development server command is:

```bash
uv run src/main.py
```

With the tracked local environment example, the API runs at
`http://localhost:8000`.

After the API is healthy, seed local users and five host-owned text categories
through the public API:

```bash
uv run ../deployment/scripts/seed_local.py
```

Before handing off back-end changes, run:

```bash
ruff format src tests
ruff check --fix src tests
```

Do not run the integration-heavy pytest suite unless explicitly requested.
