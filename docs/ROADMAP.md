# Roadmap

## Current Status

The project is a working personal prototype. Core workflows are already available: text chat, prompt modes, voice transcription, document analysis, and PDF OCR. The next major step is to turn the prototype into a maintainable service with access control, tests, modular structure, and reliable handling of heavy workloads.

## Development Principles

- Prioritize security and operability before adding more features.
- Preserve the fast Telegram-based user experience.
- Keep local processing as the default strength of the project.
- Evolve document workflows toward RAG instead of only increasing context size.
- Add tests around logic that is easy to break: routing, parsing, limits, and external errors.

## Phase 0. Stabilization

Goal: make the current bot safer and easier to reproduce without a major rewrite.

- Add a Telegram user allowlist. Done in the first Phase 0 increment.
- Hide low-level errors from normal user responses and write details to logs. Started in the first Phase 0 increment.
- Replace `print` with `logging`. Done in the first Phase 0 increment.
- Keep `README`, `.env.example`, `requirements.txt`, and operations documentation up to date.
- Add basic smoke checks: syntax, configuration import, and unit tests for pure functions. Started in the first Phase 0 increment.
- Document the minimum supported Python version.

Readiness criteria:

- a new user can start the bot from the documentation;
- unknown Telegram users cannot use the bot;
- local verification can be run with one command.

## Phase 1. Modular Structure

Goal: stop `bot.py` from becoming the whole application and separate domain logic from Telegram handlers.

Current structure:

```text
app/
  config.py
  access.py
  prompts.py
  llm.py
  handlers.py
  stt.py
  documents.py
tests/
```

Tasks:

- Move environment configuration into typed settings. Done.
- Move prompts into a separate module. Done.
- Extract the Ollama client. Done.
- Extract document handling and STT. Done.
- Add unit tests that do not require real Telegram or Ollama. Started.

Readiness criteria:

- `bot.py` is only a thin entry point. Done.
- document parsing can be tested independently. Started.
- the LLM client can be mocked. Started.

## Phase 2. Persistent Memory

Goal: keep useful context across restarts and make it manageable.

Options:

- SQLite for message history and user settings.
- A simple `messages` table with `user_id`, `role`, `content`, and `created_at`.
- Commands such as `/history`, `/reset`, and later `/memory`.

Tasks:

- Add a repository layer for history.
- Limit history by message count and/or tokens.
- Add migrations or a simple schema bootstrap.
- Separate short-term chat history from long-term user facts.

Readiness criteria:

- process restart does not erase history;
- users can clear their own history;
- database size is controlled.

## Phase 3. Queues For Heavy Work

Goal: avoid blocking Telegram handlers with OCR, STT, and long LLM requests.

Tasks:

- Introduce background task workers.
- Limit OCR/STT concurrency.
- Add user-facing statuses: queued, processing, done, failed.
- Add timeout and cancellation policy.

Readiness criteria:

- multiple heavy documents do not stall the bot;
- users receive clear processing status;
- CPU/RAM usage is bounded.

## Phase 4. Document RAG

Goal: analyze long documents without truncating only the first part.

Minimum version:

- text chunking;
- embeddings;
- local vector store;
- retrieval of relevant fragments for a question;
- answers that cite fragments or pages.

Tasks:

- Store uploaded documents and metadata.
- Preserve page references for direct PDF parsing and OCR.
- Add commands: `/doc_summary`, `/ask_doc`, `/forget_docs`.
- Add storage limits.

Readiness criteria:

- long documents can be analyzed end to end;
- users can ask questions about previously uploaded documents;
- the bot states which fragments were used for the answer.

## Phase 5. Response Quality And Modes

Goal: make prompt modes more controllable and repeatable.

Tasks:

- Move prompts into files or structured templates.
- Add modes for commercial proposals, technical specifications, meeting minutes, procurement analysis, and call summaries.
- Add a compact response policy for Telegram.
- Add post-processing for long responses with message splitting.
- Add `/mode` to select the default mode.

Readiness criteria:

- prompt modes can be changed without editing core code;
- long responses are delivered correctly in Telegram;
- output format is stable on common tasks.

## Phase 6. Observability And Maintenance

Goal: understand what is happening in production-like usage.

Tasks:

- Structured logs.
- Metrics: request count, Ollama errors, STT/OCR/LLM latency.
- Healthcheck endpoint or a dedicated diagnostics command.
- Log rotation.
- Recovery runbook.

Readiness criteria:

- issues can be diagnosed from logs;
- bottlenecks are visible across Telegram, Ollama, STT, OCR, and parsing.

## Backlog

- Dockerfile and docker-compose.
- Image attachments as first-class input.
- Support for `.xlsx`, `.pptx`, and `.rtf`.
- Role separation: owner/admin/user.
- Per-user rate limiting.
- Automatic summarization of long history.
- Calendar or task tracker integration.
- Export results to `.docx` or `.md`.
- Web UI for prompts, users, and documents.
- Regression prompt suite for evaluating model changes.

## Next Sprint Priorities

1. Persistent history storage.
2. More unit tests for document extraction, prompt mode routing, and error paths.
3. Robust retry/backoff for Ollama, STT, and OCR.
4. Background queue for OCR/STT workloads.
5. Document RAG planning.
