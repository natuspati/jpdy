# Jeopardy

Voice-answer Jeopardy with text, image, audio, and video clues. Players answer
over an external voice channel; the host judges. See [`GAME_FLOW.md`](GAME_FLOW.md)
for gameplay rules.

## Play online

Open the public URL shared by your host, typically
`https://jpdy.<tailnet>.ts.net`. It is available only while the host runs a
session; players do not need Docker or Tailscale installed.

Register with the host's private invite code, sign in, and join the waiting
lobby. Agree on a voice channel before playing. The host starts the game,
chooses a starting player, and judges spoken answers without scoring.
After the game starts, existing participants can reconnect but new players
cannot join.

## Deployment

Requires a running Docker engine with Linux containers, Compose v2.24.4+,
Git, GNU Make, and Bash (Git Bash on Windows).
Configure [Tailscale Funnel](https://tailscale.com/kb/1223/funnel) for public
HTTPS access.

### Configure Tailscale and `prod.env`

In the [Tailscale admin console](https://login.tailscale.com/admin):

1. Enable MagicDNS and HTTPS certificates; note your tailnet DNS name.
2. Allow Funnel in **Access controls**:
   `"nodeAttrs": [{"target": ["autogroup:member"], "attr": ["funnel"]}]`.
3. Generate an auth key under **Settings → Keys**. Make it **reusable**,
   **non-ephemeral**, and pre-approved if your tailnet requires device approval.
   An ephemeral key lets Tailscale purge the machine while the stack is down.
4. After the first start, open the `jpdy` machine and choose **Disable key
   expiry**. Check that it is named exactly `jpdy` (not `jpdy-1`).

```bash
cp deployment/prod.env.example deployment/prod.env
chmod 600 deployment/prod.env
```

Replace every placeholder in `deployment/prod.env`:

| Placeholder | Value |
| --- | --- |
| `__TAILNET__` | Full tailnet DNS name, e.g. `tail1234.ts.net` |
| `__TS_AUTHKEY__` | Tailscale auth key |
| `__DB_PASSWORD__` | Same generated password for `POSTGRES_PASSWORD` and `BE_DB_PASSWORD` |
| `__SECRET_KEY__` | Generated signing secret |
| `__INVITE_CODE__` | Private registration code to share with players |
| `__ADMIN_KEY__` | Private key that lets you claim the admin role (see below) |

Generate secrets with `openssl rand -hex 32` (use that for `__ADMIN_KEY__` too). Keep the environment file private
and untracked. Changing its database password does not update an existing
database's password.

### Manage sessions

Run from the repository root:

```bash
make start   # Start or update
make deploy  # Switch to main, pull latest, then start
make status  # Show container state, health, and ports
make stop    # Stop; keep data
```

Start runs `git pull --ff-only`, builds, and launches `jpdy-prod` in the
background, waiting for healthy services. A failed pull aborts startup.
Repeated starts update changed containers; unchanged ones keep running.
Status is read-only. Stop removes containers, leaving `jpdy-prod_*` data
volumes and the Docker engine intact; repeated stops are safe.

Verify the Tailscale DNS name matches `PUBLIC_URL` and `BE_ALLOWED_HOSTS`,
then check sign-in and lobby connectivity at the public URL.
No demo accounts are created. Register your host account, then share
`PUBLIC_URL` and the private `BE_REGISTRATION_CODE` with players.

To become an admin, sign in, open `/admin`, and enter `BE_ADMIN_KEY`. Each
account gets exactly one guess: a wrong key redirects home silently and spends
the attempt, while closing the form without submitting does not. Admins manage users and see
server health and game stats on that page. Without `BE_ADMIN_KEY` nobody can
claim the role, and an existing admin can promote others from the user list.
Deleting a user also deletes their unfinished lobbies and unused uploads;
completed lobbies stay as history.
Closing the terminal does not stop the session. On macOS, `make start` also runs
the built-in `caffeinate` so the host does not sleep until `make stop`
(`make status` shows whether it is running). That does not stop a closed lid on
battery: keep the Mac plugged in with the lid open or an external display, and
use wired Ethernet when you can. Do not run `make deploy` during a game; it can
recreate nginx and Tailscale and drop every player for a moment.

A fresh clone on another host does not
transfer accounts, categories, uploads, or the Tailscale identity.

### Tailscale recovery

`make start` ends by requesting `PUBLIC_URL/api/health` and warns if it does not
answer. The admin console showing the machine as connected does not prove the
public path works, so confirm from a phone on cellular. If the container is
healthy and localhost works but the public URL does not:

1. In the admin console, delete the `jpdy` machine (and any `jpdy-1`).
2. Generate a new reusable, non-ephemeral auth key and put it in
   `deployment/prod.env` as `TS_AUTHKEY`.
3. Run `make start`. Tailscale ignores `TS_AUTHKEY` while it holds saved state,
   so if it still does not register, run `make stop`, delete the
   `jpdy-prod_jpdy_tailscale_state` volume, and start again.

Never run `docker volume prune` or `docker system prune --volumes` while the
stack is stopped: the state volume looks unused and the node would re-register
under a new name that no longer matches `PUBLIC_URL`.

## Development

With Docker running, run from the repository root:

```bash
# First setup only:
cp deployment/local.env.example deployment/local.env

make dev-start   # Start or update
make dev-status  # Show container state, health, and ports
make dev-stop    # Stop; keep data
```

Open `http://localhost:8080`. The development stack includes five categories
with 25 clues and these accounts:

| Role | Username | Password |
| --- | --- | --- |
| Host | host | host123 |
| Player | alice | alice123 |
| Player | bob | bob123 |
| Player | carol | carol123 |
| Admin | admin | admin123 |

Use separate browser profiles for test users. As host, create a lobby and
assign categories to one to three rounds (each category can be used once, so
the five seeded ones are shared across rounds) and optionally set the number of
betting prompts per round, then join from the player profiles.

Implementation details are in the [backend README](be/README.md) and
[frontend README](fe/README.md); contributor conventions are in
[`AGENTS.md`](AGENTS.md).
