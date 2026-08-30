# Jeopardy local-play guide

This repository contains a Jeopardy web app with text, image, audio, and
video prompts:

- `be/` — FastAPI, SQLite, Redis, Socket.IO
- `fe/` — React, TypeScript, Vite
- `deployment/` — local Compose configuration and API seed scripts

The existing JWT sign-in is only a lightweight local identity mechanism. This
setup is for local development, not production deployment.

## Game flow

[`GAME_FLOW.md`](GAME_FLOW.md) defines the server-authoritative game contract:
players answer through an external voice channel, the host judges directly,
and every resolved clue gets a short public answer-reveal period.

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

- app, REST API, Socket.IO, built assets, and uploaded media at `http://localhost:8080`
- backend, Redis, SQLite, and media storage remain private Compose services

Nginx is sole browser entry point. It serves built React `/assets/`, immutable
uploaded `/media/` files, SPA routes, and proxies `/api/` plus Socket.IO
`/ws/` to FastAPI. FastAPI validates uploads but does not serve media bytes.
Redis persists in `jpdy_redis_data`, SQLite in `jpdy_backend_data`, and
uploaded prompt media in `jpdy_media_data`.

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
5. In the player windows, join the waiting lobby. The host starts the game
   and chooses a starting player. Players answer through the agreed voice
   channel; the host judges each spoken response directly.
6. Continue until every clue is selected. The server marks the lobby complete
   and displays the final leaderboard.

The host is a non-scoring judge. Only joined players choose clues and accrue
points. Once the host starts play, the roster locks: existing players may
reconnect, but new users cannot join. Banned users cannot reconnect until
unbanned.

## Prompt media and sound

- Category owners can set question and answer-reveal types independently:
  text, image, audio, or video.
- Every prompt still requires canonical answer text. It remains host-private
  during an active clue and becomes public during answer reveal.
- Uploaded bytes are validated before storage. Supported formats: JPEG/PNG/WebP
  images up to 10 MB; MP3/M4A/AAC/Ogg audio up to 20 MB; MP4 video up to 100 MB.
- Nginx serves immutable assets at same-origin `/media/{key}` URLs. Do not put
  uploaded files in the database or link arbitrary external URLs.
- Game sound starts disabled for every page load. Each browser user enables it
  independently, then has one **Game volume** control.

## State and answer visibility

Gameplay state is server-authoritative and replaced wholesale after each
Socket.IO update. Redis retains the internal game snapshot, including prompt
answers, for the active game.

Visibility rules are specified in [`GAME_FLOW.md`](GAME_FLOW.md):

- players answer through voice software; their answer text is never sent to
  the application;
- only the host sees an expected answer while a clue is active;
- no player receives the expected answer before the host resolves the clue;
- the correct answer becomes public only during the short `answer_reveal`
  phase after resolution.

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

The example backend environment enables startup migrations. Native Vite
development uses `VITE_SOCKET_URL=http://localhost:8000`; Compose leaves it
empty so clients use same-origin Nginx.

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

## Current scope

Prompt questions and answer reveals each support text, image, audio, or video.
Every prompt still requires canonical question and expected-answer text for
instructions, host judgment, and the public reveal. See
[`GAME_FLOW.md`](GAME_FLOW.md) for gameplay, visibility, media, timer, and
sound-cue contracts.
