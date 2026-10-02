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
Git, and Bash (Git Bash on Windows). GNU Make is optional.
Configure [Tailscale Funnel](https://tailscale.com/kb/1223/funnel) for public
HTTPS access.

### Configure Tailscale and `prod.env`

In the [Tailscale admin console](https://login.tailscale.com/admin):

1. Enable MagicDNS and HTTPS certificates; note your tailnet DNS name.
2. Allow Funnel in **Access controls**:
   `"nodeAttrs": [{"target": ["autogroup:member"], "attr": ["funnel"]}]`.
3. Generate an auth key under **Settings → Keys**.

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

Generate secrets with `openssl rand -hex 32`. Keep the environment file private
and untracked. Changing its database password does not update an existing
database's password.

### Manage sessions

Run from the repository root:

```bash
make start   # Start or update
make status  # Show container state, health, and ports
make stop    # Stop; keep data
```

Without Make, use `bash deployment/scripts/jpdy.sh start` (or `status` / `stop`).
The script prefers `docker compose`, falling back to `docker-compose` v2.

Start runs `git pull --ff-only`, builds, and launches `jpdy-prod` in the
background, waiting for healthy services. A failed pull aborts startup.
Repeated starts update changed containers; unchanged ones keep running.
Status is read-only. Stop removes containers, leaving `jpdy-prod_*` data
volumes and the Docker engine intact; repeated stops are safe.

Verify the Tailscale DNS name matches `PUBLIC_URL` and `BE_ALLOWED_HOSTS`,
then check sign-in and lobby connectivity at the public URL.
No demo accounts are created. Register your host account, then share
`PUBLIC_URL` and the private `BE_REGISTRATION_CODE` with players.
Keep the host awake and online; closing the terminal does not stop the session.
For infrequent sessions, consider disabling Tailscale device key expiry.

A fresh clone on another host does not
transfer accounts, categories, uploads, or the Tailscale identity.

## Development

With Docker running, run from the repository root:

```bash
# First setup only:
cp deployment/local.env.example deployment/local.env

docker compose --env-file deployment/local.env \
  -f deployment/docker-compose.local.yml up --build -d --wait
```

Open `http://localhost:8080`. The development stack includes five categories
with 25 clues and these accounts:

| Role | Username | Password |
| --- | --- | --- |
| Host | host | host123 |
| Player | alice | alice123 |
| Player | bob | bob123 |
| Player | carol | carol123 |

Use separate browser profiles for test users. As host, create a lobby and
select categories, then join from the player profiles.

Stop the development stack with:

```bash
docker compose --env-file deployment/local.env \
  -f deployment/docker-compose.local.yml down
```

Add `-v` only for a **destructive reset**: it deletes accounts, categories,
live games, and uploads. Restart to recreate the seeded development data.

Implementation details are in the [backend README](be/README.md) and
[frontend README](fe/README.md); contributor conventions are in
[`AGENTS.md`](AGENTS.md).
