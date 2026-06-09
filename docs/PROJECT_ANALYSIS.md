# Project Analysis

## Executive Summary

This project is a personal local AI assistant exposed through Telegram. It already covers practical workflows: business writing, rewriting, follow-ups, shell help, voice notes, and document analysis. The implementation is compact and easy to understand, but it is currently closer to a working prototype than a production-ready service.

## What Works Well

- Simple architecture with very little infrastructure.
- Key processing dependencies can run locally: Ollama, `faster-whisper`, and Tesseract.
- Prompt modes match practical business workflows.
- Voice messages and documents are available through the same Telegram interface.
- PDF processing has an OCR fallback.
- Runtime configuration is controlled through environment variables.
- File size, document text, and OCR page limits are already present.

## Functional Coverage

| Area | Status | Notes |
| --- | --- | --- |
| Text chat | Available | Through the Ollama Chat API. |
| Prompt modes | Available | Hardcoded in `MODES`. |
| History | Available | In-memory, keyed by Telegram user ID. |
| Voice | Available | `faster-whisper`, Russian language. |
| TXT/MD | Available | Multiple fallback encodings. |
| PDF | Available | Direct text extraction through `pypdf`. |
| PDF OCR | Available | `pdf2image` + Tesseract. |
| DOCX | Available | Paragraphs and tables. |
| User access control | Missing | A user allowlist is needed. |
| Persistence | Missing | History is lost on restart. |
| Tests | Missing | At least pure function unit tests are needed. |
| RAG | Missing | Long documents are currently truncated. |

## Strengths

- Fast to start and easy to inspect: one file and few moving parts.
- Local-first design: data does not need to leave the host machine for external LLM APIs.
- Business-focused prompt modes are already useful.
- OCR makes the bot useful for scans and procurement-style documents.

## Main Risks

### 1. No Access Control

Anyone who can message the bot can use the local LLM and document processing capabilities. For a personal bot, this is the highest operational risk.

Recommendation: add `ALLOWED_TELEGRAM_USER_IDS` and check it at the beginning of every handler.

### 2. One Large File

`bot.py` contains configuration, prompts, handlers, the LLM client, STT, OCR, and document parsing. This is acceptable for a prototype, but it will slow down testing and development as the project grows.

Recommendation: split the code into `app/config.py`, `app/llm.py`, `app/documents.py`, `app/stt.py`, and `app/telegram_handlers.py`.

### 3. Heavy Work Inside Handlers

OCR and STT can take noticeable time and currently run directly inside handlers. This is acceptable for one user, but it will become a problem as workload grows.

Recommendation: add a task queue or a bounded background executor.

### 4. Raw Errors Are Sent To Users

Responses that include raw Ollama exception details are useful during development, but they can reveal environment details in regular usage.

Recommendation: send short safe errors to users and write details to logs.

### 5. Long Documents Are Truncated

`MAX_DOCUMENT_CHARS` protects the context window, but only the first part of a document is analyzed. For specifications, tenders, and contracts, this can produce incomplete conclusions.

Recommendation: add chunking/RAG or at least a map-reduce summarization flow.

## Recommended Target Architecture

```text
app/
  __init__.py
  main.py
  config.py
  prompts.py
  llm.py
  history.py
  access.py
  telegram_handlers.py
  stt.py
  documents.py
  ocr.py
  logging_config.py
tests/
  test_documents.py
  test_history.py
  test_access.py
```

Minimum refactoring sequence:

1. Keep `requirements.txt`, `.env.example`, and documentation current.
2. Add a user allowlist without changing the overall structure.
3. Move pure document parsing functions into a separate module.
4. Add tests for those functions.
5. Extract the Ollama client and Telegram handlers.

## Near-Term Technical Tasks

- Add a Telegram user allowlist.
- Add a proper logger.
- Add `.env` loading through `python-dotenv` or explicitly document shell export.
- Add `pytest`.
- Split long responses to respect Telegram message limits.
- Add retry/backoff for Ollama.
- Make STT language configurable through environment variables.
- Improve PDF handling with partial OCR: direct parsing plus OCR only for empty pages.

## Conclusion

The project is already useful as a personal local assistant. The main engineering priority is to stabilize the foundation before adding more features: access control, structure, tests, logs, and heavy-task handling. After that, RAG and persistent memory will be much easier to add safely.
