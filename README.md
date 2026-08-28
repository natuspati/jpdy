# Jeopardy local-play guide

This repository contains a text-only Jeopardy MVP:

- `be/` — FastAPI, SQLite, Redis, Socket.IO
- `fe/` — React, TypeScript, Vite
- `deployment/` — local Compose configuration and API seed scripts

The existing JWT sign-in is only a lightweight local identity mechanism. This
setup is for local development, not production deployment.

## Prerequisites

- Docker Engine with Compose (Colima is supported; Docker Desktop is not required)
- Python 3.14 and uv
- Bun

## Start the app

### 1. Start the complete local stack

From the repository root:

```bash
docker-compose -f deployment/docker-compose.local.yml up --build -d
docker-compose -f deployment/docker-compose.local.yml ps
```

This guide uses the hyphenated `docker-compose` command because it works with
the local Colima setup. If your Docker CLI has the Compose v2 plugin, use
`docker compose` in place of `docker-compose`.

This starts every local runtime dependency:

- frontend at `http://localhost:8080`
- backend at `http://localhost:8000`
- backend health endpoint at `http://localhost:8000/api/health`
- Redis at `localhost:6379`

The backend waits for Redis, applies Alembic migrations to its named SQLite
volume, and exposes a health check. The frontend waits for that health check
and proxies REST `/api` requests to the backend. Socket.IO connects directly
to `http://localhost:8000` on its `/ws` path, avoiding the Vite development
server's WebSocket proxy. Redis persists in `jpdy_redis_data`; SQLite persists
in `jpdy_backend_data`.

### 2. Seed local users and categories

After `docker-compose ... ps` reports the backend as healthy, run the seed
script through the backend's local uv environment:

```bash
cd be
uv sync
uv run ../deployment/scripts/seed_local.py
```

The script calls only the running API; it does not access the database
directly, and it refuses to run until the API health endpoint responds.
Re-running it is safe: it keeps the four fixed users and reconciles five
host-owned categories to their 25 text prompts. It never creates a lobby or
game.

Seeded credentials are:

- host: `host` / `host123`
- players: `alice` / `alice123`, `bob` / `bob123`, and `carol` / `carol123`

The API currently has a six-character password minimum, hence the `123`
suffixes. It has a single `username` field, so `alice`, `bob`, and `carol`
are also the display identities shown in the app.

### 3. Create and play a local game

1. Open `http://localhost:8080` and sign in as the seeded **host**.
2. Open three separate browser profiles or incognito windows and sign in as
   the seeded **players**. Each local test user needs its own browser storage,
   because an account can only have one socket connection to a lobby.
3. The host already owns five ready categories—**Space**, **Felids**, **World
   Capitals**, **Science Basics**, and **Classic Literature**—with exactly five
   text prompts each.
4. As the host, return to **Lobbies**, choose **New lobby**, and select one or more ready
   categories. Ready categories are visible to any signed-in user, while only
   the category owner can edit them.
5. In the player windows, join the waiting lobby. The host starts the game,
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

## Native development (without Compose)

If you prefer running FastAPI and Vite directly, start Redis only:

```bash
docker-compose -f deployment/docker-compose.local.yml up -d redis
```

Then configure and run the backend:

```bash
cd be
cp .env.example .env
uv sync
uv run src/main.py
```

In a second terminal, configure and run the frontend:

```bash
cd fe
cp .env.example .env
bun install
bun run dev
```

The example backend environment enables startup migrations. The frontend's
`VITE_PROXY_TARGET` defaults to `http://localhost:8000`, while Compose
overrides it with the internal backend service address.

## Reset local data

To reset all Compose-managed state (SQLite and Redis):

```bash
docker-compose -f deployment/docker-compose.local.yml down -v
```

Then use the complete-stack command and seed command above to recreate a clean
local instance.

For native development, stop the backend and remove the local SQLite database
from `be/`:

```bash
rm -f be/jpdy.db
```

To also reset native Redis game state:

```bash
docker-compose -f deployment/docker-compose.local.yml down -v
```

Start Redis and the backend again; with the example `be/.env`, Alembic will
recreate the SQLite schema automatically. Deleting the database also removes
registered local accounts and authored categories.

## MVP scope

Prompts are text-only for this version. The underlying content-type columns
remain in the database for a future media extension, but the API accepts only
`question_type=text` and `answer_type=text`, and the UI exposes only text
inputs.
