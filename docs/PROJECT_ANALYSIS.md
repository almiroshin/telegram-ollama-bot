# Project Analysis

## Executive Summary

This project is a local AI assistant exposed through Telegram for SURF Consulting. The target product has two layers: a general AI assistant for daily work and a specialized assistant for SURF's IT infrastructure business. It should support writing, rewriting, shell help, voice notes, document analysis, pre-sales discovery, IT landscape audits, tender/RFP analysis, commercial proposal drafting, vendor alternative comparison, delivery risk review, and executive/customer communication.

## What Works Well

- Simple architecture with very little infrastructure.
- Key processing dependencies can run locally: Ollama, `faster-whisper`, and Tesseract.
- Prompt modes cover both general assistant tasks and SURF Consulting's infrastructure sales and delivery workflows.
- Voice messages and documents are available through the same Telegram interface.
- PDF processing has an OCR fallback.
- Runtime configuration is controlled through environment variables.
- File size, document text, and OCR page limits are already present.

## Functional Coverage

| Area | Status | Notes |
| --- | --- | --- |
| Text chat | Available | Through the Ollama Chat API. |
| Prompt modes | Available | Includes SURF-specific modes: `/audit`, `/proposal`, `/tender`, `/vendor`, `/risk`. |
| History | Available | SQLite-backed, keyed by Telegram user ID. |
| Voice | Available | `faster-whisper`, Russian language. |
| TXT/MD | Available | Multiple fallback encodings. |
| PDF | Available | Direct text extraction through `pypdf`. |
| PDF OCR | Available | `pdf2image` + Tesseract. |
| DOCX | Available | Paragraphs and tables. |
| User access control | Available | Owner-managed requests and SQLite-backed approvals. |
| Persistence | Partial | Conversation history and managed users persist; company knowledge, vendor data, and proposal templates are not implemented. |
| Tests | Partial | Helper-level `unittest` coverage exists; integration tests are still missing. |
| RAG | Missing | Long tenders, specifications, proposals, and vendor materials are currently truncated. |

## Strengths

- Fast to start and easy to inspect: a thin entry point plus focused modules.
- Local-first design: data does not need to leave the host machine for external LLM APIs.
- Domain prompt modes are aligned with pre-sales and tender workflows.
- OCR makes the bot useful for scans and procurement-style documents.

## Repositioned Product Scope

The general assistant layer remains part of the product. It should continue to handle everyday questions, writing, rewriting, shortening, terminal help, voice notes, and general document analysis.

The SURF-specific layer should add structured workflows for infrastructure sales and delivery.

Primary users:

- account managers;
- pre-sales engineers;
- procurement/vendor managers;
- project leads;
- leadership preparing executive communication.

Primary workflows:

- qualify a new customer request;
- prepare discovery questions for an IT audit;
- analyze an RFP, tender, or technical specification;
- draft a commercial proposal;
- compare vendor alternatives and identify supplier checks;
- review delivery, logistics, security, compatibility, and commercial risks;
- turn voice notes and meetings into follow-ups and next steps.

## Main Risks

### 1. Access Control Must Be Configured

Anyone who can message the bot can use the local LLM and document processing capabilities if both `OWNER_TELEGRAM_USER_IDS` and the legacy `ALLOWED_TELEGRAM_USER_IDS` are left empty. For an internal assistant, this is the highest operational risk.

Recommendation: set `OWNER_TELEGRAM_USER_IDS` in production. Use `/request_access`, `/approve`, `/deny`, `/revoke`, and `/users` for day-to-day access management.

### 2. Persistent Memory Is Still Minimal

Conversation history is now stored in SQLite, but there is no company knowledge base, no previous proposal memory, no vendor catalog, no customer/project profiles, and no compaction beyond message-count trimming.

Recommendation: add history inspection, summarized long-term memory, and a local knowledge base for vendors, proposals, risks, and reusable answers.

### 3. Heavy Work Inside Handlers

OCR and STT can take noticeable time and currently run directly inside handlers. This is acceptable for one user, but it will become a problem as workload grows.

Recommendation: add a task queue or a bounded background executor.

### 4. Raw Errors Are Sent To Users

Responses that include raw Ollama exception details are useful during development, but they can reveal environment details in regular usage.

Recommendation: send short safe errors to users and write details to logs.

### 5. Long Commercial Documents Are Truncated

`MAX_DOCUMENT_CHARS` protects the context window, but only the first part of a document is analyzed. For specifications, tenders, vendor proposals, contracts, and bills of materials, this can produce incomplete conclusions.

Recommendation: add chunking/RAG or at least a map-reduce summarization flow.

### 6. No Source Of Truth For Vendor And Supply Data

The assistant must not invent prices, stock availability, warranty conditions, lead times, or vendor commitments. Today it has no structured source of truth for these facts.

Recommendation: keep `/vendor` as decision support first, then add explicit supplier data ingestion with freshness labels and human confirmation.

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
  users.py
  handlers.py
  stt.py
  documents.py
  logging_config.py
tests/
  test_documents.py
  test_history.py
  test_access.py
```

Minimum refactoring sequence:

1. Keep `requirements.txt`, `.env.example`, and documentation current.
2. Add a user allowlist without changing the overall structure. Done.
3. Add owner-managed user approvals. Done.
4. Move pure document parsing functions into a separate module. Done.
5. Add tests for helper functions. Started.
6. Extract the Ollama client and Telegram handlers. Done.
7. Add SQLite-backed conversation history. Done.

## Near-Term Technical Tasks

- Set `OWNER_TELEGRAM_USER_IDS` in production.
- Add a proper logger.
- Add `.env` loading through `python-dotenv` or explicitly document shell export.
- Add user-facing history inspection and long-term memory controls.
- Add reusable proposal, audit, tender, and risk templates.
- Add local knowledge ingestion for vendor decks, stock exports, prior proposals, tender answers, and delivery lessons learned.
- Add broader test coverage for document extraction, prompt routing, and external error handling.
- Split long responses to respect Telegram message limits.
- Add retry/backoff for Ollama.
- Make STT language configurable through environment variables.
- Improve PDF handling with partial OCR: direct parsing plus OCR only for empty pages.

## Conclusion

The project is already useful as a local general assistant and now has a clearer SURF-specific direction. The main engineering priority is to keep the foundation stable while adding case management, document intelligence, vendor knowledge, and proposal workflows. After that, RAG and persistent memory will be much easier to add safely.
