# Jeopardy Game Flow

End-to-end flow of a Jeopardy lobby, from creation through completion. Used by
the front-end to wire up screens, websocket handlers, and state rendering.

## Transport summary

- **REST (`/api/v1/...`)** is used only for lobby/category/prompt CRUD and for
  *discovering* joinable lobbies. It never advances the in-game state machine.
- **Socket.IO** is the in-game transport. Each lobby has its own namespace:
  `/lobbies/{lobby_id}`. All gameplay events flow over that namespace.
- **Redis** stores `GameLobbyState` under key `lobby:{lobby_id}` (set the
  moment the lobby moves to `waiting_start`). It is the source of truth for
  everything in-game (scores, current actor, timers, prompt status, etc.).
- The DB `lobby.state` column tracks the **lifecycle** of the lobby
  (`created → waiting_start → in_progress → completed`). Transitions are
  driven by:
  - `created → waiting_start`: REST `PATCH /api/v1/lobby/{id}` (host).
  - `waiting_start → in_progress`: **Socket.IO event from the host** (see
    Scenario 4). Not a REST call.
  - `in_progress → completed`: server-driven when the last prompt resolves
    (see Scenario 9). Not a client-initiated call.

## Server-tunable constants

Defined in `be/src/configs/constants.py`:

| Constant                  | Value | Meaning                                       |
| ------------------------- | ----- | --------------------------------------------- |
| `NUM_PROMPTS_IN_CATEGORY` | 5     | Number of prompts per category                |
| `MIN_CATEGORIES_IN_LOBBY` | 1     | Min prompt categories per lobby               |
| `MAX_CATEGORIES_IN_LOBBY` | 10    | Max prompt categories per lobby               |
| `SCORE_MULTIPLIER`        | 100   | Prompt `score_value = order * SCORE_MULTIPLIER` |
| `ANSWERING_TIME_SECONDS`  | 30    | Window for the selected player to answer       |
| `BUZZING_TIME_SECONDS`    | 10    | Window after a wrong answer for others to buzz |

The FE should not hardcode these; it should read the current `timer_deadline`
on `GameLobbyState` and render the remaining time directly.

## Game state schema (Redis)

```
GameLobbyState
├─ lobby_id: int
├─ host: GameHostState { user_id, username, connection_status }
├─ players: list[GamePlayerState] {
│    user_id, username, score, connection_status,
│    is_selected, is_banned
│  }
├─ categories: list[GameCategoryState] {
│    category_id, name,
│    prompts: list[GamePromptState] {
│      prompt_id, question, answer, order, is_selected,
│      score_value  # computed = order * SCORE_MULTIPLIER
│    }
│  }
├─ phase: GamePhaseEnum
├─ current_prompt_id: int | None     # the open prompt
├─ selecting_player_id: int | None   # whose turn to pick a prompt
├─ answering_player_id: int | None   # whose turn to answer
├─ attempted_player_ids: list[int]   # already tried (and failed) on current prompt
└─ timer_deadline: datetime | None
```

`GamePhaseEnum`:

```
waiting_for_players
host_selecting_starting_player
player_selecting_prompt
player_answering
host_judging_answer
buzz_open
finished
```

`PlayerConnectionStatusEnum`: `connected` | `disconnected`.

Host is always the lobby owner (`Lobby.owner_id`). Only players (non-host
users) accumulate score.

## Scenarios

### 1. Lobby creation → ready for players

1. Owner: `POST /api/v1/lobby` → DB row in state `created`, no players.
2. Owner: `PATCH /api/v1/lobby/{id}` with `prompt_category_ids=[…]` to attach
   categories. Allowed only while `state=created`. Count must be in
   `[MIN_CATEGORIES_IN_LOBBY, MAX_CATEGORIES_IN_LOBBY]`.
3. Owner: `PATCH /api/v1/lobby/{id}` with `state=waiting_start`.
4. On that transition, the server **materializes** `GameLobbyState` into
   Redis at `lobby:{id}`:
   - `host` populated from `Lobby.owner` (connection status starts as
     `disconnected` until the host's socket connects).
   - `categories[]` + `prompts[]` are snapshotted from the attached
     categories (so subsequent DB edits to categories/prompts can't mutate an
     in-flight game).
   - `players=[]`, `phase=waiting_for_players`, all defaults.

### 2. Player discovery & joining

1. Players hit `GET /api/v1/lobby?states=waiting_start` to list joinable
   lobbies. Filters available: `owner_ids`, `owner_username` (case-insensitive
   partial), `ids`, date range, pagination.
2. Player opens a Socket.IO connection to namespace `/lobbies/{lobby_id}`,
   authenticated by their bearer token.
3. On namespace connect, server:
   - Loads `GameLobbyState` from Redis.
   - Rejects if no such lobby, or `phase=finished`.
   - Rejects if `is_banned=True` for this `user_id`.
   - Rejects if the user_id is already in `players` with
     `connection_status=connected` (prevents multi-device).
   - Otherwise upserts a `GamePlayerState` (preserving prior `score` and
     `is_banned` on reconnect) and sets `connection_status=connected`.
   - Persists state and broadcasts `state_changed` (full `GameLobbyState`) to
     the namespace.
4. The host connects the same way to the same namespace. The server
   recognizes the user_id matches `host.user_id` and flips
   `host.connection_status=connected`. The host is not added to `players`.

### 3. Mid-lobby events while waiting

- **Player disconnects**: server flips that player's
  `connection_status=disconnected` but keeps the row (score, ban status
  persist across reconnects). Broadcast updated state.
- **Host bans a player**: host emits `ban_player({"user_id": X})`. Server
  validates sender == `host.user_id`, sets `is_banned=True`, force-disconnects
  that socket, broadcasts state.
- **Host unbans**: emits `unban_player({"user_id": X})` → clears `is_banned`.
  Player may re-join the namespace.

### 4. Host starts the game (websocket-driven DB transition)

1. Host emits `start_game` over the namespace (no payload required).
2. Server validates:
   - Sender == `host.user_id`.
   - DB lobby `state=waiting_start`.
   - At least one connected, non-banned player.
3. Server updates DB `lobby.state` to `in_progress` (this is the websocket
   handler's responsibility — there is **no** REST endpoint for this
   transition).
4. Server flips Redis `phase=host_selecting_starting_player` and broadcasts
   `state_changed`.

### 5. Host selects starting player

1. Host emits `select_starter({"user_id": X})`.
2. Server validates sender == `host.user_id`, target player is `connected`
   and not banned.
3. Server sets `selecting_player_id=X`, that player's `is_selected=True`,
   `phase=player_selecting_prompt`. No timer for the picking step itself.

### 6. Player picks a prompt

1. Selected player emits `select_prompt({"prompt_id": P})`.
2. Server validates sender == `selecting_player_id`, prompt exists in this
   lobby's categories, prompt `is_selected=False`.
3. Server mutates state:
   - Mark prompt `is_selected=True`, set `current_prompt_id=P`.
   - `answering_player_id = selecting_player_id`, that player keeps
     `is_selected=True`.
   - Clear `attempted_player_ids`.
   - `phase=player_answering`.
   - `timer_deadline = now + ANSWERING_TIME_SECONDS`.
4. Broadcast `state_changed`. FE shows the question to all clients and starts
   the countdown locally using `timer_deadline`.

### 7. Player answers

1. Answering player emits `submit_answer({"text": "..."})` before
   `timer_deadline`.
2. Server transitions `phase=host_judging_answer` and broadcasts the submitted
   text alongside state so all clients (and the host) see the answer.
3. Host emits `judge_answer({"correct": true|false})`.
   - **Correct** →
     - `player.score += prompt.score_value`.
     - The correct player becomes the next picker: `selecting_player_id =
       answering_player_id`; that player keeps `is_selected=True`; the
       previous answerer flag is cleared on everyone else.
     - Clear `current_prompt_id`, `answering_player_id`, `attempted_player_ids`.
     - `phase=player_selecting_prompt`.
     - Run end-of-game check (Scenario 10).
   - **Wrong** →
     - `player.score -= prompt.score_value`.
     - Push `answering_player_id` into `attempted_player_ids`.
     - Clear `answering_player_id`, drop that player's `is_selected=False`.
     - If every connected, non-banned, non-host player has now attempted:
       prompt is resolved as "no score" — selecting role returns to whoever
       picked the prompt; `phase=player_selecting_prompt`; clear
       `current_prompt_id`.
     - Otherwise: `phase=buzz_open`,
       `timer_deadline = now + BUZZING_TIME_SECONDS`.
4. Broadcast `state_changed`.

### 8. Buzz race

1. Eligible players (connected, not banned, not in `attempted_player_ids`)
   emit `buzz` (no payload).
2. Server accepts the first one atomically. The single-threaded SIO event
   loop guarantees ordering; if you ever shard across processes, do the
   "first buzz wins" check inside a Redis Lua script or `WATCH/MULTI` block.
3. Server sets `answering_player_id = buzzer_id`, that player's
   `is_selected=True`, `phase=player_answering`,
   `timer_deadline = now + ANSWERING_TIME_SECONDS`.
4. Resume Scenario 7 (player answers).

### 9. Timer expiries

- **`player_answering` expires** with no `submit_answer`: server treats it
  like a wrong judgment. Push to `attempted_player_ids`, clear
  `answering_player_id`; if everyone has attempted, resolve the prompt with
  no score; else `phase=buzz_open`,
  `timer_deadline = now + BUZZING_TIME_SECONDS`. Whether to deduct score on
  timeout is a tunable rule — current default is **no** score change on
  timeout (only on wrong judgments).
- **`buzz_open` expires** with no buzz: prompt resolves with no score.
  `phase=player_selecting_prompt`; selecting role returns to the previous
  picker; clear `current_prompt_id`.

The server runs a single per-lobby async timer task; clients render the
countdown locally from `timer_deadline`.

### 10. End-of-game check

After every prompt resolution, walk every category's `prompts`. If every
prompt has `is_selected=True`:

1. `phase=finished`, persist final scores in Redis.
2. Update DB `lobby.state=completed`.
3. Broadcast a final `state_changed`. Clients render the leaderboard.
4. The namespace can stay open for a courtesy view, but no further state
   transitions occur.

### 11. Reconnect mid-game

- Player reconnects to the namespace → server flips
  `connection_status=connected`, sends the full current `GameLobbyState` so
  the FE can render exactly the current screen (prompt visible, timer
  remaining, who's selected, scores).
- If the player was the active answerer when they dropped and the timer
  already expired during their absence, the prompt has already moved on —
  they don't get the turn back.
- Host reconnect works the same way (flips `host.connection_status`); host
  resumes whatever judging/selecting screen the current `phase` implies.

## Front-end implementation notes

- **One websocket connection per lobby**: open on join, close on leave or
  game end. Don't multiplex multiple lobbies onto the same socket — the
  per-lobby namespace handles isolation server-side.
- **State is fully server-authoritative**: every event response is a full
  `GameLobbyState` snapshot. Don't try to keep a parallel client-side FSM
  in sync — just render whatever the latest `state_changed` says.
- **Timers**: derive remaining time from `timer_deadline - now()` on the
  client. Don't trust an interval counter that started locally; if the user
  tabs away the interval will pause.
- **Role-based UI**: pick UI by comparing the current user's `user_id` with
  `host.user_id`, `selecting_player_id`, and `answering_player_id`. The
  `is_selected` flag on the player is the convenience flag for "this user is
  the current actor"; combine it with `phase` to know what action they
  should be performing.
- **REST is for setup only**: lobby creation, attaching categories,
  promoting `created → waiting_start`, and listing/discovering lobbies. Once
  the player is on the namespace, all game progression is websocket.
