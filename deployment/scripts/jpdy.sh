#!/usr/bin/env bash
# Manage the detached production stack (dev-* for the local dev stack); data is kept.
set -euo pipefail
cd "$(dirname "$0")/../.."
action=${1:-start}
dev=false
if [[ $action == dev-* ]]; then
  dev=true
  action=${action#dev-}
fi

if [[ $# -gt 1 || ( $action != start && $action != stop && $action != status ) ]]; then
  echo "Usage: $0 [start|stop|status|dev-start|dev-stop|dev-status]" >&2
  exit 1
fi

if $dev; then env_file=deployment/local.env stop_cmd=dev-stop; else env_file=deployment/prod.env stop_cmd=stop; fi

if [[ ! -f $env_file ]]; then
  echo "Configure $env_file first; see README.md." >&2
  exit 1
fi

if ! docker info >/dev/null 2>&1; then
  echo "Docker is unavailable. Start Docker Desktop, Docker Engine, or Colima (colima start), then retry." >&2
  exit 1
fi

if docker compose version >/dev/null 2>&1; then
  compose=(docker compose)
elif command -v docker-compose >/dev/null 2>&1 && docker-compose version >/dev/null 2>&1; then
  compose=(docker-compose)
else
  echo "Install Docker Compose v2 (docker compose or docker-compose), then retry." >&2
  exit 1
fi

# Separate project name keeps prod volumes apart from the local dev stack.
# Dev keeps Compose's default project so it matches the README commands and volumes.
if $dev; then
  compose+=(--env-file "$env_file" -f deployment/docker-compose.local.yml)
else
  compose+=(-p jpdy-prod --env-file "$env_file"
    -f deployment/docker-compose.local.yml -f deployment/docker-compose.prod.yml)
fi

# Keep the prod Mac awake while the stack runs (macOS built-in; skipped elsewhere and for dev).
awake_pid_file=${TMPDIR:-/tmp}/jpdy-prod-caffeinate.pid
awake_running() {
  [[ -f $awake_pid_file ]] || return 1
  local pid; pid=$(<"$awake_pid_file")
  [[ $(ps -p "$pid" -o comm= 2>/dev/null) == *caffeinate ]]
}

case $action in
  start)
    $dev || git pull --ff-only
    "${compose[@]}" up --build -d --wait
    echo "jpdy is running in the background. Stop with: bash deployment/scripts/jpdy.sh $stop_cmd"
    if ! $dev && command -v caffeinate >/dev/null && ! awake_running; then
      nohup caffeinate -dimsu >/dev/null 2>&1 &
      echo $! >"$awake_pid_file"
      echo "Keeping this Mac awake until stop (caffeinate)."
    fi
    if ! $dev; then
      # A healthy container does not prove Funnel works; ask the public URL itself.
      public_url=$(sed -n 's/^PUBLIC_URL=//p' "$env_file" | head -n 1)
      for _ in {1..12}; do
        curl -fsS -m 10 -o /dev/null "$public_url/api/health" 2>/dev/null && reachable=true && break
        sleep 5
      done
      if [[ ${reachable:-false} == true ]]; then
        echo "Public URL is reachable: $public_url"
      else
        echo "WARNING: $public_url did not answer. Check it from a phone on cellular; if it is" >&2
        echo "down, see 'Tailscale recovery' in README.md (new auth key, delete the old machine)." >&2
      fi
    fi
    ;;
  stop)
    "${compose[@]}" down
    if ! $dev && awake_running; then kill "$(<"$awake_pid_file")"; fi
    rm -f "$awake_pid_file"
    echo "jpdy is stopped; data volumes are kept."
    ;;
  status)
    "${compose[@]}" ps --all
    if ! $dev; then awake_running && echo "Keep-awake: running" || echo "Keep-awake: not running"; fi
    ;;
esac
