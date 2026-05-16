# Front-end Implementation Plan

End-to-end plan for the `fe/` React + TypeScript app that talks to the FastAPI
back-end (REST for setup/discovery, Socket.IO for game flow). Pairs with
[`GAME_FLOW.md`](../GAME_FLOW.md) at the repo root.

---

## 1. Stack & tooling

| Concern              | Choice                                                                   |
| -------------------- | ------------------------------------------------------------------------ |
| Package manager      | **bun** (`bun add`, `bunx`, `bun test`)                                  |
| Build / dev server   | **Vite** (`vite`, `@vitejs/plugin-react`)                                |
| Language             | TypeScript strict mode, no `.js`/`.jsx`                                  |
| UI framework         | React 18, function components + hooks                                    |
| Styling              | **Tailwind CSS v4** with `@tailwindcss/vite` plugin                      |
| Routing              | **React Router v6** (data-router APIs)                                   |
| REST cache           | **@tanstack/react-query**                                                |
| HTTP client          | thin `fetch` wrapper in `src/api/http.ts` (auth token injection, errors) |
| Sockets              | **socket.io-client** (matches back-end `python-socketio`)                |
| Global / auth state  | **Zustand** (auth token + current user, persisted to `localStorage`)     |
| Validation           | **zod** — single source of truth for forms *and* server payloads          |
| Forms                | `react-hook-form` + `@hookform/resolvers/zod`                            |
| Unit tests           | **Vitest** + **@testing-library/react** + `jsdom`                        |
| Lint / format        | ESLint (typescript-eslint, react-hooks) + Prettier                       |

No component library — we use Tailwind primitives plus a small `components/ui/`
folder for `Button`, `Input`, `Card`, `Modal`, `Spinner`, `Badge`, `Toast`.

---

## 2. Top-level directory layout

```
fe/
├── index.html
├── package.json
├── bun.lockb
├── tsconfig.json
├── vite.config.ts
├── tailwind.config.ts
├── postcss.config.js
├── .eslintrc.cjs
├── .prettierrc
├── .env.example                  # VITE_API_URL, VITE_SOCKET_URL, VITE_MEDIA_URL
└── src/
    ├── main.tsx                  # React root, QueryClientProvider, router
    ├── App.tsx                   # Route definitions
    ├── router.tsx                # Routes + auth guards
    │
    ├── config/
    │   └── env.ts                # Typed accessor for VITE_* env vars
    │
    ├── schemas/                  # zod schemas — single source of truth; TS types derived via z.infer
    │   ├── enums.ts              # z.nativeEnum or z.enum for LobbyState, GamePhase, ConnectionStatus, QuestionType, AnswerType
    │   ├── user.ts               # UserPublic, UserCreate, TokenSchema, MeResponse
    │   ├── lobby.ts              # LobbyInDB, LobbyCreate, LobbyUpdate, LobbyFilter, LobbyWithCategories, paginated wrapper
    │   ├── prompt.ts             # PromptInDB, PromptCreate, PromptUpdate, PromptCategory*, paginated wrapper
    │   ├── game.ts               # GameHostState, GamePlayerState, GamePromptState, GameCategoryState, GameLobbyState
    │   ├── socketEvents.ts       # Client→server payload schemas + server→client error payload schema
    │   ├── error.ts              # BE ErrorResponse shape ({ detail: ..., code? ... })
    │   └── pagination.ts         # Generic paginated<T>(item: z.ZodTypeAny)
    │
    ├── api/
    │   ├── http.ts               # fetch wrapper: base URL, auth header, JSON, error mapping;
    │   │                         #   takes a zod schema and validates the response (`.parse`)
    │   ├── errors.ts             # ApiError class + parser for BE ErrorResponse via zod
    │   ├── auth.ts               # signIn(), register(), me()  — each call validates response with zod
    │   ├── lobbies.ts            # list/get/create/patch/delete + searchLobbies(filters)
    │   ├── categories.ts         # list/get/create/patch/delete + prompts CRUD
    │   └── queryKeys.ts          # Centralized TanStack Query keys (typed factory)
    │
    ├── sockets/
    │   ├── client.ts             # createLobbySocket(lobbyId, token) → typed Socket
    │   ├── events.ts             # Event name constants + emit helpers; emit() validates payload with zod first
    │   ├── types.ts              # ServerToClientEvents / ClientToServerEvents (derived from zod schemas)
    │   └── parseIncoming.ts      # Wrap raw `state_changed`/`error` payloads in zod safeParse before surfacing
    │
    ├── store/
    │   ├── authStore.ts          # Zustand: token, user, signIn(), signOut(); persisted
    │   └── toastStore.ts         # Zustand: enqueue/dismiss; tiny app-wide toaster
    │
    ├── hooks/
    │   ├── useAuth.ts            # Convenience selector over authStore
    │   ├── useMe.ts              # TanStack Query → GET /user/me, gated on token
    │   ├── useLobbies.ts         # Search lobbies, paginated
    │   ├── useLobby.ts           # GET /lobby/{id}
    │   ├── useCreateLobby.ts     # POST /lobby
    │   ├── useUpdateLobby.ts     # PATCH /lobby/{id}
    │   ├── useDeleteLobby.ts     # DELETE /lobby/{id}
    │   ├── usePromptCategories.ts# Search categories
    │   ├── useCategoryMutations.ts# create/update/delete category
    │   ├── usePromptMutations.ts # create/update/delete prompt
    │   ├── useLobbySocket.ts     # Builds socket, subscribes to state_changed/error
    │   ├── useGameState.ts       # Selects/derives view-model slices from GameLobbyState
    │   ├── useCountdown.ts       # timer_deadline → remaining seconds (rAF based)
    │   └── useMediaQuery.ts      # Tailwind breakpoints for layout decisions
    │
    ├── services/
    │   ├── auth/
    │   │   └── tokenStorage.ts   # Token read/write + JWT exp check
    │   ├── game/
    │   │   ├── gameDerivations.ts# Pure helpers: isHost(), canSelectPrompt(), eligibleBuzzers()
    │   │   ├── roleFor.ts        # Returns 'host' | 'selector' | 'answerer' | 'buzzer' | 'spectator'
    │   │   └── phaseGuards.ts    # Phase-based predicates used by views
    │   └── media/
    │       └── assetUrl.ts       # Joins VITE_MEDIA_URL with file path served by nginx
    │
    ├── components/
    │   ├── ui/                   # Button, Input, Card, Modal, Spinner, Badge, FieldError, Toast
    │   ├── layout/
    │   │   ├── AppShell.tsx      # Header + main + toaster; mobile-aware
    │   │   ├── TopBar.tsx        # Logo + username + sign-out button
    │   │   └── MobileNav.tsx     # Hamburger nav for narrow screens
    │   ├── auth/
    │   │   ├── SignInForm.tsx
    │   │   └── RegisterForm.tsx
    │   ├── lobby/
    │   │   ├── LobbyList.tsx     # Browseable joinable lobbies
    │   │   ├── LobbyCard.tsx     # Single lobby row with Join button
    │   │   ├── CreateLobbyModal.tsx
    │   │   └── LobbySetupPanel.tsx# For owner: pick categories, promote to waiting_start
    │   ├── categories/
    │   │   ├── CategoryList.tsx
    │   │   ├── CategoryEditor.tsx
    │   │   ├── PromptEditor.tsx
    │   │   └── MediaUploadField.tsx # File picker → POST to nginx-backed endpoint (stub)
    │   └── game/
    │       ├── GameBoard.tsx     # Categories × prompts grid (rendered for everyone)
    │       ├── PromptCell.tsx    # Score tile; greyed if is_selected
    │       ├── PromptStage.tsx   # Fullscreen prompt view during PLAYER_ANSWERING/BUZZ_OPEN
    │       ├── AnswerInput.tsx   # Answering player's text/buzz input
    │       ├── BuzzButton.tsx    # Large mobile-friendly button during BUZZ_OPEN
    │       ├── HostJudgePanel.tsx# Correct/Wrong buttons during HOST_JUDGING_ANSWER
    │       ├── HostControls.tsx  # Ban/unban, start game, select starter pickers
    │       ├── ScoreBoard.tsx    # Players + scores; highlights selector/answerer
    │       ├── TimerBar.tsx      # Visual countdown bound to timer_deadline
    │       ├── PhaseBanner.tsx   # "Waiting for host…", "Pick a prompt", etc.
    │       ├── ConnectionPill.tsx# Player connection status dot
    │       ├── FinalLeaderboard.tsx
    │       └── MediaRenderer.tsx # Switches by question_type/answer_type (text/image/audio/video)
    │
    ├── pages/
    │   ├── HomePage.tsx          # Unauth → SignInForm + Register link; Auth → LobbyList + create CTAs
    │   ├── RegisterPage.tsx
    │   ├── CategoriesPage.tsx    # Manage own prompt categories
    │   ├── CategoryEditPage.tsx  # /categories/:id
    │   ├── LobbyPage.tsx         # /lobby/:id — opens socket, renders role-aware view
    │   └── NotFoundPage.tsx
    │
    ├── styles/
    │   └── index.css             # Tailwind directives + 1-2 globals
    │
    └── test/
        ├── setup.ts              # Vitest setup: jsdom, RTL matchers, msw server reset
        ├── mocks/
        │   ├── server.ts         # msw setup for REST
        │   ├── handlers.ts       # Default REST handlers
        │   └── socket.ts         # Mock socket.io-client (vi.mock factory)
        └── fixtures/
            ├── gameState.ts      # Builders for GameLobbyState in various phases
            └── lobbies.ts        # Builders for lobby/category fixtures
```

---

## 3. Validation with zod (user input *and* server payloads)

zod is the **single source of truth** for the shape of any data that crosses
a boundary — both directions. We never hand-write TypeScript interfaces for
those boundaries; types are derived from schemas:

```ts
export const LobbyInDB = z.object({
  id: z.number().int(),
  owner_id: z.number().int().nullable(),
  state: LobbyStateEnum,
  created_at: z.string().datetime(),
  updated_at: z.string().datetime(),
});
export type LobbyInDB = z.infer<typeof LobbyInDB>;
```

### Where validation runs

| Boundary                          | Schema                       | Behavior on failure                                |
| --------------------------------- | ---------------------------- | -------------------------------------------------- |
| User → form (sign-in, create lobby, prompt, ban…) | per-form `*FormSchema`       | `react-hook-form` shows field-level error          |
| Form → REST request body          | `*CreateSchema` / `*UpdateSchema` | parse before send; throw `ApiError` if invalid |
| REST response                     | per-endpoint response schema | log + throw `ApiError("invalid_response", issues)` so TanStack Query surfaces it as a toast and does NOT cache garbage |
| Socket `state_changed` incoming   | `GameLobbyState`             | log + drop the frame, surface a toast; previous state remains  |
| Socket `error` incoming           | `SocketErrorPayload`         | fallback to generic error toast if shape mismatches |
| Socket emit payload               | `Select*Payload`, etc.       | refuse to emit; show toast (defensive — UI shouldn't allow it) |

### Why validate the server too

- Catches BE/FE schema drift the moment it happens — far easier to debug than
  a `TypeError: cannot read property of undefined` 4 components deep.
- Lets us safely use `as` nowhere: the validated value is the typed value.
- Keeps zod schemas mirrored against `be/src/schemas/`. A short README in
  `src/schemas/` calls out the mapping (one zod file per BE schema folder).

### Helpers

```ts
// api/http.ts (excerpt)
async function request<TSchema extends z.ZodTypeAny>(
  path: string,
  init: RequestInit,
  responseSchema: TSchema,
): Promise<z.infer<TSchema>> {
  const res = await fetch(...);
  if (!res.ok) throw await ApiError.fromResponse(res);
  const json = await res.json();
  const parsed = responseSchema.safeParse(json);
  if (!parsed.success) {
    console.error('Schema mismatch', { path, issues: parsed.error.issues });
    throw new ApiError('invalid_response', 'Unexpected response shape');
  }
  return parsed.data;
}
```

```ts
// sockets/parseIncoming.ts (excerpt)
export function onStateChanged(socket: Socket, cb: (s: GameLobbyState) => void) {
  socket.on('state_changed', (raw) => {
    const parsed = GameLobbyState.safeParse(raw);
    if (!parsed.success) {
      console.error('Bad state_changed', parsed.error.issues);
      toastStore.push({ kind: 'error', text: 'Received invalid game state' });
      return;
    }
    cb(parsed.data);
  });
}
```

---

## 5. Routing

React Router v6 with a tiny `RequireAuth` wrapper that redirects unauthenticated
users to `/`.

| Path              | Page                | Auth | Notes                                                              |
| ----------------- | ------------------- | ---- | ------------------------------------------------------------------ |
| `/`               | `HomePage`          | —    | Shows `SignInForm` if no token; otherwise lobby list + CTAs        |
| `/register`       | `RegisterPage`      | —    | Form → POST /user/register → auto sign-in → `/`                    |
| `/categories`     | `CategoriesPage`    | yes  | List + create category modal                                       |
| `/categories/:id` | `CategoryEditPage`  | yes  | Edit name, reorder prompts, add/edit/delete prompts                |
| `/lobby/:id`      | `LobbyPage`         | yes  | Opens namespace `/lobbies/:id`; renders role-aware game UI         |
| `*`               | `NotFoundPage`      | —    | 404                                                                |

Hash/scroll: default. No nested data routers needed.

---

## 6. Auth flow

1. Sign-in form → `POST /api/v1/user/sign-in` with `application/x-www-form-urlencoded`
   (OAuth2PasswordRequestForm on BE).
2. Receive `{ access_token, token_type }`. Persist token + decoded `sub`/`exp`
   into `authStore` (persisted to localStorage).
3. `useMe` fetches `/user/me` once token is present; result feeds `username` in
   `TopBar`. If `me` returns 401, clear token and route to `/`.
4. Sign-out: clear authStore + `queryClient.clear()` and navigate to `/`.

`api/http.ts` reads the token from `authStore.getState()` (not a hook — avoids
the React-only access constraint) and attaches `Authorization: Bearer …` to
every request. Any 401 response also clears the store.

JWT lifetime is 24h (BE default). Optional improvement: pre-emptively log out
when `exp - now < 60s`; out of scope for v1 but the hook structure supports it.

---

## 7. Socket layer

### Client creation

```ts
// sockets/client.ts
export function createLobbySocket(lobbyId: number, token: string): Socket<S2C, C2S> {
  const url = env.SOCKET_URL;
  return io(`${url}/lobbies/${lobbyId}`, {
    path: '/ws',
    transports: ['websocket'],
    query: { token },
    autoConnect: false,
  });
}
```

### Typed events

```ts
// sockets/types.ts
export interface ServerToClientEvents {
  state_changed: (state: GameLobbyState) => void;
  error: (payload: SocketErrorPayload) => void;
}
export interface ClientToServerEvents {
  start_game: () => void;
  select_starter: (p: { user_id: number }) => void;
  select_prompt: (p: { prompt_id: number }) => void;
  submit_answer: (p: { text: string }) => void;
  judge_answer: (p: { correct: boolean }) => void;
  buzz: () => void;
  ban_player: (p: { user_id: number }) => void;
  unban_player: (p: { user_id: number }) => void;
}
```

### `useLobbySocket(lobbyId)`

Single React hook that owns the lifecycle:

- Builds socket on mount, connects, and:
  - Stores latest `GameLobbyState` in local React state.
  - Pipes `error` events to the toast store with a friendly message.
  - Surfaces a `connectionStatus` flag (`connecting | open | closed | failed`).
- Returns `{ state, emit, connectionStatus }` where `emit` is a typed function
  bound to the right namespace.
- Cleans up on unmount: `socket.disconnect()`. Also disconnects if the lobby
  ID in the URL changes.

State is **fully server-authoritative**, as `GAME_FLOW.md` calls out — every
`state_changed` simply replaces the prior snapshot. No client-side FSM.

---

## 8. Game UI architecture

### Role resolution

```ts
type Role = 'host' | 'selector' | 'answerer' | 'buzzer' | 'spectator' | 'banned';

roleFor(state: GameLobbyState, userId: number): Role
```

This single pure function decides which sub-component the page renders within
`PromptStage` / `HostControls`. Avoids `if (isHost && phase === …)` ladders in
JSX.

### `LobbyPage` layout

```
┌─────────────────────────────────────────────┐
│ TopBar                                      │
├─────────────────────────────────────────────┤
│ PhaseBanner                                 │
│ ┌──────────────────┐ ┌────────────────────┐ │
│ │ GameBoard        │ │ ScoreBoard         │ │
│ │ (cat × prompts)  │ │ TimerBar           │ │
│ │                  │ │ HostControls/      │ │
│ │                  │ │ PromptStage/       │ │
│ │                  │ │ BuzzButton/        │ │
│ │                  │ │ HostJudgePanel     │ │
│ └──────────────────┘ └────────────────────┘ │
└─────────────────────────────────────────────┘
```

On mobile (`< md`): the board and the side panel stack vertically; the
`PromptStage` becomes a fixed overlay so the active prompt fills the viewport,
and the `BuzzButton` is a sticky bottom-of-screen full-width bar.

### Phase → primary control mapping

| Phase                              | Host UI                                  | Selector UI               | Answerer UI            | Other players UI       |
| ---------------------------------- | ---------------------------------------- | ------------------------- | ---------------------- | ---------------------- |
| `WAITING_FOR_PLAYERS`              | `HostControls` (Start, ban list)         | "Waiting for host…"       | n/a                    | "Waiting for host…"    |
| `HOST_SELECTING_STARTING_PLAYER`   | `HostControls` (pick player)             | n/a                       | n/a                    | "Host is choosing…"    |
| `PLAYER_SELECTING_PROMPT`          | Spectate                                 | `GameBoard` prompts clickable | Spectate           | Spectate               |
| `PLAYER_ANSWERING`                 | Spectate prompt                          | n/a                       | `AnswerInput`          | Spectate               |
| `HOST_JUDGING_ANSWER`              | `HostJudgePanel` (Correct/Wrong)         | n/a                       | Spectate               | Spectate               |
| `BUZZ_OPEN`                        | Spectate                                 | n/a                       | n/a                    | `BuzzButton` (eligible)|
| `FINISHED`                         | `FinalLeaderboard`                       | `FinalLeaderboard`        | `FinalLeaderboard`     | `FinalLeaderboard`     |

Host **auto-joins** a lobby right after promoting it to `waiting_start`:
`useUpdateLobby` `onSuccess` runs `navigate('/lobby/{id}')`. The socket
connection on the lobby page is what flips `host.connection_status` to
`connected` server-side.

### Timers

`useCountdown(deadlineIso)` computes `remaining = max(0, deadline - now)` and
re-renders ~5 times/sec via `requestAnimationFrame`. `TimerBar` renders a
shrinking bar + numeric seconds. Per `GAME_FLOW.md`, the server owns expiry —
the client never sends an "expired" event.

### Mobile-first specifics

- Tailwind `md`/`lg` breakpoints used to switch board grid from `grid-cols-1`
  to `grid-cols-N` where N = `categories.length`.
- All interactive elements meet a 44×44 px tap target.
- `BuzzButton` and `AnswerInput` get a `sticky bottom-0` treatment on mobile.
- Use `text-[clamp(...)]` so prompt question/answer scales with viewport.

---

## 9. Media handling

`question_type` / `answer_type` ∈ `text | image | audio | video` (BE enum).
`MediaRenderer` switches:

```tsx
switch (type) {
  case 'text':  return <p>{value}</p>;
  case 'image': return <img src={assetUrl(value)} alt="" />;
  case 'audio': return <audio controls src={assetUrl(value)} />;
  case 'video': return <video controls src={assetUrl(value)} />;
}
```

`assetUrl(path)` joins `VITE_MEDIA_URL` with the file path returned by the BE.
Upload is **out of scope for v1** — `MediaUploadField` ships as a typed `<input
type="file">` stub that POSTs to a placeholder endpoint we'll wire up when the
nginx upload route exists.

---

## 10. Error handling & UX

- All REST mutations: errors caught by TanStack Query's `onError`, pushed to
  `toastStore`. ApiError carries the BE's `detail` field for display.
- Socket `error` event → toast with the `detail` from `SocketErrorPayload`.
- Socket connection failure (bad token, missing lobby, banned, etc.) →
  navigate back to `/` and show a toast.
- Form errors via `react-hook-form` + `zod`; field-level messages render via
  `<FieldError>`.

---

## 11. Testing strategy

### Tooling

- **Vitest** for runner.
- **@testing-library/react** for component tests.
- **msw** for mocking REST.
- **vi.mock('socket.io-client')** with a small `MockSocket` that lets tests
  push `state_changed` snapshots and assert which events the component emitted.

### Coverage targets (unit only — no E2E in v1)

| Area                     | Tests                                                                                       |
| ------------------------ | ------------------------------------------------------------------------------------------- |
| `api/http.ts`            | attaches bearer token, parses ApiError, clears auth on 401, **throws on response shape mismatch** |
| `schemas/*`              | round-trip: known-good JSON parses; known-bad JSON fails with expected issues               |
| `sockets/parseIncoming`  | bad `state_changed` drops + toasts; good `state_changed` reaches the callback               |
| `store/authStore`        | sign-in stores token, sign-out clears, persists to/from localStorage                        |
| `services/game/roleFor`  | one test per (phase, role) cell of the table above                                          |
| `services/game/phaseGuards` | canSelectPrompt, canBuzz, canJudge, canSubmitAnswer                                      |
| `hooks/useCountdown`     | counts down, stops at 0, restarts when deadline changes                                     |
| `hooks/useLobbySocket`   | connects with token, applies state_changed, surfaces errors, disconnects on unmount         |
| `components/auth/SignInForm` | submits, shows field errors, surfaces ApiError detail                                   |
| `components/lobby/LobbyList` | renders rows, filters by state, join button navigates                                   |
| `components/game/GameBoard` | clickable only for selector + correct phase, scores rendered correctly                   |
| `components/game/HostJudgePanel` | only renders for host + judging phase; emits judge_answer                            |
| `components/game/BuzzButton` | only enabled for eligible players in BUZZ_OPEN; emits buzz once                         |
| `components/game/TimerBar` | width shrinks; numeric label updates                                                      |
| `components/game/FinalLeaderboard` | sorts by score desc, marks host non-scoring                                       |
| `pages/LobbyPage`        | renders correct sub-view per (role, phase) using a fixture-driven matrix test               |

Goal is ~75% coverage on `services/` and `hooks/`, plus a smoke test per major
component. No backend integration tests from the FE side — those live in `be/`.

---

## 12. Build & dev scripts

```jsonc
// package.json (excerpt)
"scripts": {
  "dev":     "vite",
  "build":   "tsc -b && vite build",
  "preview": "vite preview",
  "test":    "vitest run",
  "test:watch": "vitest",
  "lint":    "eslint --max-warnings 0 src",
  "format":  "prettier --write src",
  "typecheck": "tsc --noEmit"
}
```

Dev proxy in `vite.config.ts` forwards `/api` and `/ws` to
`http://localhost:8080` so the FE and BE share an origin during development
(no CORS issues; matches the eventual single-EC2 deployment topology).

---

## 13. Implementation phases (suggested order)

1. **Bootstrap**: `bun create vite`, Tailwind v4 setup, ESLint/Prettier,
   Vitest, base folder skeleton, `env.ts`, `http.ts`, `authStore`.
2. **Auth UX**: `SignInForm`, `RegisterForm`, `HomePage` (unauth view), `useMe`,
   `TopBar` w/ sign-out. Unit tests for store + form.
3. **Categories CRUD**: REST hooks, `CategoriesPage`, `CategoryEditPage`,
   `PromptEditor`. (Media upload is stub.)
4. **Lobby setup**: `CreateLobbyModal`, `LobbySetupPanel`, `useUpdateLobby`,
   `LobbyList` on `HomePage`.
5. **Socket plumbing**: `client.ts`, `useLobbySocket`, `useGameState`,
   `useCountdown`, `roleFor`, plus tests. Validate against a manually run BE.
6. **Game UI**: `GameBoard`, `PromptStage`, `AnswerInput`, `BuzzButton`,
   `HostJudgePanel`, `HostControls`, `ScoreBoard`, `TimerBar`, `PhaseBanner`,
   `FinalLeaderboard`. Per-component unit tests.
7. **Mobile polish**: responsive breakpoints, sticky bottom bars, larger tap
   targets, `clamp()` scaling.
8. **Error UX**: `Toast`, ApiError surfacing, socket error routing, 401 → sign-in.

Each phase ends with `bun run typecheck && bun run lint && bun run test`
passing before moving on.

---

## 14. Things explicitly out of scope for v1

- Media upload UI (only the renderer + URL helper ship).
- WebSocket reconnection backoff customization (rely on socket.io defaults).
- E2E tests (Playwright/Cypress) — unit tests only for now.
- Profile editing, password reset, account deletion.
- Spectator-only mode for non-players.
- I18n.
