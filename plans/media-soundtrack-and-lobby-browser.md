# Media, Soundtrack, and Lobby Discovery Plan

## Scope

This plan combines every item from the previous game-UI backlog with new
soundtrack work:

1. media prompts: image, audio, and video question media;
2. host lobby deletion from the home page;
3. Counter-Strike-style lobby browser;
4. background music and action sound effects.

It builds on the completed voice-answer, answer-reveal game contract in
`GAME_FLOW.md`. Gameplay remains server-authoritative. Sound is presentation
only: it must never change timers, scores, eligibility, phase transitions, or
Socket.IO permissions.

## Decisions made by this plan

- Prompt questions may be `text`, `image`, `audio`, or `video`.
- Prompt answers remain **text only**. Answer-media support is out of scope.
- Uploaded prompt media is stored as a first-class media asset, not as an
  arbitrary URL pasted into a prompt.
- A lobby owner may delete only `created` and `waiting_start` lobbies.
  Deleting `in_progress` or `completed` lobbies remains disallowed.
- Public lobby discovery includes `waiting_start`, `in_progress`, and
  `completed` lobbies. Private `created` drafts are visible only in the
  owner’s draft section.
- `waiting_start` rows offer **Join**. `in_progress` and `completed` rows
  offer read-only **View details**; this plan does not add spectators.
- Game audio defaults to off until each browser user enables it. This avoids
  browser autoplay failures and unwanted audio.
- The audio manager uses fixed base gains: background music at approximately
  `0.1` and one-shot effects at approximately `0.2`. One in-game volume
  slider is the only volume control and multiplies both base gains.
- Do not add downloaded TV-show audio to the repository unless its use is
  authorized. Exact Jeopardy television music and effects may be protected.
  Provide assets you own, created, or have permission/license to use; a
  licensed “classic quiz-show style” replacement is acceptable.

## Included audio assets

The approved MP3 bundle is already committed in `fe/src/assets/game-audio/`.
It contains generic game audio from CC0/public-domain sources, not television
show audio.

```text
fe/src/assets/game-audio/
├─ intro.mp3                 # game starts; 2–8 seconds
├─ board-loop.mp3            # waiting/board background; seamless 20–90 second loop
├─ answering-loop.mp3        # active spoken-answer/buzz background; seamless 15–45 second loop
├─ clue-selected.mp3         # clue opens; 0.2–2 seconds
├─ buzz.mp3                  # first eligible buzz accepted; 0.1–1 second
├─ correct.mp3               # host marks answer correct; 0.2–2 seconds
├─ wrong.mp3                 # host marks answer wrong; 0.2–2 seconds
├─ time-expired.mp3          # answer or buzz timer expires; 0.2–2 seconds
├─ answer-reveal.mp3         # answer-reveal screen opens; 0.5–3 seconds
└─ game-complete.mp3         # final reveal completes; 2–10 seconds
```

No separate audio-asset documentation is needed for this personal,
non-distributed project. Do not add audio from television episodes, streaming
services, YouTube, or fan collections without the needed authorization.

### Audio technical requirements

- Final delivery: MP3, stereo or mono, 44.1 kHz or 48 kHz.
- Use no leading/trailing silence on one-shot cues.
- Make both loop files seamless at their exact start/end points.
- In the audio manager, start background music around gain `0.1` and
  one-shot effects around gain `0.2`, before applying user volume and ducking.
- Do not include spoken answer content, player names, ad reads, or profanity.
- Keep one-shot effects small; prefer less than 1 MB each. Keep loops
  reasonably sized for mobile connections.
- Use neutral filenames above. Do not encode trademarked show names in paths
  or UI copy.

If only lossless source files are available, retain those outside the web
bundle and create the approved MP3 derivatives for the application.

## 1. Add common media-asset infrastructure

### Problem

The current database has content-type columns, but the API accepts only text
and there is no upload, storage, validation, or public delivery path for
media.

### Data model and storage

- Add a `media_asset` model and Alembic migration. Keep the model portable
  across SQLite and PostgreSQL; use normal `String`, `Integer`, `Boolean`,
  and timestamp columns rather than database-specific JSON or blob types.
- Store metadata such as:
  - asset ID;
  - owner ID;
  - immutable storage key;
  - original filename;
  - media kind (`image`, `audio`, or `video`);
  - validated MIME type;
  - byte size;
  - optional duration/dimensions when safely determined;
  - creation time.
- Store uploaded bytes outside the database:
  - local development: configured persistent filesystem directory;
  - container development: a dedicated named volume mounted into the backend;
  - deployment: preserve the same storage interface so a durable object
    store/CDN backend can be added without changing prompt records.
- Storage keys must be generated server-side. Never use a user filename as a
  path and never allow `..`, absolute paths, or arbitrary external URLs.
- Serve only approved media MIME types with `X-Content-Type-Options: nosniff`.
  Reject SVG and executable/document formats.
- Add a cleanup path for orphan assets. Deleting an asset attached to a prompt
  must be rejected; replacing media creates a new immutable asset instead.

### API and validation

- Add authenticated multipart upload endpoints and typed metadata responses.
- Limit uploads to prompt-compatible types:

  | Media kind | Accepted final formats | Initial maximum |
  | --- | --- | --- |
  | Image | JPEG, PNG, WebP | 10 MB |
  | Audio | MP3, M4A/AAC, Ogg | 20 MB |
  | Video | MP4 with browser-compatible H.264/AAC | 100 MB |

- Validate actual file signatures/MIME rather than trusting the browser
  `Content-Type`. Reject files that do not match their declared type.
- Enforce ownership when assigning an asset to a prompt.
- Add a public, immutable media URL to the validated asset metadata. Prompt
  media is intentionally viewable by game participants, just as prompt text
  is; assets must not carry private expected-answer data.
- Add a configured upload root/base URL and document local/container setup in
  `README.md` and deployment configuration.

### Prompt representation

- Keep `question` as the author-facing instruction/caption and keep `answer`
  as the expected text answer.
- Add nullable `question_media_asset_id` to `prompt`.
- Preserve the existing `question_type` field and enforce:
  - `text`: no question-media asset;
  - `image`, `audio`, or `video`: exactly one matching question-media asset;
  - every `answer_type`: `text`;
  - text answers remain required.
- Expose a typed public `QuestionContent` object instead of forcing the client
  to infer a media URL from a string:

  ```text
  QuestionContent
  ├─ type: text | image | audio | video
  ├─ text                         # question/instructions
  └─ media? { asset_id, url, mime_type, filename }
  ```

- Update internal game snapshots to include the selected prompt’s question
  content. Snapshot the immutable asset reference when the lobby moves to
  `waiting_start`, so later prompt edits cannot change a running game.
- Keep expected answers out of public game state until `answer_reveal`.
  This work must not weaken the current answer-key and answer-reveal privacy
  rules.

### Authoring UI

- Replace text-only prompt schema literals with the supported question-type
  union while preserving text-only answer fields.
- In `PromptEditor`, let an owner select question type and show:
  - text area only for text prompts;
  - prompt instruction/caption plus upload/select/replace controls for media
    prompts;
  - file-type, size, and ownership errors before and after upload;
  - media preview with remove/replace controls.
- Do not auto-upload on file selection without visible progress and an
  explicit error state.
- Show author guidance:
  - image: add text that tells players what to identify;
  - audio/video: use a concise instruction and avoid an answer-revealing
    transcript unless that is the intended clue;
  - provide meaningful accessible labels/captions where possible.

### Game rendering

- Add a focused `PromptMedia` renderer used only by `PromptStage`.
- Render:
  - responsive images with meaningful alt text from authored prompt context;
  - native `<audio controls preload="metadata">`;
  - native `<video controls preload="metadata">`.
- Never inject user HTML. Do not autoplay authored prompt audio/video.
- Keep media controls keyboard accessible and avoid hiding the spoken-answer,
  Buzz, host-judgment, timer, or answer-reveal controls.
- Retain the existing text prompt layout when no media is attached.

### Acceptance criteria

- An owner can create and edit text, image, audio, and video question prompts.
- Invalid type, size, ownership, and MIME-signature uploads are rejected.
- A game snapshot renders selected question media correctly.
- Public game frames still never contain the expected answer before
  `answer_reveal`.
- Text answers continue to work unchanged for all prompt types.
- A running/waiting game remains stable if its source prompt is edited later.

## 2. Add game soundtrack and action effects

### Audio architecture

- Create a typed frontend sound manifest that imports only approved files from
  `fe/src/assets/game-audio/`. Vite then fingerprints files in production.
- Create a single `GameAudioProvider`/audio manager near the application
  shell. Do not create independent `Audio` objects inside game components.
- The manager owns:
  - enabled/disabled preference and one shared volume multiplier;
  - fixed base gain near `0.1` for background loops and `0.2` for one-shot
    effects; effective gain is `base gain × shared volume multiplier`;
  - looping, fade in/out, and one-shot playback;
  - ducking background music while an action effect plays;
  - cleanup when leaving a lobby, disconnecting, muting, or unmounting.
- Persist only local audio preferences in browser storage. Never synchronize a
  user’s enabled/mute choice or volume multiplier through the game server.
- Add accessible sound controls in the active-game UI:
  - initial state: **Enable sound**;
  - enabled state: mute/unmute plus one clearly labeled **Game volume** slider
    from `0` to `100%`;
  - slider value is a multiplier for both fixed base gains; do not add
    separate music/effects sliders;
  - clear text when browser playback is blocked;
  - visible state, not icon-only controls.
- Keep all existing visual state/copy. Sound must never be the sole indication
  of a correct answer, timeout, buzz, ban, or phase change.

### Browser autoplay handling

- Do not attempt to force autoplay on first page load.
- First click/tap on **Enable sound** must create/unlock the audio context and
  start the applicable background track, if any.
- If the browser rejects playback, leave sound disabled and show a concise
  recovery message. Retrying after another explicit user gesture must work.
- Users who join a game with sound disabled must not receive a burst of old
  effects when they enable it later. Start only the current background track.

### Server-issued action cues

Client state snapshots remain authoritative for rendering, but transition
effects must not be inferred from a parallel browser game-state machine.

- Add a server-issued, presentation-only Socket.IO event such as
  `game_sound_cue`.
- Define a validated payload with an increasing cue ID and one of:

  ```text
  game_started
  clue_selected
  buzz_accepted
  answer_correct
  answer_wrong
  answer_expired
  answer_revealed
  game_completed
  ```

- Emit a cue only after the corresponding server action/timer transition has
  succeeded and the resulting state is broadcast.
- Emit to the lobby namespace for every connected host/player. Clients never
  emit this event and missed cues have no gameplay consequence.
- Update direct action handlers and timer-hook expiry paths so correct, wrong,
  buzz, answer timeout, buzz timeout, reveal, and final completion each emit
  the appropriate cue exactly once.
- Deduplicate cue IDs client-side to tolerate Socket.IO retransmission. On a
  fresh connection, establish the latest cue ID without replaying old
  one-shots.

### Cue mapping and background rules

| Server cue / game state | Audio behavior |
| --- | --- |
| `waiting_for_players`, `host_selecting_starting_player`, `player_selecting_prompt` | Play `board-loop.mp3` when sound is enabled. |
| `game_started` | Play `intro.mp3`; resume/fade board loop afterward. |
| `clue_selected` | Play `clue-selected.mp3`, then switch to `answering-loop.mp3`. |
| `player_answering` or `buzz_open` | Keep `answering-loop.mp3` active at low background volume. |
| `buzz_accepted` | Play `buzz.mp3`; continue answering loop. |
| `answer_correct` | Play `correct.mp3`; stop answering loop before reveal. |
| `answer_wrong` | Play `wrong.mp3`; retain/switch to answering loop if buzz opens. |
| `answer_expired` | Play `time-expired.mp3`; stop answering loop before reveal. |
| `answer_revealed` | Play `answer-reveal.mp3`; do not loop music during the short reveal. |
| `game_completed` | Play `game-complete.mp3`; stop all loops. |
| Disconnect, lobby leave, mute | Stop all active tracks and release listeners. |

If two effects occur close together, preserve the most important state cue and
avoid overlapping a pile of one-shots. For example, an expired clue should
play `time-expired` before the reveal cue, with the reveal cue delayed or
suppressed according to the documented audio-manager priority rule.

### Documentation and acceptance criteria

- `GAME_FLOW.md` documents `game_sound_cue` as presentation-only and confirms
  it cannot alter game state.
- With sound disabled, all gameplay behaves exactly as it does now.
- With sound enabled, host and players hear the intended current loop and
  receive each action cue once.
- At a `100%` Game volume setting, loop gain starts near `0.1` and one-shot
  effect gain starts near `0.2`; lower slider values scale both together.
- There is exactly one in-game volume slider, with no separate music/effects
  volume controls.
- Reconnects, duplicate socket frames, a rejected autoplay attempt, and a
  missing audio file fail visibly or silently without breaking the game.

## 3. Add host lobby deletion on the home page

### Backend lifecycle changes

- Keep deletion owner-only.
- Extend the current deletion rule from only `created` to:

  ```text
  created | waiting_start
  ```

- Explicitly reject deletion of:

  ```text
  in_progress | completed
  ```

- When deleting a `waiting_start` lobby:
  - remove its database record and category associations;
  - delete its Redis game state;
  - cancel any registered game timer;
  - notify connected clients that the lobby was deleted;
  - close lobby namespace sockets so stale clients cannot keep acting on
    deleted state.
- Ensure the REST route performs socket/timer teardown only after the service
  has successfully completed the deletion path. Return a clear structured
  error if the lobby is not deletable.
- Do not add a destructive delete path for live games. A future cancel/archive
  design would need separate game-flow and data-retention decisions.

### Home-page UI

- Reuse `useDeleteLobby`, but add a dedicated accessible confirmation modal
  rather than relying only on a bare destructive button.
- Show **Delete lobby** only when `lobby.owner_id === currentUserId` and its
  state is `created` or `waiting_start`.
- Include lobby ID/state in the confirmation copy and explain that waiting
  players will be disconnected.
- Disable controls while deletion is pending; display server failures through
  the existing toast/error mechanism.
- If the owner deletes from a lobby page, handle `lobby_deleted`, stop the
  game socket/audio, show a message, and navigate to home.
- Invalidate lobby lists, lobby details, and owner-draft queries after
  deletion.

### Acceptance criteria

- Owners can delete their `created` and `waiting_start` lobbies from home.
- Non-owners never see a delete action and receive `403` if they call the API.
- `in_progress` and `completed` deletion is rejected by both UI and backend.
- A deleted waiting lobby no longer has Redis state, scheduled timers, or
  usable Socket.IO connections.

## 4. Replace lobby cards with a lobby browser

### Discovery contract

- Preserve `created` as a private draft state. Do not include other users’
  drafts in public discovery.
- Make the main browser query these public states:

  ```text
  waiting_start | in_progress | completed
  ```

- Add a separate **My drafts** section/query for the current owner’s
  `created` lobbies.
- Extend the lobby discovery response with a server-calculated roster count:
  - for materialized lobbies, count known non-host players from Redis game
    state, including disconnected roster members;
  - for an unmaterialized draft, return `0`;
  - if transient Redis state is unavailable for a non-draft lobby, return
    `null`/“Unavailable”, not a misleading zero.
- Keep the database repository responsible for SQL filtering/pagination and
  enrich its validated results in the service layer with Redis-only live
  roster data. Do not add raw SQL or database-specific behavior.

### Browser UI

- Replace the responsive card grid with a responsive table that keeps the
  existing dark/slate/amber visual language.
- Desktop columns:

  | Column | Content |
  | --- | --- |
  | Lobby ID | `#id` |
  | Host | owner username or deleted-user fallback |
  | Players | known player count / unavailable state |
  | State | human-readable status badge |
  | Categories | attached-category count |
  | Action | Join, View details, or Delete where allowed |

- Use this display mapping:

  | Internal state | Display label |
  | --- | --- |
  | `created` | Setup |
  | `waiting_start` | Waiting for players |
  | `in_progress` | In progress |
  | `completed` | Completed |

- On narrow screens, retain every field using stacked row labels or a
  horizontally scrollable table with an accessible fallback; do not silently
  hide state/action information.
- Add loading, empty, and refresh states. Keep periodic refresh for
  joinable/in-progress lobby state, but avoid aggressive polling.
- `waiting_start` uses **Join** and opens the existing live lobby route.
- `in_progress` and `completed` use **View details**:
  - show REST-backed lobby metadata, categories, host, state, and roster
    summary;
  - do not open a game socket for a user outside the locked roster;
  - do not imply spectator support.
- Show owner actions beside the normal action without making table rows
  ambiguous or click-to-delete.

### Acceptance criteria

- Users can scan ID, host, player count, state, category count, and action in
  one responsive browser.
- Public discovery includes waiting, live, and completed lobbies but never
  another owner’s private drafts.
- A user cannot accidentally attempt to join a locked/completed game from the
  browser.
- The display state labels match the table above, while API values remain
  unchanged.
- Owner-only delete controls work from both public waiting rows and My drafts.

## 5. Contract, tests, and verification

### Backend

- Generate the media schema migration with Alembic `--autogenerate`, review
  it, and confirm it uses portable SQLAlchemy model types.
- Add tests for:
  - media upload authentication, ownership, MIME validation, size limits, and
    deletion/reference rules;
  - valid and invalid prompt/media-type combinations;
  - media snapshotting into a waiting/running game;
  - answer secrecy for all new media prompt types;
  - deletable/non-deletable lobby state rules;
  - Redis state/timer/socket teardown for a deleted waiting lobby;
  - public versus private lobby discovery filters and player-count fallback;
  - validated server-issued sound-cue payloads and timer/action cue paths.
- After backend changes, always run in this exact order:

  ```bash
  cd be
  uv run ruff format src tests
  uv run ruff check --fix src tests
  ```

- Run `uv run pytest` only when explicitly requested.

### Frontend

- Add tests for:
  - text/image/audio/video authoring validation and preview states;
  - media rendering in `PromptStage` without autoplaying clue media;
  - no early expected-answer exposure for media prompts;
  - audio preference, autoplay rejection, loop cleanup, cue deduplication,
    and no one-shot replay on reconnect;
  - each cue-to-asset mapping;
  - browser table state labels, responsive semantics, actions, and empty
    states;
  - owner-only delete confirmation, pending state, and successful navigation;
  - View details not opening a game socket for non-roster users.
- Before frontend completion, run:

  ```bash
  cd fe
  bun run typecheck
  bun run lint
  bun run test
  bun run build
  ```

### Manual verification

Use one host browser profile plus at least two player profiles:

1. Enable sound independently in each browser and confirm muted users hear
   nothing.
2. Start a game, select a clue, buzz, judge correct/wrong, allow answer and
   buzz timeouts, reveal answers, and finish the board. Confirm each approved
   cue and loop transition plays once without changing gameplay.
3. Join after a game phase has already started; confirm only the current
   background loop starts after sound is enabled and old one-shots do not
   replay.
4. Block browser autoplay, then use **Enable sound** and verify graceful
   recovery.
5. Author and play one image, audio, and video prompt; verify mobile sizing,
   keyboard controls, and text-answer secrecy.
6. Delete a waiting lobby with connected users; confirm they receive the
   deleted state, return home, and cannot reconnect.
7. Inspect desktop and mobile lobby browser rows for all four display states.
   Confirm only waiting lobbies can be joined and only the owner sees allowed
   delete actions.

## Implementation order

1. Obtain approved soundtrack assets and record their license/attribution.
2. Define media asset schemas/storage configuration and create/review the
   Alembic migration.
3. Implement upload, delivery, prompt assignment, game snapshots, and backend
   tests.
4. Implement prompt authoring and `PromptStage` media rendering.
5. Add server-issued sound cues, then the frontend audio manager and controls.
6. Extend deletion lifecycle/teardown and add its confirmation UI.
7. Add enriched lobby discovery API and responsive lobby browser/details UI.
8. Update `GAME_FLOW.md`, `README.md`, deployment configuration, and asset
   documentation.
9. Run required checks and complete the multi-browser manual verification.

## Explicitly out of scope

- Answer images, answer audio, and answer video.
- Spectator game-state access for users outside the locked roster.
- Streaming, recording, voice chat, or sending spoken answers through the
  application.
- Downloading, hosting, or redistributing unlicensed television soundtrack
  recordings.
- Changing game timers, answer-reveal timing, scoring, or voice-answer rules.
