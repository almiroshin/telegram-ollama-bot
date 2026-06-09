#!/usr/bin/env bash
set -Eeuo pipefail

BOT_DIR="${BOT_DIR:-$HOME/telegram-ollama-bot}"
VENV_DIR="${VENV_DIR:-$BOT_DIR/venv}"
PYTHON_BIN="${PYTHON_BIN:-$VENV_DIR/bin/python}"
REMOTE="${REMOTE:-origin}"
BRANCH="${BRANCH:-main}"
LAUNCHD_LABEL="${LAUNCHD_LABEL:-com.surf.telegram-ollama-bot}"
PLIST_PATH="${PLIST_PATH:-$HOME/Library/LaunchAgents/$LAUNCHD_LABEL.plist}"

log() {
  printf '==> %s\n' "$1"
}

fail() {
  printf 'ERROR: %s\n' "$1" >&2
  exit 1
}

require_command() {
  command -v "$1" >/dev/null 2>&1 || fail "Required command not found: $1"
}

require_command git
require_command launchctl

[[ -d "$BOT_DIR" ]] || fail "Project directory not found: $BOT_DIR"

cd "$BOT_DIR"
[[ -d .git ]] || fail "No git repository found in $BOT_DIR"

if [[ -n "$(git status --porcelain)" ]]; then
  git status -sb
  fail "Working tree has local changes. Commit, stash, or discard them before deployment."
fi

log "Updating $BOT_DIR from $REMOTE/$BRANCH"
git fetch "$REMOTE" "$BRANCH"
git checkout "$BRANCH"
git pull --ff-only "$REMOTE" "$BRANCH"

if [[ ! -x "$PYTHON_BIN" ]]; then
  log "Creating virtual environment at $VENV_DIR"
  python3 -m venv "$VENV_DIR"
fi

log "Installing Python dependencies"
"$PYTHON_BIN" -m pip install -r requirements.txt

log "Checking Python syntax"
"$PYTHON_BIN" -m py_compile bot.py

if [[ ! -f "$PLIST_PATH" ]]; then
  fail "launchd plist not found: $PLIST_PATH"
fi

log "Restarting launchd service: $LAUNCHD_LABEL"
launchctl unload "$PLIST_PATH" >/dev/null 2>&1 || true
launchctl load "$PLIST_PATH"
launchctl start "$LAUNCHD_LABEL"

sleep 2

log "Deployment status"
"$BOT_DIR/scripts/status_macmini.sh"
