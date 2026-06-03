#!/bin/bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
ICSGNN_DIR="$ROOT/ICSGNN"

cd "$ICSGNN_DIR"

if [ -d "venv" ]; then
  # shellcheck disable=SC1091
  source venv/bin/activate
fi

export PYTHONPATH="$ICSGNN_DIR:${PYTHONPATH:-}"

echo "Starting GICS backend API on http://localhost:5001"
python run_api.py
