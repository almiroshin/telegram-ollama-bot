# Deployment

This project uses GitHub as the source of truth and the Mac mini as the production checkout.

## Current Production Profile

The current Mac mini setup uses:

| Setting | Value |
| --- | --- |
| Project directory | `~/telegram-ollama-bot` |
| Python virtual environment | `~/telegram-ollama-bot/venv` |
| launchd label | `com.surf.telegram-ollama-bot` |
| launchd plist | `~/Library/LaunchAgents/com.surf.telegram-ollama-bot.plist` |
| stdout log | `~/telegram-ollama-bot/bot.log` |
| stderr log | `~/telegram-ollama-bot/bot.err` |
| Git branch | `main` |

## Deployment Rule

Do not edit production code directly on the Mac mini. The preferred flow is:

1. Make changes in the development workspace.
2. Commit and push to GitHub.
3. SSH into the Mac mini.
4. Run the deployment script.

If an emergency hotfix is made directly on the Mac mini, commit and push it immediately or port it back into the development workspace before making more changes.

## One-Command Deploy

Run this on the Mac mini:

```bash
cd ~/telegram-ollama-bot
./scripts/deploy_macmini.sh
```

The script will:

1. Refuse to continue if the working tree has local changes.
2. Fetch and fast-forward `main` from GitHub.
3. Install dependencies from `requirements.txt`.
4. Compile-check `bot.py`.
5. Restart the launchd service.
6. Print deployment status and recent logs.

## Status Check

Run this on the Mac mini:

```bash
cd ~/telegram-ollama-bot
./scripts/status_macmini.sh
```

The script prints:

- Git branch and latest commit.
- Python interpreter path and version.
- launchd load status.
- running bot process.
- local Ollama availability.
- recent stdout and stderr logs.

## Bot Runtime

`launchd` should call:

```bash
/Users/almiroshin/telegram-ollama-bot/scripts/run_bot.sh
```

`run_bot.sh`:

- switches into the project directory;
- sources `.env` if it exists;
- starts `bot.py` through the project virtual environment.

## launchd Setup

An example plist is available at:

```text
launchd/com.surf.telegram-ollama-bot.plist.example
```

Install it on the Mac mini:

```bash
cd ~/telegram-ollama-bot
cp launchd/com.surf.telegram-ollama-bot.plist.example \
  ~/Library/LaunchAgents/com.surf.telegram-ollama-bot.plist
launchctl unload ~/Library/LaunchAgents/com.surf.telegram-ollama-bot.plist 2>/dev/null || true
launchctl load ~/Library/LaunchAgents/com.surf.telegram-ollama-bot.plist
launchctl start com.surf.telegram-ollama-bot
```

## Configuration

Keep secrets and runtime configuration in:

```text
~/telegram-ollama-bot/.env
```

Do not commit `.env`.

Minimum required value:

```text
TELEGRAM_TOKEN=...
ALLOWED_TELEGRAM_USER_IDS=...
```

Common Mac mini values:

```text
OLLAMA_URL=http://127.0.0.1:11434/api/chat
OLLAMA_MODEL=qwen3:8b
LOG_LEVEL=INFO
POPPLER_PATH=/opt/homebrew/bin
TESSERACT_CMD=/opt/homebrew/bin/tesseract
```

## Custom Paths

All scripts support environment overrides:

```bash
BOT_DIR=/path/to/bot \
VENV_DIR=/path/to/venv \
LAUNCHD_LABEL=com.example.bot \
./scripts/deploy_macmini.sh
```

Use this only when the production layout changes.
