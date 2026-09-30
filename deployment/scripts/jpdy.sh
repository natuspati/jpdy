#!/usr/bin/env bash
# Bring jpdy online via Tailscale Funnel. Ctrl+C takes it offline; data is kept.
set -euo pipefail
cd "$(dirname "$0")/.."
env_file=prod.env

if [[ ! -f $env_file ]]; then
  read -rp "Tailscale auth key (tskey-auth-...): " ts_key
  read -rp "Tailnet DNS name (e.g. tail1234.ts.net): " tailnet
  db_password=$(openssl rand -hex 24)
  sed -e "s|__TS_AUTHKEY__|$ts_key|" \
    -e "s|__TAILNET__|$tailnet|g" \
    -e "s|__SECRET_KEY__|$(openssl rand -hex 32)|" \
    -e "s|__DB_PASSWORD__|$db_password|g" \
    -e "s|__INVITE_CODE__|$(openssl rand -hex 4)|" \
    prod.env.example >"$env_file"
  chmod 600 "$env_file"
fi

docker info >/dev/null 2>&1 || colima start

# Separate project name keeps prod volumes apart from the local dev stack.
compose=(docker-compose -p jpdy-prod --env-file "$env_file"
  -f docker-compose.local.yml -f docker-compose.prod.yml)
trap '"${compose[@]}" down' EXIT
"${compose[@]}" up --build -d --wait

env_value() { grep "^$1=" "$env_file" | cut -d= -f2-; }
echo
echo "jpdy is live at $(env_value PUBLIC_URL)  (invite code: $(env_value BE_REGISTRATION_CODE))"
echo "Keeping the Mac awake; keep the lid open. Press Ctrl+C to shut down."
caffeinate -dis
