#!/bin/bash
# Levanta backend + frontend en modo local
# Uso: ./dev.sh

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"

trap 'kill 0' EXIT

echo ">> Levantando backend en :8000..."
(
  cd "$ROOT_DIR/backend"
  if [ ! -d .venv ]; then
    echo "Creando venv..."
    python3 -m venv .venv
    .venv/bin/pip install -r requirements.txt
  fi
  .venv/bin/uvicorn app.main:app --reload --port 8000
) &

echo ">> Levantando frontend en :5173..."
(
  cd "$ROOT_DIR/frontend"
  npm run dev
) &

echo ""
echo ">> Todo corriendo: frontend http://localhost:5173  |  backend http://localhost:8000"
echo ">> Ctrl+C para frenar ambos"
wait
