# Jeopardy front-end

See the repository [local-play guide](../README.md) for the complete local
runtime setup, URLs, Socket.IO path, and multi-user browser workflow.

From this directory:

```bash
bun install
bun run dev
```

The Vite server runs on `http://localhost:5173` and proxies `/api` and `/ws`
to the local FastAPI server.
