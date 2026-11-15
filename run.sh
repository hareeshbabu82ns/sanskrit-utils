#!/usr/bin/env bash
# Local dev runner: creates .venv if missing, (re)installs requirements when
# requirements.txt changes, loads .env, and starts the API from inside .venv.
#
#   ./run.sh            start the API (http://HOST:PORT/graphql)
#   ./run.sh --install  only set up the venv / install requirements
set -euo pipefail
cd "$(dirname "$0")"

VENV=.venv
PY=${PYTHON:-python3}
STAMP="$VENV/.requirements.sha"

if [ ! -x "$VENV/bin/python" ]; then
  echo ">> creating virtualenv in $VENV"
  "$PY" -m venv "$VENV"
fi

# shellcheck disable=SC1091
source "$VENV/bin/activate"

req_sha=$(sha256sum requirements.txt | cut -d' ' -f1)
if [ ! -f "$STAMP" ] || [ "$(cat "$STAMP")" != "$req_sha" ]; then
  echo ">> installing requirements"
  python -m pip install --upgrade pip
  python -m pip install -r requirements.txt
  echo "$req_sha" > "$STAMP"
fi

[ "${1:-}" = "--install" ] && { echo ">> environment ready"; exit 0; }

if [ -f .env ]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi

HOST="${HOST:-0.0.0.0}"
PORT="${PORT:-5000}"
export HOST PORT

if [ "$HOST" = "0.0.0.0" ]; then
  host_ip=$(hostname -I 2>/dev/null | awk '{print $1}' || true)
  if [ -z "$host_ip" ]; then
    host_ip=$(ip -4 route get 1.1.1.1 2>/dev/null | awk '{print $7}' || true)
  fi
  if [ -z "$host_ip" ]; then
    host_ip=$(ip -4 addr show scope global 2>/dev/null | awk '/inet / {print $2}' | cut -d/ -f1 | head -n1 || true)
  fi
  if [ -z "$host_ip" ]; then
    host_ip=$(awk '/^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+/ && !/^127\./ {print $1; exit}' /etc/hosts 2>/dev/null || true)
  fi

  echo ">> starting API on:"
  echo "   - Local:    http://127.0.0.1:${PORT}/graphql"
  if [ -n "$host_ip" ] && [ "$host_ip" != "127.0.0.1" ]; then
    echo "   - Host IP:  http://${host_ip}:${PORT}/graphql"
  fi
else
  echo ">> starting API on http://${HOST}:${PORT}/graphql"
fi
exec python app.py
