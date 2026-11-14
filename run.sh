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

echo ">> starting API on http://${HOST:-127.0.0.1}:${PORT:-5000}/graphql"
exec python app.py
