# SURF Telegram Ollama Bot

A local Telegram bot powered by Ollama. It works as a general AI assistant for daily work and as a specialized pre-sales and delivery assistant for SURF Consulting's IT infrastructure, supply, tender, and consulting workflows.

The project is implemented as a small Python application with [bot.py](bot.py) as the entry point and the main runtime code split across the [app](app) package. Telegram is the current user interface, with eXpress planned as the next corporate channel. Ollama provides the local LLM backend, `faster-whisper` handles speech-to-text, and Tesseract/Poppler are used for OCR and PDF processing.

## Features

- Local text chat through the Ollama Chat API.
- Per-user short-term conversation history persisted in SQLite.
- Owner-managed access requests and SQLite-backed user approvals.
- General assistant workflows for writing, rewriting, shortening, shell help, voice notes, and document analysis.
- Current Telegram interface with a planned channel adapter path for eXpress.
- SURF business prompt modes:
  - `/audit` - prepare IT landscape audit and discovery questions.
  - `/proposal` - draft a commercial proposal structure.
  - `/tender` - analyze tenders, RFPs, and technical specifications.
  - `/vendor` - compare vendor alternatives and mark supplier checks.
  - `/risk` - review project, delivery, logistics, security, and commercial risks.
- General business prompt modes:
  - `/email` - draft a business email.
  - `/rewrite` - rewrite and improve text.
  - `/shorten` - make text shorter and stronger.
  - `/vip` - prepare concise text for senior executives or government officials.
  - `/surf` - write in a SURF Consulting-style enterprise tone.
  - `/shell` - help with macOS/Linux terminal commands.
  - `/followup` - prepare a meeting follow-up.
- Utility commands:
  - `/start` - show help.
  - `/status` - check Ollama and runtime settings.
  - `/model` - show the current Ollama model.
  - `/reset` - clear the current user's chat history.
  - `/myid` - show the current Telegram user ID.
  - `/request_access` - request access from the bot owner.
- Owner commands:
  - `/users` - list owners and managed users.
  - `/approve <telegram_id>` - approve a pending user.
  - `/deny <telegram_id>` - deny a pending user.
  - `/revoke <telegram_id>` - revoke an approved user.
- Voice messages with local transcription through `faster-whisper`.
- Document analysis for `.txt`, `.md`, `.pdf`, and `.docx`.
- OCR fallback for PDFs without a text layer.

## Documentation

- [Architecture](docs/ARCHITECTURE.md)
- [Channel Integrations](docs/CHANNEL_INTEGRATIONS.md)
- [SURF Business Context](docs/SURF_BUSINESS_CONTEXT.md)
- [Deployment](docs/DEPLOYMENT.md)
- [Operations](docs/OPERATIONS.md)
- [Roadmap](docs/ROADMAP.md)
- [Project Analysis](docs/PROJECT_ANALYSIS.md)

## Requirements

- Python 3.10+.
- A running Ollama instance.
- A Telegram bot token from BotFather.
- System utilities for OCR and PDF rendering:
  - macOS: `poppler`, `tesseract`, Tesseract language packs.
  - Linux: `poppler-utils`, `tesseract-ocr`, `tesseract-ocr-rus`.

Python dependencies are listed in [requirements.txt](requirements.txt).

## Quick Start On macOS

```bash
brew install ollama poppler tesseract tesseract-lang
ollama pull qwen3:8b
```

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

```bash
cp .env.example .env
```

Set `TELEGRAM_TOKEN` in `.env`, then export the variables and start the bot:

```bash
set -a
source .env
set +a
python bot.py
```

Ollama must be reachable through `OLLAMA_URL`. The default endpoint is:

```text
http://127.0.0.1:11434/api/chat
```

## Configuration

Main environment variables:

| Variable | Default | Purpose |
| --- | --- | --- |
| `TELEGRAM_TOKEN` | none | Telegram bot token. Required. |
| `OWNER_TELEGRAM_USER_IDS` | empty | Comma or space separated Telegram user IDs that can approve, deny, revoke, and list users. |
| `ALLOWED_TELEGRAM_USER_IDS` | empty | Legacy/bootstrap allowlist. If owners are not configured, these users are treated as owners for compatibility. |
| `OLLAMA_URL` | `http://127.0.0.1:11434/api/chat` | Ollama Chat API endpoint. |
| `OLLAMA_MODEL` | `qwen3:8b` | Ollama model name. |
| `MAX_HISTORY_MESSAGES` | `12` | Number of recent messages kept in active context and retained per user. |
| `HISTORY_DB_PATH` | `bot.sqlite` | SQLite database path for conversation history and managed users. |
| `LOG_LEVEL` | `INFO` | Python logging level. |
| `WHISPER_MODEL_SIZE` | `small` | `faster-whisper` model size. |
| `WHISPER_DEVICE` | `cpu` | STT device: `cpu`, `cuda`, or `auto`. |
| `WHISPER_COMPUTE_TYPE` | `int8` | `faster-whisper` compute type. |
| `MAX_FILE_SIZE_MB` | `20` | Maximum Telegram document size. |
| `MAX_DOCUMENT_CHARS` | `18000` | Maximum extracted document text sent to the LLM. |
| `OCR_DPI` | `200` | DPI used when rendering PDF pages for OCR. |
| `OCR_LANG` | `rus+eng` | Tesseract OCR languages. |
| `MAX_OCR_PAGES` | `20` | Maximum number of PDF pages processed by OCR. |
| `POPPLER_PATH` | `/opt/homebrew/bin` | Path to Poppler binaries on macOS/Homebrew. |
| `TESSERACT_CMD` | `/opt/homebrew/bin/tesseract` | Path to the Tesseract binary. |

A complete example is available in [.env.example](.env.example).

## Verification

Check Python syntax without writing bytecode cache:

```bash
python3 -c 'import ast, pathlib; [ast.parse(path.read_text()) for path in pathlib.Path(".").glob("app/*.py")]; ast.parse(pathlib.Path("bot.py").read_text())'
```

Check Ollama:

```bash
curl http://127.0.0.1:11434/api/tags
```

Run unit tests:

```bash
python3 -m unittest discover -s tests
```

After starting the bot, send this command in Telegram:

```text
/status
```

## Access Management

For production, set `OWNER_TELEGRAM_USER_IDS` in `.env`. Unknown users can send `/start` or `/request_access`; the bot stores a pending request and sends the owner approval commands:

```text
/approve <telegram_id>
/deny <telegram_id>
```

Approved users are stored in SQLite and can use the bot without changing `.env`. Owners remain configured in `.env`, so they cannot be revoked accidentally through Telegram commands.

## Current Limitations

- Conversation history is persisted in SQLite, but there is no `/history` inspection command yet.
- There is no case workspace yet for customer opportunities, tenders, and proposal drafts.
- eXpress is planned, but the current runtime channel is Telegram only.
- Vendor, stock, price, warranty, and delivery facts are not backed by a structured source of truth yet.
- Access control is disabled unless `OWNER_TELEGRAM_USER_IDS` or the legacy `ALLOWED_TELEGRAM_USER_IDS` is set.
- Heavy OCR/STT work still runs inside Telegram handlers.
- Documents longer than `MAX_DOCUMENT_CHARS` are truncated; RAG/document indexing for long tenders and specifications is not implemented yet.
- Automated tests currently cover helper logic only; Telegram/Ollama integration tests are not implemented yet.

## Recommended Next Step

Next, add a minimal case workspace for customer opportunities, then improve tender/document intelligence.
