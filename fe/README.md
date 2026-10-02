# Jeopardy frontend

React, strict TypeScript, and Vite; dependencies managed with Bun.
Run through Docker Compose as described in [`README.md`](../README.md).

Nginx serves the built app and media, proxies REST at `/api/`, and Socket.IO
at `/ws/`. The client uses same-origin URLs in Compose.

See [`GAME_FLOW.md`](../GAME_FLOW.md) for gameplay and
[`AGENTS.md`](../AGENTS.md) for contributor conventions.
