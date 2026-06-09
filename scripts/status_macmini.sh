#!/usr/bin/env bash
set -Eeuo pipefail

BOT_DIR="${BOT_DIR:-$HOME/telegram-ollama-bot}"
VENV_DIR="${VENV_DIR:-$BOT_DIR/venv}"
PYTHON_BIN="${PYTHON_BIN:-$VENV_DIR/bin/python}"
LAUNCHD_LABEL="${LAUNCHD_LABEL:-com.surf.telegram-ollama-bot}"
LOG_FILE="${LOG_FILE:-$BOT_DIR/bot.log}"
ERR_FILE="${ERR_FILE:-$BOT_DIR/bot.err}"
ENV_FILE="${ENV_FILE:-$BOT_DIR/.env}"
OLLAMA_TAGS_URL="${OLLAMA_TAGS_URL:-http://127.0.0.1:11434/api/tags}"

if [[ -f "$ENV_FILE" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "$ENV_FILE"
  set +a
fi

HISTORY_DB_PATH="${HISTORY_DB_PATH:-bot.sqlite}"

if [[ "$HISTORY_DB_PATH" != /* ]]; then
  HISTORY_DB_PATH="$BOT_DIR/$HISTORY_DB_PATH"
fi

print_section() {
  printf '\n== %s ==\n' "$1"
}

print_section "Project"
printf 'BOT_DIR: %s\n' "$BOT_DIR"

if [[ -d "$BOT_DIR/.git" ]]; then
  cd "$BOT_DIR"
  git status -sb
  git log -1 --oneline
else
  printf 'No git repository found at %s\n' "$BOT_DIR"
fi

print_section "Python"
if [[ -x "$PYTHON_BIN" ]]; then
  printf 'PYTHON_BIN: %s\n' "$PYTHON_BIN"
  "$PYTHON_BIN" --version
else
  printf 'Python interpreter not found: %s\n' "$PYTHON_BIN"
fi

print_section "launchd"
if launchctl print "gui/$(id -u)/$LAUNCHD_LABEL" >/dev/null 2>&1; then
  printf 'Loaded: %s\n' "$LAUNCHD_LABEL"
else
  printf 'Not loaded: %s\n' "$LAUNCHD_LABEL"
fi

print_section "Process"
if pgrep -fl "$BOT_DIR/bot.py" >/dev/null 2>&1; then
  pgrep -fl "$BOT_DIR/bot.py"
else
  printf 'No running bot.py process found for %s\n' "$BOT_DIR"
fi

print_section "Ollama"
if command -v curl >/dev/null 2>&1 && curl -fsS "$OLLAMA_TAGS_URL" >/dev/null; then
  printf 'Ollama is reachable: %s\n' "$OLLAMA_TAGS_URL"
else
  printf 'Ollama check failed: %s\n' "$OLLAMA_TAGS_URL"
fi

print_section "History"
printf 'HISTORY_DB_PATH: %s\n' "$HISTORY_DB_PATH"

if [[ -f "$HISTORY_DB_PATH" ]]; then
  wc -c "$HISTORY_DB_PATH"
else
  printf 'History database not found yet.\n'
fi

print_section "Logs"
if [[ -f "$LOG_FILE" ]]; then
  printf '%s\n' "--- tail: $LOG_FILE ---"
  tail -n 40 "$LOG_FILE"
else
  printf 'Log file not found: %s\n' "$LOG_FILE"
fi

if [[ -f "$ERR_FILE" ]]; then
  printf '%s\n' "--- tail: $ERR_FILE ---"
  tail -n 40 "$ERR_FILE"
else
  printf 'Error log file not found: %s\n' "$ERR_FILE"
fi
