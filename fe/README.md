# Jeopardy frontend

React, strict TypeScript, and Vite; dependencies managed with Bun.
Run through Docker Compose as described in [`README.md`](../README.md).

Nginx serves the built app and media, proxies REST at `/api/`, and Socket.IO
at `/ws/`. The client uses same-origin URLs in Compose.

## Configuration and behavior

- Compose supplies frontend build settings from the selected environment file:
  `VITE_API_URL=/api/v1`, empty `VITE_SOCKET_URL` for same-origin connections,
  and `VITE_SOCKET_PATH=/ws`.
- Render server-authoritative Socket.IO snapshots; do not maintain a parallel
  game-state machine. Keep the host's private answer key separate from public state.
- Images, audio, and video use native browser elements. Game sound is opt-in
  on every page load; media controls remain usable when autoplay is blocked.

See [`GAME_FLOW.md`](../GAME_FLOW.md) for gameplay and
[`AGENTS.md`](../AGENTS.md) for contributor conventions.
