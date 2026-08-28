# Jeopardy game contract

This is the server-authoritative contract for a local Jeopardy lobby. The
client replaces its state with each Socket.IO snapshot; it does not maintain a
parallel game state machine.

## Transport and lifecycle

- REST (`/api/v1`) creates/configures lobbies and discovers waiting games.
- Socket.IO at path `/ws` drives gameplay. Each lobby is `/lobbies/{lobby_id}`.
- Redis stores internal active-game state at `lobby:{lobby_id}`.
- Database lifecycle:

  ```text
  created → waiting_start → in_progress → completed
  ```

  REST permits only `created → waiting_start`. The host's `start_game` event
  performs `waiting_start → in_progress`; the server completes the game.

## Setup contract

This MVP accepts text prompts only: `question_type=text` and
`answer_type=text`. A lobby may move to `waiting_start` only with one through
ten categories, each containing exactly five prompts with unique orders `1..5`.

Any authenticated host may select a complete visible category; category editing
remains owner-only. On `created → waiting_start`, categories and prompts are
snapshotted to Redis, so later edits do not alter the game.

## State views

### Public `state_changed`

Every connected client receives:

```text
GameLobbyState
├─ lobby_id
├─ host { user_id, username, connection_status }
├─ players[] { user_id, username, score, connection_status, is_selected, is_banned }
├─ categories[]
│  └─ prompts[] { prompt_id, question, order, is_selected, score_value }
├─ phase
├─ current_prompt_id
├─ selecting_player_id
├─ answering_player_id
├─ attempted_player_ids
├─ last_submitted_answer
└─ timer_deadline
```

Public prompts never have an `answer` field.

### Host-only `host_judging_answer`

Only the host receives this while `phase=host_judging_answer`:

```text
HostJudgingAnswer
├─ lobby_id
├─ prompt_id
├─ submitted_answer
└─ expected_answer
```

The submitted answer is public; the expected answer is host-private.

### Internal Redis state

The persisted `GameLobbyState` contains the expected prompt answers and is
never emitted directly to clients.

## Roles and roster

The owner is a non-scoring host/judge and never appears in `players[]`. Only
non-host players choose clues and earn scores.

Before start, authenticated users can join. Once the lobby is in progress:

- existing players can reconnect with their scores;
- new users are rejected;
- banned players stay rejected until unbanned;
- a simultaneous second device for one account is rejected.

## Gameplay

Phases are:

```text
waiting_for_players
host_selecting_starting_player
player_selecting_prompt
player_answering
host_judging_answer
buzz_open
finished
```

1. The host emits `start_game`; at least one connected, non-banned player is
   required.
2. The host selects a connected starter.
3. The selected player picks an unused prompt. It becomes selected, the player
   is answerer, and the answering deadline begins.
4. `submit_answer` is accepted only from the answerer before the server-side
   deadline. The server rejects a late answer even when a timer callback has
   not run yet.
5. The host judges:
   - correct: award points, make that player the next selector, resolve;
   - wrong: deduct points, record an attempt, then open buzz or resolve if no
     eligible buzzer remains.
6. The first eligible buzz becomes answerer and gets a new deadline.

## Timers and completion

- An answering timeout records an attempt without a score deduction, then
  opens buzz or resolves with no score.
- A buzz timeout resolves with no score.
- Completion is checked after every resolution: correct, wrong with no
  remaining buzzers, answering timeout with no buzzers, and buzz timeout.
- When every clue has been selected, phase becomes `finished`, timers and
  selection flags clear, and database state becomes `completed`.

Clients display countdowns using `timer_deadline`; the server is authoritative
for deadline validation and all state transitions.
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
