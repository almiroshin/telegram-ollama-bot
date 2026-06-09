# Roadmap

## Product Direction

The project should evolve into a two-layer local assistant:

- a general AI assistant for everyday work;
- a specialized pre-sales and delivery assistant for SURF Consulting, an IT infrastructure supplier and consulting company.

The highest-value workflows are:

- answer general work questions;
- draft, rewrite, shorten, and structure texts;
- help with shell commands and operational troubleshooting;
- process voice notes and documents;
- qualify customer requests and prepare discovery questions;
- support IT landscape audits;
- analyze tenders, RFPs, technical specifications, and procurement documents;
- draft commercial proposals and follow-ups;
- compare vendor alternatives without inventing prices or stock availability;
- identify delivery, logistics, compatibility, security, and commercial risks;
- preserve internal knowledge locally.

## Development Principles

- Keep sensitive customer and commercial data local by default.
- Treat generated output as a draft that requires human commercial approval.
- Never invent prices, stock, lead times, warranty terms, or vendor commitments.
- Prefer structured outputs that can be reused in email, proposals, and internal notes.
- Keep generic assistant features stable while adding SURF-specific workflows.
- Preserve the general assistant layer; specialized workflows should extend it, not replace it.
- Add tests around prompt routing, document parsing, access control, and failure paths.

## Phase 0. Operational Foundation

Goal: make the bot safe enough for internal use.

Status: mostly done.

Completed:

- modular `app/` structure;
- `.env.example`, requirements, deployment and operations docs;
- owner-managed Telegram access requests;
- SQLite conversation history;
- safe user-facing errors and logs;
- Mac mini deployment scripts;
- helper-level unit tests.

Remaining:

- document the minimum supported Python version;
- add automatic `.env` loading or make shell export behavior explicit in every path;
- add log rotation and backup guidance for `bot.sqlite`.

Readiness criteria:

- unknown Telegram users cannot use work commands;
- owners can approve and revoke users without SSH;
- the Mac mini can be deployed from GitHub with one command.

## Phase 1. SURF Workflow Prompt Modes

Goal: preserve the general assistant core and add modes aligned with SURF Consulting's real operating work.

Status: initial implementation done.

Implemented modes:

- general assistant: `default`, `/email`, `/rewrite`, `/shorten`, `/shell`, voice, and document processing;
- `/audit` - IT landscape audit and discovery questions;
- `/proposal` - commercial proposal structure;
- `/tender` - tender, RFP, and technical specification analysis;
- `/vendor` - vendor alternatives and supplier checklists;
- `/risk` - delivery, logistics, security, compatibility, and commercial risk review;
- `/followup` - meeting follow-up;
- `/vip` - executive communication.

Next tasks:

- add tests that verify every Telegram command maps to an existing prompt mode;
- move prompts into structured files or templates;
- add examples for common SURF scenarios: storage, servers, AI infrastructure, security, engineering systems, and modernization projects;
- add a compact output policy for Telegram message length.

Readiness criteria:

- account managers can process a customer request from Telegram;
- pre-sales engineers can produce audit questions and a first proposal outline;
- tender documents generate a structured response plan and risk list.

## Phase 2. Pre-Sales Case Workspace

Goal: group messages, documents, and outputs by customer opportunity instead of only by Telegram user.

Tasks:

- add a `cases` table: customer, opportunity name, sector, stage, owner, created date;
- add commands: `/case_new`, `/case_select`, `/case_status`, `/case_close`;
- attach document analyses and generated drafts to a case;
- store key facts: customer goals, deadlines, budget signals, required vendors, constraints, risks;
- add `/case_summary` for a clean internal brief.

Readiness criteria:

- several opportunities can be handled in parallel;
- the bot can summarize a case after restart;
- a case brief can be reused for internal handoff.

## Phase 3. Tender And Document Intelligence

Goal: analyze long commercial and technical documents without truncating only the beginning.

Tasks:

- chunk long documents;
- preserve page and section references for PDFs and DOCX;
- add local embeddings and vector search;
- add commands: `/doc_summary`, `/ask_doc`, `/doc_risks`, `/forget_docs`;
- add tender-specific extraction: mandatory requirements, deadlines, penalties, warranty, delivery terms, security requirements, clarification questions;
- add map-reduce summarization for large documents before full RAG is ready.

Readiness criteria:

- long tenders can be analyzed end to end;
- the bot can answer questions about previously uploaded documents;
- answers include the fragments or pages used.

## Phase 4. Vendor And Supply Knowledge Base

Goal: support vendor alternatives and supply planning with explicit source control.

Tasks:

- add local ingestion for vendor decks, product matrices, stock exports, prior quotes, and delivery notes;
- store source metadata: file, date, owner, freshness, confidence;
- add `/vendor_compare`, `/vendor_checks`, and `/supply_risks`;
- prevent generated answers from treating stale or missing data as facts;
- add manual confirmation fields for price, stock, warranty, lead time, and logistics route.

Readiness criteria:

- the assistant can prepare a vendor shortlist with explicit assumptions;
- supplier checks are visible before a proposal is sent;
- stale data is clearly marked.

## Phase 5. Proposal Factory

Goal: turn case facts and document analysis into reusable proposal drafts.

Tasks:

- add proposal templates for infrastructure modernization, storage, server platforms, AI infrastructure, security, and engineering systems;
- generate proposal sections: customer context, goals, solution, scope, options, risks, assumptions, next steps;
- add export to Markdown first, then DOCX;
- add internal review checklist before sending;
- add versioned proposal drafts per case.

Readiness criteria:

- a first proposal draft can be generated from a case summary;
- assumptions and missing data are visible;
- a proposal can be reviewed and revised without losing previous drafts.

## Phase 6. Heavy Work And Reliability

Goal: avoid blocking Telegram handlers with OCR, STT, long LLM requests, and document indexing.

Tasks:

- introduce a background task queue;
- limit OCR/STT/indexing concurrency;
- add user-facing statuses: queued, processing, done, failed;
- add timeout and cancellation policy;
- split long Telegram responses safely;
- add retry/backoff for Ollama and document processing.

Readiness criteria:

- multiple heavy documents do not stall the bot;
- users receive clear processing status;
- CPU/RAM usage is bounded on the Mac mini.

## Phase 7. Observability, Governance, And Operations

Goal: make internal production use auditable and recoverable.

Tasks:

- structured logs;
- metrics: requests, errors, OCR/STT/LLM latency, document counts, case counts;
- backup and restore for SQLite;
- access audit log for approvals and revocations;
- admin command audit trail;
- healthcheck endpoint or diagnostics command;
- recovery runbook.

Readiness criteria:

- issues can be diagnosed from logs;
- access changes are auditable;
- the Mac mini service can be restored after failure.

## Backlog

- Web UI for cases, prompts, users, and documents.
- Integration with CRM or task tracker.
- Vendor stock import from spreadsheets.
- Role separation beyond owner/user.
- Per-user and per-case rate limits.
- Regression prompt suite for evaluating model changes.
- Dockerfile and docker-compose.
- Support for `.xlsx`, `.pptx`, and `.rtf`.
- Export results to `.docx` and proposal-ready Markdown.

## Next Sprint Priorities

1. Add `/case_new`, `/case_select`, and a minimal SQLite `cases` table.
2. Add command-to-prompt routing tests for all SURF modes.
3. Improve document mode for tender/RFP extraction.
4. Add response splitting for long Telegram outputs.
5. Add backup guidance for `bot.sqlite` on the Mac mini.
