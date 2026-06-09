#!/usr/bin/env bash
set -Eeuo pipefail

BOT_DIR="${BOT_DIR:-$HOME/telegram-ollama-bot}"
VENV_DIR="${VENV_DIR:-$BOT_DIR/venv}"
PYTHON_BIN="${PYTHON_BIN:-$VENV_DIR/bin/python}"
ENV_FILE="${ENV_FILE:-$BOT_DIR/.env}"

cd "$BOT_DIR"

if [[ ! -x "$PYTHON_BIN" ]]; then
  echo "Python interpreter not found or not executable: $PYTHON_BIN" >&2
  exit 1
fi

if [[ -f "$ENV_FILE" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "$ENV_FILE"
  set +a
fi

exec "$PYTHON_BIN" "$BOT_DIR/bot.py"
