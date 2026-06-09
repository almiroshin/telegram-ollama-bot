# Channel Integrations

## Direction

The assistant should not remain tied only to Telegram. Telegram is the current runtime channel, but the product should evolve toward a channel adapter architecture that can support both:

- Telegram for fast personal and small-team usage;
- eXpress for corporate, secure, and potentially customer-facing communication.

## Why eXpress Matters

eXpress is positioned as a secure corporate communication platform with messenger, video calls, mail, SmartApps, and chat-bot capabilities. The official eXpress materials describe:

- chat-bots for business process automation;
- BotX as a microservice for interaction between chat-bots and the eXpress communication platform;
- API-based bot development by customers;
- text messages, files, buttons, chat creation, and system events;
- SmartApps as a single window for corporate systems and services.

This makes eXpress a natural second channel for an internal SURF assistant.

Official references:

- `https://express.ms/`
- `https://express.ms/chatbots/`
- `https://docs.express.ms/`

## Product Positioning

The assistant should have one core and multiple channels.

Core capabilities:

- general AI assistant;
- SURF workflow modes;
- document processing;
- case workspace;
- access control;
- history and future knowledge base;
- audit logs.

Channel capabilities:

- receive messages and files;
- send replies;
- expose commands;
- map platform users to internal users;
- preserve channel-specific metadata;
- enforce access rules.

## Target Architecture

```text
Telegram Bot API      eXpress BotX/API
       |                    |
       v                    v
  TelegramAdapter      ExpressAdapter
       |                    |
       +--------+-----------+
                |
                v
        Assistant Core
                |
                v
  LLM, prompts, documents, cases, users, history
```

The core must not depend on `python-telegram-bot` objects. Channel adapters should convert platform-specific updates into internal request objects and convert assistant responses back into channel-specific messages.

## Internal Request Model

Planned internal object:

```text
AssistantRequest(
  channel,
  channel_user_id,
  internal_user_id,
  chat_id,
  text,
  command,
  attachments,
  message_id,
  thread_id,
  metadata
)
```

Planned internal response:

```text
AssistantResponse(
  text,
  attachments,
  actions,
  visibility,
  metadata
)
```

## eXpress Integration Phases

### Phase 1. Discovery

Tasks:

- obtain access to the exact eXpress BotX/API documentation for the target deployment;
- confirm authentication flow, webhook/event delivery, file download/upload, button support, and user identifiers;
- confirm whether the SURF deployment will use cloud, on-premise, or federated eXpress;
- define environment variables for eXpress integration without storing secrets in Git.

Expected output:

- a small technical design note;
- sample incoming event payloads;
- sample outgoing message payloads;
- security requirements from the eXpress administrator.

### Phase 2. Core Refactor For Channels

Tasks:

- extract Telegram-specific logic from `app/handlers.py` into `app/channels/telegram.py`;
- introduce channel-neutral request handling in `app/assistant.py`;
- keep prompt modes, LLM access, history, users, and documents in shared modules;
- add unit tests for command routing without Telegram objects.

Expected output:

- current Telegram behavior preserved;
- assistant core can be called from tests without Telegram.

### Phase 3. eXpress MVP

Tasks:

- add `app/channels/express.py`;
- support text commands first: `/start`, `/status`, `/reset`, `/audit`, `/proposal`, `/tender`, `/vendor`, `/risk`;
- support owner-managed access mapping for eXpress users;
- add basic outbound messages;
- add deployment settings for eXpress webhook or polling mode, depending on the actual API.

Expected output:

- eXpress users can use the same assistant modes as Telegram users;
- Telegram remains fully supported.

### Phase 4. Files And Documents

Tasks:

- support eXpress file download;
- reuse existing document extraction and OCR logic;
- preserve source metadata: channel, chat, sender, file name, message ID;
- add channel-specific file size limits.

Expected output:

- tender/RFP files from eXpress can be analyzed like Telegram documents.

### Phase 5. SmartApps Option

Tasks:

- evaluate whether a SmartApp is useful for structured workflows such as cases, proposals, approvals, and document lists;
- keep the bot conversational interface for quick use;
- use SmartApps only when a form/table UI is materially better than chat commands.

Expected output:

- decision on bot-only versus bot plus SmartApp UI.

## Access And Identity

Telegram user IDs and eXpress user IDs are different identifiers. The assistant should introduce internal users:

```text
internal_users(id, display_name, role, status)
channel_identities(internal_user_id, channel, channel_user_id, username)
```

Until that model exists, eXpress integration should avoid mixing Telegram and eXpress users in the same `users` table without a migration plan.

## Security Requirements

- Store eXpress credentials only in `.env` or a secret manager.
- Do not log access tokens or full event payloads with sensitive files/text.
- Keep owner approval for new channel users.
- Add audit logs for access changes and admin commands.
- Treat files from eXpress as sensitive customer/internal data.
- Confirm TLS requirements between the bot and eXpress/BotX.

## Environment Variables

Planned variables:

```text
ENABLE_TELEGRAM=true
ENABLE_EXPRESS=false

EXPRESS_BASE_URL=
EXPRESS_BOT_ID=
EXPRESS_BOT_TOKEN=
EXPRESS_WEBHOOK_SECRET=
EXPRESS_VERIFY_TLS=true
```

Exact names may change after the real BotX/API payloads are reviewed.

## Open Questions

- Is the target eXpress deployment cloud, on-premise, or federated?
- Will the bot receive events through webhooks, polling, or another integration mode?
- What user identifier is stable enough for access control?
- How are files downloaded and uploaded?
- Are buttons supported in the required client versions?
- Should the assistant also be exposed as a SmartApp?
- What security controls are required by SURF or the customer environment?
