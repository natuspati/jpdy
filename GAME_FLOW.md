# Jeopardy game flow

This is the normative game contract for the local Jeopardy application.
The server owns game state and timers; clients render the latest Socket.IO
snapshot and do not maintain a parallel game-state machine.

This document describes the intended **voice-answer** game. Players answer
through external voice software such as Discord. They do not type answers into
the application and do not press an answer-submission button.

## Core rules

- The lobby owner is a distinct, non-scoring **host/judge**.
- Only non-host players select clues and receive scores.
- A prompt question and answer reveal can independently be text, image, audio,
  or video. Every prompt still has canonical text question and answer fields.
- A player answers verbally after selecting a clue or winning a buzz.
- The host accepts or rejects the spoken answer directly.
- Canonical expected answer text is private to host while clue is active, then
  canonical answer text and optional answer media are revealed publicly after
  clue resolves.
- The board is visible only while a player is choosing a clue. An active clue
  replaces the board with a full prompt stage.

## Lobby lifecycle and setup

Database lobby states are:

```text
created → waiting_start → in_progress → completed
```

- REST is used for lobby setup and discovery.
- Socket.IO is used for live gameplay at path `/ws`, with each lobby at
  `/lobbies/{lobby_id}`.
- Redis stores the persisted internal state of an active lobby at
  `lobby:{lobby_id}`.

### Category requirements

- A lobby must have between one and ten attached categories.
- A lobby may move from `created` to `waiting_start` only after categories are
  attached.
- Every attached category must contain exactly five valid prompts with unique
  orders `1..5`.
- Each prompt has independent `question_type` and `answer_type` values:
  `text`, `image`, `audio`, or `video`.
- Text content has no media asset. Non-text content must reference an uploaded
  media asset owned by the category editor and of matching kind. Canonical
  question and answer text remain required for every content type.
- On transition to `waiting_start`, selected categories and prompts are
  snapshotted for the game. Later category edits do not change the lobby.

### Roster rules

- Before the game starts, authenticated players join by connecting to the
  lobby Socket.IO namespace. This creates or refreshes a persistent
  `LobbyParticipant` record.
- When a lobby becomes `in_progress`, its player roster is locked:
  - existing players may reconnect and retain their score;
  - new users cannot join;
  - banned users cannot reconnect until unbanned;
  - one account cannot play simultaneously from multiple devices.
- The host may reconnect and resume judging/control duties.
- Lobby discovery lists a waiting lobby as active only for users who are not
  its host or participant. **My lobbies** offers **Join** to the host and
  non-banned participants while the lobby is `waiting_start` or
  `in_progress`, so either role can return after disconnecting.
- At completion, final player scores and ban status are snapshotted to
  `LobbyParticipant`. Host and non-banned participants can read lobby details
  and final ranking without opening a game socket.
- Host may delete its lobby in any lifecycle state. Server removes persistent
  lobby data and Redis game state, cancels timer, emits `lobby_deleted`, then
  disconnects lobby sockets.

### Prompt media

- Category editors upload prompt media through authenticated REST API. FastAPI
  validates bytes and stores file under generated immutable key; it does not
  serve file bytes.
- Supported media:
  - image: JPEG, PNG, WebP, maximum 10 MB;
  - audio: MP3, M4A/AAC, Ogg, maximum 20 MB;
  - video: browser-compatible H.264/AAC MP4, maximum 100 MB.
- Nginx is browser-facing media server at `/media/{storage_key}`. Prompt data
  contains generated same-origin reference, never arbitrary external URL.
- Native browser image, audio, and video controls render media. Audio and
  video never autoplay.

## State visibility

### Public `state_changed`

Every connected client receives a recipient-specific public `GameLobbyState`
snapshot:

```text
PublicGameLobbyState
├─ lobby_id
├─ host { user_id, username, connection_status }
├─ players[]
│  └─ { user_id, username, score, connection_status, is_selected, is_banned }
├─ categories[]
│  └─ prompts[] {
│       prompt_id, question, question_type, question_media,
│       order, is_selected, score_value
│     }
├─ phase
├─ current_prompt_id
├─ selecting_player_id
├─ answering_player_id
├─ attempted_player_ids
├─ timer_deadline
├─ resolved_prompt_id             # set only in answer_reveal
├─ resolved_answer                # set only in answer_reveal
├─ resolved_answer_type           # set only in answer_reveal
├─ resolved_answer_media          # set only in answer_reveal
├─ resolution                     # set only in answer_reveal
└─ latest_sound_cue_id
```

The host receives the full player roster, including banned rows, so it can
moderate and unban them. Non-host snapshots omit banned players entirely,
including their scores, connection state, and active labels. The server never
broadcasts a broad state frame before these recipient-specific frames.

Public prompt data never contains expected-answer field. `question`,
`question_type`, and `question_media` are populated only for current active
prompt; other board prompts expose only their identity, order, spent state,
and value. Canonical correct answer text and optional answer media are public
only while:

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

The backend emits or re-emits the answer key to the current host when the game
enters `player_answering` and when the host reconnects during that phase. The
client clears this private value whenever the phase changes away from
`player_answering`.

No player receives `host_answer_key`. There is no public submitted-answer
field because spoken answers are not transmitted through the application.

### Internal Redis state

Persisted state contains full prompt data: canonical answers, content types,
and media references. It is never emitted directly to clients.

## Game phases

```text
waiting_for_players
host_selecting_starting_player
player_selecting_prompt
player_answering
buzz_open
answer_reveal
finished
```

There is intentionally no `host_judging_answer` phase in the desired flow.
The host judges directly while the active player is answering by voice.

## Gameplay sequence

### 1. Wait for players

Phase:

```text
waiting_for_players
```

- The host can start only when at least one connected, non-banned player is
  present.
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
choose a replacement selector. If no player is currently eligible, it remains
visible until somebody reconnects or the host unbans somebody.

### 3. Select a clue

Phase:

```text
player_selecting_prompt
```

- Only `selecting_player_id` may select an unselected prompt.
- The selected prompt becomes permanently spent.
- Set:
  - `current_prompt_id`;
  - `answering_player_id` to the selecting player;
  - `attempted_player_ids` to an empty list.
- Transition to `player_answering`.
- Start the answering timer.

Prompt stage shows canonical question text, which can be an instruction or
caption for image, audio, or video clue, plus optional question media.

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

The buzz window is ten seconds total. A player who wins it receives a separate
30-second spoken-answer timer.

The player who originally selected the clue remains the next selector when no
one answers that clue correctly.

#### Answer timeout

If the answering deadline expires before the host judges:

1. Record the active answerer in `attempted_player_ids`.
2. Do not change that player's score.
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
- The server starts a short reveal timer; the initial local value is five
  seconds.
- The client may show a resolution message, such as “Correct”, “No correct
  response”, or “Time expired”.

The correct answer is visible to all clients only in this phase.

### After the reveal timer

After the reveal timer expires:

- if unselected prompts remain:
  - clear `resolved_prompt_id`, `resolved_answer`, and `resolution`;
  - transition to `player_selecting_prompt` only when saved next selector is
    connected and non-banned;
  - otherwise transition to `host_selecting_starting_player` so host chooses
    next player;
- if every prompt has been selected:
  - transition to `finished`;
  - clear timers and active IDs;
  - update database lobby state to `completed`;
  - snapshot final player score, username, and ban status for final ranking.

The final clue always receives its answer-reveal period before the final
leaderboard appears.

## Ban recovery

Banning always updates both Redis game state and persistent
`LobbyParticipant.is_banned`, then disconnects target socket.

- Ban current selector in `player_selecting_prompt`: clear active ownership
  and timer, then enter `host_selecting_starting_player`.
- Ban active answerer in `player_answering`: leave selected clue spent, do not
  score or deduct it, clear ownership, then reveal it as `unanswered` for
  normal five seconds. Reveal expiry enters host player selection.
- Ban next selector while clue is in `answer_reveal` or `buzz_open`: clear
  selector ID. Existing eligible buzzers remain able to buzz. After reveal,
  host chooses next player rather than returning control to banned selector.
- If banning leaves no eligible buzzer in `buzz_open`, reveal clue immediately
  as `unanswered`.

## Timers and deadline enforcement

Initial local timing values are:

```text
answering timer:     30 seconds
buzz timer:          10 seconds
answer reveal timer:  5 seconds
```

The server is authoritative:

- `judge_answer` must reject or resolve expired answering attempts even if a
  scheduled timer callback has not yet run.
- A late buzz is rejected even if the buzz timeout callback has not yet run.
- The browser derives countdown display from `timer_deadline - now()` and
  never decides game transitions locally.

## Socket event permissions

| Event | Allowed sender | Required phase |
| --- | --- | --- |
| `start_game` | host | `waiting_for_players` |
| `select_starter` | host | `host_selecting_starting_player` |
| `select_prompt` | current selector | `player_selecting_prompt` |
| `judge_answer` | host | `player_answering` |
| `buzz` | eligible non-host player | `buzz_open` |
| `ban_player` / `unban_player` | host | no phase restriction while host has active lobby socket |

The desired flow removes these old typed-answer concepts:

```text
submit_answer
last_submitted_answer
host_judging_answer
finish_answering
```

All rejected events return a structured socket error to the sender. Clients
must not optimistically mutate game state.

## Rendering rules

### Board and prompt stage

- Show the category board only before a clue is active:
  - `waiting_for_players`;
  - `host_selecting_starting_player`;
  - `player_selecting_prompt`.
- Give every category header the same vertical space so prompt rows align
  despite title length.
- Replace board with full prompt stage in:
  - `player_answering`;
  - `buzz_open`;
  - `answer_reveal`.
- Current prompt provides its text, type, and optional media only while prompt
  is active. Media controls are native and never autoplay.
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
- Replace client game state on each valid `state_changed` frame.
- Keep host-private answer-key data separate from public game state and clear
  it on phase change/disconnect.
- Invalidate lobby discovery queries when a lobby moves out of
  `waiting_start`, reaches `finished`, or is otherwise changed through REST.
- Treat connection, roster-lock, ban, late-join, and invalid-action errors as
  explicit user-facing states.
- Sound is opt-in for every browser page load. Browser storage records the
  previous setting and volume, but playback never begins without a new user
  gesture. Sound failure remains presentation-only.

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
