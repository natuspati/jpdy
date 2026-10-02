# Jeopardy

Voice-answer Jeopardy with text, image, audio, and video clues. Players answer
over an external voice channel; the host judges. See [`GAME_FLOW.md`](GAME_FLOW.md)
for gameplay rules.

React/TypeScript frontend, FastAPI backend, PostgreSQL for persistent data,
Redis for live games, and Nginx for the browser entry point. Run the app with
Docker Compose; SQLite is used only for tests.

## Development stack

Start Docker, then run from the repository root:

```bash
# First setup only:
cp deployment/local.env.example deployment/local.env

docker compose --env-file deployment/local.env \
  -f deployment/docker-compose.local.yml up --build -d --wait
```

Open `http://localhost:8080`. PostgreSQL (`localhost:5432`) and Redis
(`localhost:6379`) are also available locally for IDE access.

Compose applies Alembic migrations and seeds five categories with 25 clues:

| Role | Username | Password |
| --- | --- | --- |
| Host | host | host123 |
| Player | alice | alice123 |
| Player | bob | bob123 |
| Player | carol | carol123 |

Use separate browser profiles for test users. As host, create a lobby and
select categories; players join before the host starts. The host does not score.
Once started, only existing participants can reconnect.

## Host a game night

The game-night overlay skips demo accounts and exposes the app publicly through
[Tailscale Funnel](https://tailscale.com/kb/1223/funnel). Players do not need
Tailscale installed.

### One-time setup

In the [Tailscale admin console](https://login.tailscale.com/admin):

1. Enable MagicDNS and HTTPS certificates; note your tailnet DNS name.
2. Allow Funnel in **Access controls**:
   `"nodeAttrs": [{"target": ["autogroup:member"], "attr": ["funnel"]}]`.
3. Generate an auth key under **Settings → Keys**.

```bash
cp deployment/prod.env.example deployment/prod.env
chmod 600 deployment/prod.env
```

Replace all `__PLACEHOLDERS__` with your tailnet name, auth key, database
password, JWT secret, and private registration code. Generate secrets with
`openssl rand -hex 32`. Never commit or share the environment file.

### Start a session

Start Docker, then run:

```bash
git pull --ff-only
docker compose -p jpdy-prod --env-file deployment/prod.env \
  -f deployment/docker-compose.local.yml \
  -f deployment/docker-compose.prod.yml up --build -d --wait
```

Verify the device's Tailscale DNS name matches `PUBLIC_URL` and
`BE_ALLOWED_HOSTS`. For infrequent sessions, consider disabling device key
expiry. Open the public URL and check sign-in and lobby connectivity.

Register your host account, then privately share `BE_REGISTRATION_CODE` with
players. Keep the host awake and online throughout the session.

### Stop a session

```bash
docker compose -p jpdy-prod --env-file deployment/prod.env \
  -f deployment/docker-compose.local.yml \
  -f deployment/docker-compose.prod.yml down
```

Data stays in `jpdy-prod_*` volumes. A fresh clone on another host does not
transfer accounts, categories, uploads, or the Tailscale identity.

## Configuration and data

- Always pass the appropriate `--env-file`. Environment files are gitignored.
- Keep `POSTGRES_PASSWORD` and `BE_DB_PASSWORD` identical. Changing them does
  not update an existing database's password.
- `BE_ALLOWED_HOSTS` must match the browser origin, including its port.
- PostgreSQL, Redis, and uploaded media persist in Docker volumes. Nginx serves
  media from a read-only mount; FastAPI validates uploads.
- To check multiple backend workers, set `BE_WORKERS_COUNT=2` in `local.env`
  and rerun development startup. Restore `1` afterwards.

**Destructive reset:** `down -v` deletes the selected stack's volumes.
For a clean development database, live state, and media storage:

```bash
docker compose --env-file deployment/local.env \
  -f deployment/docker-compose.local.yml down -v
```

Restart with the development command to recreate and seed the stack. Do not
use `-v` for ordinary shutdown.

## Optional GitHub Actions deployment

A self-hosted runner can run the same Compose command using a manual
`workflow_dispatch` trigger. Start the runner and Docker first; keep deployment
secrets outside the Actions checkout and never run untrusted PR code on it.

Actions cannot power on the host; offline jobs
[fail after 24 hours queued](https://docs.github.com/en/actions/reference/runners/self-hosted-runners#routing-precedence-for-self-hosted-runners).
For occasional sessions, manual pull-and-start is simpler. No workflow is configured.
