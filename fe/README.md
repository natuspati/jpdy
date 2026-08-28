# Jeopardy front-end

See the repository [local-play guide](../README.md) for the complete
Compose-based local runtime, seed data, URLs, Socket.IO path, and multi-user
browser workflow. [`GAME_FLOW.md`](../GAME_FLOW.md) defines the desired
server-authoritative voice-answer and answer-reveal experience; the current
client retains a temporary typed-answer/host-judging UI until that contract is
implemented.

From this directory:

```bash
bun install
bun run dev
```

The Vite server runs on `http://localhost:8080` and proxies REST `/api`
requests to FastAPI. Socket.IO connects directly to
`http://localhost:8000/ws`; this avoids Vite's development WebSocket proxy.
Native development uses `http://localhost:8000` as the backend target;
Compose sets `VITE_PROXY_TARGET=http://backend:8000`.
