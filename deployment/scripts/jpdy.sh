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

case $action in
  start)
    $dev || git pull --ff-only
    "${compose[@]}" up --build -d --wait
    echo "jpdy is running in the background. Stop with: bash deployment/scripts/jpdy.sh $stop_cmd"
    ;;
  stop)
    "${compose[@]}" down
    echo "jpdy is stopped; data volumes are kept."
    ;;
  status)
    "${compose[@]}" ps --all
    ;;
esac
