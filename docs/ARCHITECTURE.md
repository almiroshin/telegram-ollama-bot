# Architecture

## Purpose

The project implements a personal Telegram assistant backed by a local Ollama model. Telegram provides the user interface, while text generation, voice transcription, and document processing run locally on the machine that hosts the bot.

## Components

```mermaid
flowchart LR
    U["Telegram user"] --> TG["Telegram Bot API"]
    TG --> H["python-telegram-bot handlers"]
    H --> M["Prompt modes and chat history"]
    M --> O["Ollama Chat API"]
    O --> M
    H --> V["faster-whisper STT"]
    H --> D["Document text extraction"]
    D --> PDF["pypdf"]
    D --> DOCX["python-docx"]
    D --> OCR["pdf2image + Poppler + Tesseract"]
    V --> M
    D --> M
    M --> TG
```

## Entry Point

The main entry point is `main()` in [bot.py](../bot.py). It:

- delegates to `app.main.main()`;
- validates that `TELEGRAM_TOKEN` is set;
- logs the current runtime configuration;
- creates a `python-telegram-bot` `Application`;
- registers command handlers and message handlers;
- starts polling with `app.run_polling()`.

## Module Layout

```text
bot.py
app/
  __init__.py
  access.py
  config.py
  documents.py
  handlers.py
  llm.py
  main.py
  prompts.py
  stt.py
tests/
```

Responsibilities:

- `bot.py` - stable launchd-compatible entry point.
- `app/config.py` - environment parsing, typed settings, logging setup.
- `app/prompts.py` - system prompts and prompt modes.
- `app/access.py` - Telegram user allowlist.
- `app/llm.py` - Ollama Chat API client and in-memory conversation history.
- `app/stt.py` - `faster-whisper` model loading and transcription.
- `app/documents.py` - text extraction from TXT/MD/PDF/DOCX and OCR fallback.
- `app/handlers.py` - Telegram command and message handlers.
- `app/main.py` - application wiring and polling startup.

## Text Request Flow

1. The user sends a text message or command.
2. The handler selects a prompt mode: `default`, `email`, `rewrite`, `shorten`, `vip`, `surf`, `shell`, or `followup`.
3. `ask_ollama()` builds the request:
   - the system prompt for the selected mode;
   - the user's recent history;
   - the new user message.
4. The request is sent to `OLLAMA_URL` with `POST`.
5. The response is stored in `USER_HISTORY` and sent back to Telegram.

History is stored in process memory:

```text
USER_HISTORY[user_id] = [
    {"role": "user", "content": "..."},
    {"role": "assistant", "content": "..."}
]
```

After each response, history is trimmed to `MAX_HISTORY_MESSAGES`.

## Voice Messages

`handle_voice()` follows this flow:

1. Download the Telegram voice file into a temporary directory.
2. Lazily initialize `WhisperModel` through `get_stt_model()`.
3. Transcribe the audio in `transcribe_audio_file()`.
4. Build a dedicated prompt for the `voice` mode.
5. Send both the transcript and the processed summary back to the user.

The STT model is stored in the global `STT_MODEL` variable so it is not reloaded for every voice message.

## Documents

`handle_document()` follows this flow:

1. Validate file size with `MAX_FILE_SIZE_MB`.
2. Validate the extension: `.txt`, `.md`, `.pdf`, or `.docx`.
3. Download the file into a temporary directory.
4. Call `extract_text_from_file()`.
5. Trim extracted text with `trim_document_text()` if it exceeds `MAX_DOCUMENT_CHARS`.
6. Send the prepared text to Ollama using the `document` mode.

Text extraction strategy:

- `.txt`, `.md` - read with fallback encodings: `utf-8`, `utf-8-sig`, `cp1251`, `latin-1`.
- `.docx` - extract paragraphs and tables through `python-docx`.
- `.pdf` - first try direct extraction through `pypdf`; if the text layer is empty, run OCR.
- OCR - render pages through `pdf2image`, then recognize text with `pytesseract`.

## Configuration Model

Configuration is read from environment variables when the module is imported. Values are not reloaded while the process is running. After changing `.env` or shell environment variables, restart the bot.

## Responsibility Boundaries

The code now has a modular baseline. The next boundary worth extracting is persistent history, because `app/llm.py` still stores conversation state in process memory.

## Main Technical Risks

- Telegram user access control is disabled unless `ALLOWED_TELEGRAM_USER_IDS` is set.
- Conversation history is not persistent.
- Heavy OCR/STT work is executed inside handlers and can delay processing.
- Test coverage is still helper-level and does not cover Telegram/Ollama integration.
- No graceful shutdown, health endpoint, or metrics.
