# Jeopardy local-play guide

This repository contains a text-only Jeopardy MVP:

- `be/` — FastAPI, SQLite, Redis, Socket.IO
- `fe/` — React, TypeScript, Vite
- `deployment/` — local Redis Compose configuration

The existing JWT sign-in is only a lightweight local identity mechanism. This
setup is for local development, not production deployment.

## Prerequisites

- Docker Desktop (or Docker Engine with Compose)
- Python 3.14 and uv
- Bun

## Start the app

### 1. Start Redis

From the repository root:

```bash
docker compose -f deployment/docker-compose.local.yml up -d
docker compose -f deployment/docker-compose.local.yml ps
```

Redis listens on `localhost:6379`, persists in the named
`jpdy_redis_data` volume, and reports healthy after `redis-cli ping` works.

### 2. Configure and start the backend

```bash
cd be
cp .env.example .env
uv sync
uv run src/main.py
```

The example `.env` enables `BE_DB_APPLY_MIGRATIONS=true`, so FastAPI applies
the existing Alembic migration before serving a fresh SQLite database. The API
is available at `http://localhost:8080`; its health endpoint is
`http://localhost:8080/api/health`.

If you choose not to enable startup migrations, run this from `be/` before
starting FastAPI:

```bash
uv run alembic upgrade head
```

### 3. Start the frontend

In another terminal:

```bash
cd fe
cp .env.example .env
bun install
bun run dev
```

Open `http://localhost:5173`. Vite proxies REST requests to
`http://localhost:8080/api/v1` and Socket.IO to `http://localhost:8080/ws`.
The Socket.IO path is `/ws`; individual games use namespaces such as
`/lobbies/12`.

## Create and play a local game

1. Open the app and register a **host** account.
2. Open a separate browser profile or an incognito window and register a
   **player** account. Each local test user needs its own browser storage,
   because an account can only have one socket connection to a lobby.
3. As the host, open **Categories**, create a category, and add exactly five
   text question/answer prompts. Repeat for every category you want on the
   board.
4. Return to **Lobbies**, choose **New lobby**, and select one or more ready
   categories. Ready categories are visible to any signed-in user, while only
   the category owner can edit them.
5. In the player window, join the waiting lobby. The host starts the game,
   chooses a starting player, and judges submitted answers.
6. Continue until every clue is selected. The server marks the lobby complete
   and displays the final leaderboard.

The host is a non-scoring judge. Only joined players choose clues and accrue
points. Once the host starts play, the roster locks: existing players may
reconnect, but new users cannot join. Banned users cannot reconnect until
unbanned.

## State and answer visibility

Gameplay state is server-authoritative and replaced wholesale after each
Socket.IO update. Player frames include the board, scores, timer deadline, and
submitted answer while judging, but **never** include a clue's expected answer.
Only the host receives the `host_judging_answer` event containing the expected
answer during the judging phase. Redis retains the internal game snapshot,
including answers, for the active game.

## Reset local data

Stop the backend, then remove the local SQLite database from `be/`:

```bash
rm -f be/jpdy.db
```

To also reset running game state in Redis:

```bash
docker compose -f deployment/docker-compose.local.yml down -v
```

Start Redis and the backend again; with the example `be/.env`, Alembic will
recreate the SQLite schema automatically. Deleting the database also removes
registered local accounts and authored categories.

## MVP scope

Prompts are text-only for this version. The underlying content-type columns
remain in the database for a future media extension, but the API accepts only
`question_type=text` and `answer_type=text`, and the UI exposes only text
inputs.
