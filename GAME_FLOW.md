# Jeopardy game flow

This is the normative game contract for the Jeopardy application.
Redis owns live-game state and timers; SQL owns lobby setup plus
participant/completion projections. Clients render ordered Socket.IO snapshots
and do not maintain a parallel game-state machine.

This document describes the **voice-answer** game. Players answer
through external voice software such as Discord. They do not type answers into
the application and do not press an answer-submission button.

For deployment and Tailscale configuration, see the
[`setup and game-night guide`](README.md). Gameplay rules are the same for
development and hosted sessions.

## Core rules

- The lobby owner is a distinct, non-scoring **host/judge**.
- Only non-host players select clues and receive scores.
- A prompt question and answer reveal can independently be text, image, audio,
  or video. Every prompt still has canonical text question and answer fields.
- A player answers verbally after selecting a clue or winning a buzz.
- The host accepts or rejects the spoken answer directly.
- Canonical expected answer text is private to host only while a player is
  actively answering. Canonical answer text and optional answer media are
  revealed publicly after clue resolves.
- The board is visible only before a clue is active. An active clue replaces
  the board with a full prompt stage.

## Lobby lifecycle and setup

Database lobby states are:

```text
created → waiting_start → in_progress → completed
```

- REST is used for lobby setup and discovery.
- Socket.IO is used for live gameplay at path `/ws`, with each lobby at
  `/lobbies/{lobby_id}`.
- Redis stores persisted live-game state at `game:{lobby_id}:state`, where the
  braces are a Redis Cluster hash tag. State is initialized when the lobby
  enters `waiting_start` and remains available through `finished`, unless the
  lobby is deleted.
- Each accepted live command uses Redis `WATCH`/`MULTI`/`EXEC` to atomically
  write one incremented state revision, a command-result deduplication entry,
  a Redis Stream transition event, and a durable timer schedule.
- SQL participant, ban, and completion records are projections written after
  Redis accepts a transition. Live-game authorization, scores, phases, and
  deadlines never use SQL projections as their authority.

### Backend ownership boundaries

- `GameService` is thin application-command façade used by Socket.IO handlers
  and timer hooks. It extracts command inputs, invokes Redis serialization,
  then requests any required SQL projection.
- `GameStateMachine` owns pure synchronous Jeopardy transitions: permissions,
  phase/deadline rules, score changes, reveal progression, and ban recovery.
  It mutates only an in-memory `GameLobbyState` and returns a command outcome;
  it performs no database, Redis, Socket.IO, or other awaited I/O.
- `GameCommandExecutor` sends one state-machine transition to
  `GameStateRepo`, supplies fallback command IDs, and translates missing-state
  or optimistic-conflict errors. `GameStateRepo` retains Redis
  `WATCH`/`MULTI`/`EXEC`, idempotency, event-stream, and timer-schedule work.
- `GameProjectionService` performs idempotent post-Redis SQL projections:
  participant creation and bans, lobby `in_progress`, and completed-game score
  snapshots. Redis remains live-game authority if projection work must retry.
- `GameStateMaterializer` converts the SQL lobby/category/prompt snapshot into
  its initial Redis `GameLobbyState` when lobby preparation reaches
  `waiting_start`.

### Category requirements

- A lobby has between one and three **rounds**, and each round has between one
  and five categories. The host assigns categories to rounds when creating the
  lobby (`rounds`: one list of category ids per round; list index + 1 is the
  round number).
- A category can be used only once per lobby; it cannot appear in two rounds.
  The maximum is therefore 3 x 5 = 15 categories.
- A lobby may move from `created` to `waiting_start` only after categories are
  attached to every round.
- Every attached category must contain exactly five valid prompts with unique
  orders `1..5`.
- Each prompt has independent `question_type` and `answer_type` values:
  `text`, `image`, `audio`, or `video`.
- Text content has no media asset. Non-text content must reference an uploaded
  media asset owned by the category editor and of matching kind. Canonical
  question and answer text remain required for every content type.
- On transition to `waiting_start`, selected categories and prompts are
  snapshotted for the game. Later category edits do not change the lobby.

### Rounds and prompt values

- Prompt value in round `r` is `order * 100 * 2^(r-1)`: round 1 is 100..500,
  round 2 is 200..1000, and round 3 is 400..2000. The value is stored on each
  prompt as `score_value` when the lobby is materialized.
- A wrong answer or timeout deducts the round-scaled value, exactly as in
  round 1.
- Only the current round's categories are selectable. All rounds stay in
  `categories` so clients can preload media for the whole game; the board
  shows only categories whose `round_number` equals `current_round`.
- A game whose Redis state predates rounds loads as a single round
  (`current_round=1`, `total_rounds=1`, category `round_number=1`).

### Betting prompts

- Some prompts are randomly flagged as **betting prompts** (`is_betting`) when
  the lobby is materialized on the move to `waiting_start`. The draw is made
  **per round**, from that round's own prompts.
- The host sets one optional number, `betting_prompt_count` ("Betting prompts
  in each round" in the lobby form, 0 to 25). It is a count of prompts, not a
  percent, applied to every round and clamped to that round's prompt count.
  When unset (`null`, shown as "Auto"), each round uses
  `prompt_count * 10 // 100`: 2 for a five-category round (25 prompts), 0 for a
  one-category round (5 prompts).
- The lobby form previews the result per round ("Round N: X of Y prompts will
  be betting prompts"), mirroring the server's clamp and default. It is UX
  only; the server draw is authoritative.
- `betting_prompt_count` can be changed through REST only while the lobby is
  `created`, in the same PATCH as `rounds` or separately. An explicit `null`
  resets it to the default.

### Roster rules

- Before the game starts, authenticated players join by connecting to the
  lobby Socket.IO namespace. Redis immediately updates the authoritative
  roster; the server then creates or refreshes the persistent
  `LobbyParticipant` projection.
- When a lobby becomes `in_progress`, its player roster is locked:
  - existing players may reconnect and retain their score;
  - new users cannot join;
  - banned users cannot reconnect until unbanned;
  - a reconnect takes over that user's recorded Socket.IO SID and asks the
    prior SID to disconnect.
- Redis fences SID cleanup: a disconnect removes connection ownership only
  when its SID is still the recorded owner, so an old disconnected socket
  cannot mark a newer reconnect as offline.
- A dropped socket is shown as `disconnected` only after a 15-second grace
  period (`DISCONNECT_GRACE_SECONDS`), and only if the user has not reconnected
  by then, so a brief network blip changes neither buzz eligibility nor the
  host's view. The grace timer is process-local.
- The host may reconnect and resume judging/control duties.
- Lobby discovery lists a waiting lobby as active only for users who are not
  its host or participant. **My lobbies** offers **Join** to the host and
  non-banned participants while the lobby is `waiting_start` or
  `in_progress`, so either role can return after disconnecting.
- At completion, final player scores and ban status are snapshotted to
  `LobbyParticipant`, and every round's standings are stored in
  `lobby_round_result`. Host and non-banned participants can read lobby details,
  final ranking, and per-round categories and results without opening a game
  socket.
- Host may delete its lobby in any lifecycle state. Server removes persistent
  lobby data plus the Redis state, event-stream, and timer-schedule keys,
  cancels local timer wakeups, emits `lobby_deleted`, then asks Socket.IO to
  disconnect sockets known to that server process.

### Prompt media

- Category editors upload prompt media through authenticated REST API. FastAPI
  validates bytes and stores file under generated immutable key; it does not
  serve file bytes.
- Supported media:
  - image: JPEG, PNG, WebP, maximum 10 MB upload; stored re-encoded as WebP
    (quality 85, longest edge capped at 1920 px, EXIF rotation applied);
  - audio: MP3, M4A/AAC, Ogg, maximum 20 MB;
  - video: browser-compatible H.264/AAC MP4, maximum 100 MB.
- Nginx is browser-facing media server at `/media/{storage_key}`. Prompt data
  contains generated same-origin reference, never arbitrary external URL.
- Native browser image, audio, and video controls render media. During an
  active game, question and answer audio/video each autoplay once when first
  shown if that browser has enabled game sound; native controls remain the
  manual fallback when sound is disabled or autoplay is blocked.

## State visibility

### Public `state_changed`

Every connected client receives a recipient-specific public `GameLobbyState`
snapshot:

```text
PublicGameLobbyState
├─ lobby_id
├─ state_revision
├─ host { user_id, username, connection_status }
├─ players[]
│  └─ { user_id, username, score, connection_status, is_selected, is_banned }
├─ categories[]
│  ├─ { category_id, name, round_number }
│  └─ prompts[] {
│       prompt_id, question, question_type, question_media,
│       order, is_selected, score_value,
│       is_betting                 # true only for the current prompt
│     }
├─ phase
├─ current_round
├─ total_rounds
├─ round_results[]                # one entry per finished round
│  └─ { round_number, scores[] { user_id, username, score, score_delta,
│       is_banned } }              # score is cumulative, score_delta is the round's
├─ current_prompt_id
├─ selecting_player_id
├─ answering_player_id
├─ attempted_player_ids
├─ min_bet                        # betting phases only, else 0
├─ max_bet                        # betting phases only, else 0
├─ current_bet                    # highest bet so far, else 0
├─ betting_player_id              # holder of the highest bet, else null
├─ timer_deadline
├─ resolved_prompt_id             # set only in answer_reveal
├─ resolved_answer                # set only in answer_reveal
├─ resolved_answer_type           # set only in answer_reveal
├─ resolved_answer_media          # set only in answer_reveal
├─ resolution                     # set only in answer_reveal
└─ latest_sound_cue_id
```

`state_revision` starts at `0` for a materialized game and increments exactly
once for each accepted state mutation. Recipients discard a state frame older
than the newest revision they rendered.

The host receives the full player roster, including banned rows, so it can
moderate and unban them. Non-host snapshots omit banned players entirely,
including their scores, connection state, active labels, and their rows in
`round_results`. The server emits
recipient-specific snapshots to separate host and player Socket.IO rooms; it
never broadcasts a broad state frame before these recipient-specific frames.

Public prompt data never contains expected-answer field. `question` and
`question_type` are populated only for current active prompt; other board
prompts expose only their identity, order, spent state, and value. The
exception is media: `question_media` and `answer_media` are present for every
board prompt so clients can preload all media during the lobby; this trades some
secrecy of upcoming media for faster loads. Answer text is never sent early.
`is_betting` is public only for the current prompt, so players learn a prompt is
a betting prompt once it is selected, not before. During `player_betting` and
`betting_open` the current prompt's `question` is empty and its `question_type`
is `text`; question media references are still sent for preloading, but clients
must not render them during betting.
Canonical correct answer text and `resolved_answer_media` are public only while:

```text
phase = answer_reveal
```

`resolution` is one of:

```text
correct
unanswered
expired
```

It is display information only; scoring and transitions remain
server-authoritative.

### Host-only `host_answer_key`

Only the host receives this event while a player has an active spoken answer:

```text
HostAnswerKey
├─ lobby_id
├─ prompt_id
└─ expected_answer
```

The backend emits or re-emits the answer key to the current host while the
game is in `player_answering`, including when the phase starts or the host
reconnects. The client clears this private value whenever the phase changes
away from `player_answering`.

No player receives `host_answer_key`. There is no public submitted-answer
field because spoken answers are not transmitted through the application.

### Internal Redis state

Persisted state contains full prompt data: canonical answers, content types,
and media references. It is never emitted directly to clients.

Per-lobby Redis data also includes:

- `game:{lobby_id}:events`: Redis Stream record for every accepted mutation,
  including command ID, transition reason, revision, and internal snapshot;
- `game:{lobby_id}:command:{command_id}`: short-lived cached accepted result
  used to make a repeated command ID idempotent;
- `game:{lobby_id}:timers`: sorted-set timer schedule, whose member contains
  the expected timer revision and deadline;
- `game:{lobby_id}:connection:{user_id}`: current Socket.IO SID used for
  reconnect takeover and fenced disconnect cleanup.

The Stream and internal snapshots are backend infrastructure data and must not
be exposed to browser clients.

### Live command serialization and Socket.IO delivery

- Redis serializes conflicting commands for one lobby optimistically. On a
  `WATCH` conflict, the backend reloads and revalidates against the newer
  revision; only retry exhaustion returns a retryable game-busy error.
- Socket.IO uses a shared `AsyncRedisManager` when
  `BE_SOCKETIO_REDIS_URL` is configured. Host/player room broadcasts and
  Redis SID lookup can then reach sockets attached to another backend worker.
  This Pub/Sub manager transports notifications only; Redis game-state
  transactions remain the authority.
- A WebSocket stays attached to the backend worker that accepted it. A
  reconnect can land on another worker and must receive a newly broadcast
  recipient-specific snapshot.
- State broadcasts are performed by the command/timer handler after its Redis
  transaction commits. The Redis Stream records transitions durably, but this
  implementation does not yet run a Stream consumer that replays a missed
  broadcast after that handler process crashes.

## Game phases

```text
waiting_for_players
host_selecting_starting_player
player_selecting_prompt
player_betting
betting_open
player_answering
buzz_open
answer_reveal
round_summary
finished
```

## Gameplay sequence

### 1. Wait for players

Phase:

```text
waiting_for_players
```

- The host can start only when at least one connected, non-banned player is
  present and every connected, non-banned player has `assets_loaded=true`.
  `start_game` with `{"force": true}` skips the loaded check (host override).
- Each player's client preloads all question and answer media and reports it
  with `set_assets_loaded`. The flag resets whenever that player's socket
  connects or disconnects, so a reconnecting client must report again.
- Players wait for the host.
- The host is the active actor in the UI.

### 2. Choose next player

Phase:

```text
host_selecting_starting_player
```

- The host chooses a connected, non-banned player.
- That player becomes `selecting_player_id`.
- The game transitions to `player_selecting_prompt`.

This phase occurs at game start and whenever ban recovery needs the host to
choose a replacement selector. It also occurs at the start of a later round
when the lowest-scoring eligible player is not unique, or nobody is eligible. If no player is currently eligible, it remains
visible until somebody reconnects or the host unbans somebody.

### 3. Select a clue

Phase:

```text
player_selecting_prompt
```

- Only `selecting_player_id` may select an unselected prompt, and only one in
  the current round (`Prompt belongs to another round` otherwise).
- The selected prompt becomes permanently spent.
- Set:
  - `current_prompt_id`;
  - `answering_player_id` to the selecting player;
  - `attempted_player_ids` to an empty list.
- Transition to `player_answering`.
- Start the answering timer.

Prompt stage shows canonical question text, which can be an instruction or
caption for image, audio, or video clue, plus optional question media.

If the selected prompt is a betting prompt, the flow below goes to
`player_betting` instead of `player_answering`.

### 3a. Betting prompts

Selecting a betting prompt: set `current_prompt_id`, clear
`answering_player_id`, flag the selector, and set the bet limits once for
everyone:

- `min_bet` = the prompt's round-scaled `score_value`;
- `max_bet` = `max(highest value of the current round, highest score among
  non-banned players)`, where the highest value of round `r` is
  `5 * 100 * 2^(r-1)`;
- `current_bet = 0`, `betting_player_id = null`.

The existing `clue_selected` cue still fires; there are no new cues. Bets are
integers and public. A bet is valid only when `min_bet <= amount <= max_bet`
and `amount` is strictly greater than `current_bet`, so there are no ties.

#### `player_betting` (10 seconds)

- Only `selecting_player_id` may bet. A bet ends the phase immediately.
- If the timer expires with no bet, the selector has no bet yet; if nobody else
  bets either, they answer at the prompt's default value (see Resolution).
- Either way the game continues to `betting_open`; when no eligible player
  other than the selector exists, `betting_open` is skipped and betting resolves
  at once.

#### `betting_open` (10 seconds, fixed)

- Every eligible non-host player **except the selector** may bet at any time.
  The timer does not restart on a bet. A player may raise their own bet if it
  is strictly higher than `current_bet`.
- When the timer ends, betting resolves.

#### Resolution

- Nobody bet: the selector is treated as having bet the prompt's default value
  (`min_bet`) and answers it as below. Only an ineligible (banned or
  disconnected) selector spends the prompt: `answer_reveal` with
  `resolution=expired`, nobody scores.
- Otherwise the prompt's `score_value` is set to the winning bet, the highest
  bettor becomes `answering_player_id` and `selecting_player_id`,
  `attempted_player_ids` is emptied, and the game enters `player_answering`
  with the usual 30-second timer and a `host_answer_key` for the host. The
  betting fields are cleared.
- **Nobody else may buzz.** A Wrong judgment deducts the bet and reveals with
  `resolution=unanswered`; a timeout deducts the bet and reveals with
  `resolution=expired`. Correct adds the bet.
- The highest bettor is the next selector whether they answered correctly or not.

### 4. Answer by voice; host judges directly

Phase:

```text
player_answering
```

- `answering_player_id` answers aloud through the agreed voice channel.
- The active player does **not** type an answer, send answer text over the
  socket, or press an answer-complete button.
- The host receives the private `host_answer_key` and sees prominent
  **Correct** and **Wrong** controls.
- The host may judge only while the server-side answering deadline remains
  valid.

#### Correct

When the host marks the spoken answer correct:

1. Add the prompt value to the answerer's score.
2. Make that player the next `selecting_player_id`.
3. Clear `answering_player_id` and active-player selection flags.
4. Enter `answer_reveal` with:
   - `resolved_prompt_id`;
   - `resolved_answer`;
   - `resolution=correct`.

#### Wrong

When the host marks the spoken answer wrong:

1. Deduct the prompt value from the answerer's score.
2. Add the answerer to `attempted_player_ids`.
3. Clear `answering_player_id`.
4. If another connected, non-banned, unattempted player exists, open buzz.
5. Otherwise enter `answer_reveal` with `resolution=unanswered`.

(A betting prompt never opens buzz; see 3a.)

The buzz window is ten seconds total. A player who wins it receives a separate
30-second spoken-answer timer.

The player who originally selected the clue remains the next selector when no
one answers that clue correctly.

#### Answer timeout

If the answering deadline expires before the host judges:

1. Record the active answerer in `attempted_player_ids`.
2. Subtract the clue value from that player's score, exactly as a host Wrong
   judgment does.
3. Clear `answering_player_id`.
4. Open buzz if an eligible player remains.
5. Otherwise enter `answer_reveal` with `resolution=expired`.

The resulting buzz window is ten seconds total; it is distinct from the
30-second answer-attempt timer after a winning buzz.

### 5. Buzz

Phase:

```text
buzz_open
```

- Every eligible non-host player sees a large Buzz control.
- The first eligible buzz wins the next answer attempt.
- A player is ineligible when they are banned, disconnected, or already in
  `attempted_player_ids`.
- The host never buzzes and never scores.
- The server sets the winning user as `answering_player_id`, marks them
  selected, transitions to `player_answering`, starts a new answering timer,
  and sends the host a new private `host_answer_key`.

The winning buzzer then answers by voice and the host uses the same direct
Correct/Wrong judgment flow.

#### Buzz timeout

If the buzz deadline expires before an eligible player buzzes:

1. Keep scores unchanged.
2. Clear current answer/buzz state.
3. Enter `answer_reveal` with `resolution=expired`.

## Answer reveal and game completion

### Answer reveal

Phase:

```text
answer_reveal
```

- The board stays hidden.
- Full prompt stage shows question text/media and public canonical answer
  text plus optional answer media.
- The server starts a 30-second maximum reveal timer.
- The host sees a **Next prompt** control and may end the reveal early with
  `advance_answer_reveal`; other clients wait for the host or the deadline.
- The client may show a resolution message, such as “Correct”, “No correct
  response”, or “Time expired”.

The correct answer is visible to all clients only in this phase.

### After the reveal ends

When the host advances or the reveal timer expires:

- if unselected prompts remain:
  - clear `resolved_prompt_id`, `resolved_answer`, and `resolution`;
  - transition to `player_selecting_prompt` only when saved next selector is
    connected and non-banned;
  - otherwise transition to `host_selecting_starting_player` so host chooses
    next player;
- if every prompt of the current round has been selected:
  - append a `round_results` entry with every player's cumulative score and
    `score_delta` (the score minus that player's score in the previous round
    result, or minus 0 for round 1), including banned players;
  - if `current_round < total_rounds`, transition to `round_summary`;
  - otherwise transition to `finished`:
    - clear timers and active IDs;
    - update database lobby state to `completed`;
    - snapshot final player score, username, and ban status for final ranking
      and store the round results.

The final clue of every round always receives its answer-reveal period before
the round leaderboard or final leaderboard appears.

### Round summary

Phase:

```text
round_summary
```

Exists only between rounds, after every prompt of the round is spent, so a
round cannot be skipped. After the **last** round there is no `round_summary`:
the game goes straight to `finished`.

- `selecting_player_id` is cleared, selection flags are cleared, and the
  server starts a 10-second timer.
- All clients show the round leaderboard: per player the cumulative score and
  the delta earned in that round.
- The host may end the summary early with `advance_round`; otherwise the
  timer does. There is no other way to start the next round.
- Starting the next round increments `current_round`, clears the timer, and
  picks the next selector: the connected, non-banned player with the strictly
  lowest score moves to `player_selecting_prompt`. If the lowest score is tied,
  or nobody is eligible, enter `host_selecting_starting_player`.
- Bans need no special branch here because `selecting_player_id` is `None`
  during the summary.
- No new sound cue is issued; background music stops, as in `answer_reveal`.

## Ban recovery

Banning always updates both Redis game state and persistent
`LobbyParticipant.is_banned`, then disconnects target socket.

- Ban current selector in `player_selecting_prompt`: clear active ownership
  and timer, then enter `host_selecting_starting_player`.
- Ban the selector in `player_betting`: clear the selector, selection flags and
  betting fields, then reveal the clue as `unanswered`. The prompt stays spent
  and nothing is scored.
- Ban the player holding the highest bet in `betting_open`: reset
  `current_bet` to `0` and `betting_player_id` to `null`; the window continues.
  Disconnects need no special handling.
- Ban active answerer in `player_answering`: leave selected clue spent, do not
  score or deduct it, clear ownership, then reveal it as `unanswered` for
  the normal 30-second maximum. Reveal completion enters host player
  selection.
- Ban next selector while clue is in `answer_reveal` or `buzz_open`: clear
  selector ID. Existing eligible buzzers remain able to buzz. After reveal,
  host chooses next player rather than returning control to banned selector.
- If banning leaves no eligible buzzer in `buzz_open`, reveal clue immediately
  as `unanswered`.

## Timers and deadline enforcement

Timer durations are:

```text
answering timer:     30 seconds
betting timer:       10 seconds (player_betting), 10 seconds fixed (betting_open)
buzz timer:          10 seconds
answer reveal timer: 30 seconds maximum
round summary timer: 10 seconds
```

The server is authoritative:

- `judge_answer` rejects an expired answering attempt even if a scheduled
  timer callback has not yet run. A fenced timer-expiry command performs the
  legal timeout transition.
- A late buzz is rejected even if the buzz timeout callback has not yet run.
- The browser derives countdown display from `timer_deadline - now()` and
  never decides game transitions locally.
- Every timed state carries an internal `timer_revision`. The same accepted
  transition atomically replaces its Redis sorted-set schedule entry with a
  member containing that revision and deadline. Timer workers must match both
  values before expiring it; stale entries therefore become no-ops.
- Each backend process may arm a local `asyncio` wakeup for low latency, but
  that wakeup only submits the fenced Redis expiry command. A process-local
  task is not timer authority.
- A per-process scheduler reconciles active Redis states with timer schedules
  and polls due entries. This recovers deadlines after a process restart;
  concurrent schedulers safely race through the same optimistic executor.

## Socket event permissions

| Event | Allowed sender | Required phase |
| --- | --- | --- |
| `set_assets_loaded` | lobby player | `waiting_for_players` |
| `start_game` | host | `waiting_for_players` |
| `select_starter` | host | `host_selecting_starting_player` |
| `select_prompt` | current selector | `player_selecting_prompt` |
| `place_bet` | selector in `player_betting`; eligible non-host non-selector in `betting_open` | `player_betting`, `betting_open` |
| `judge_answer` | host | `player_answering` |
| `buzz` | eligible non-host player | `buzz_open` |
| `advance_answer_reveal` | host | `answer_reveal` |
| `advance_round` | host | `round_summary` |
| `ban_player` / `unban_player` | host | no phase restriction while host has active lobby socket |

All rejected events return a structured socket error to the sender. Clients
must not optimistically mutate game state.

Payload-bearing events accept an optional UUID `command_id`; a repeated
accepted ID returns its cached result without a second state mutation. The
web client emits a UUID for every gameplay event, but the current server reads
it only from payload-bearing events. `buzz`,
`advance_answer_reveal`, and `advance_round` currently receive a server-generated ID, so retries
of those payload-free events are not client-idempotent. Older clients without
a payload command ID also receive a server-generated ID.

## Rendering rules

### Board and prompt stage

- Show the category board only before a clue is active:
  - `waiting_for_players`;
  - `host_selecting_starting_player`;
  - `player_selecting_prompt`.
- Show only the current round's categories on the board
  (`round_number === current_round`).
- Give every category header the same vertical space so prompt rows align
  despite title length.
- During `player_betting` and `betting_open`, the board and prompt stage are
  hidden and a betting panel is shown instead: category name, the range
  `min_bet..max_bet`, the current highest bet and its holder (or "No bet yet"),
  and the countdown. Players who may bet also get a number input (default
  `max(min_bet, current_bet + 1)`) and a **Place bet** button; the host and
  everyone else see it read-only. The selected tile flashes on the board first,
  as for any clue. Client-side bet validation is UX only.
- Replace board with full prompt stage in:
  - `player_answering`;
  - `buzz_open`;
  - `answer_reveal`.
- In `round_summary`, show the round leaderboard in the board area (title
  "Round N complete", rank, name, cumulative score, and `+delta`, plus the
  countdown). The host sees a **Start round N+1** button; everyone else sees
  "Next round starts automatically". The phase banner shows "Round X of Y"
  whenever `total_rounds > 1`.
- The final leaderboard and lobby details break results down per round: each
  round's category names plus the standings after it.
- Current prompt provides its text, type, and optional media only while prompt
  is active. Question and answer audio/video use stable per-prompt playback
  identities, so ordinary parent renders do not restart them. Each game-media
  item autoplays once only when game sound is enabled; media controls remain
  native and manually usable.
- Canonical answer text and optional answer media remain hidden until
  `answer_reveal`.

### Participant and control panel

- The host/player panel receives proportionally more desktop space than the
  current narrow sidebar.
- Highlight the active answerer with an explicit `ANSWERING` label.
- Highlight the current selector with `SELECTING`.
- Highlight the host during host action:
  - starting the game;
  - choosing the next player;
  - judging an active spoken answer.
- Use labels as well as color so the active state is accessible.
- During `buzz_open`, all non-host players see a large Buzz control in either
  enabled or disabled form. The disabled state must remain understandable.
- During `player_answering`, the host sees large Correct/Wrong controls; the
  current answerer is expected to answer over voice rather than use an
  application control.

## Client implementation rules

- Maintain one Socket.IO connection per lobby namespace.
- Replace client game state on each valid `state_changed` frame unless its
  `state_revision` is older than the newest rendered revision.
- Keep host-private answer-key data separate from public game state and clear
  it on phase change/disconnect.
- Invalidate lobby discovery queries when a lobby moves out of
  `waiting_start`, reaches `finished`, or is otherwise changed through REST.
- Treat connection, roster-lock, ban, late-join, and invalid-action errors as
  explicit user-facing states.
- Sound is opt-in for every browser page load. Browser storage records the
  previous setting and volume, but playback never begins without a new user
  gesture. Sound failure remains presentation-only.
- While prompt audio/video is playing, the active board or answering
  background loop pauses without resetting. It resumes only after all active
  prompt media has ended, paused, errored, or unmounted, provided the current
  game phase still calls for that loop.

## Presentation-only sound cues

For qualifying gameplay transitions, the server emits `game_sound_cue` after
the successful state broadcast. Payload:

```text
{ cue_id: increasing integer, cue: game_started | clue_selected |
  buzz_accepted | answer_correct | answer_wrong | answer_expired |
  answer_revealed | game_completed }
```

Clients deduplicate `cue_id` values and may miss cues without consequence.
Sound never changes timers, scores, eligibility, phase transitions, or Socket.IO
permissions. Audio preferences are local browser presentation settings only.
