#!/bin/bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"

echo "==> GICS Demo"
echo "Backend:  http://localhost:5001"
echo "Frontend: http://localhost:5173"
echo ""
echo "Start backend in one terminal:"
echo "  bash backend/start.sh"
echo ""
echo "Start frontend in another terminal:"
echo "  cd frontend && npm install && npm run dev"
