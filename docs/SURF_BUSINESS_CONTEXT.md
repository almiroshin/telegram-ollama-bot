# SURF Business Context

## Source Context

This roadmap is based on the public positioning of SURF Consulting at `https://surf.consulting`.

Public signals used for product direction:

- SURF Consulting works on the Russian IT market and focuses on complex IT infrastructure projects.
- The company emphasizes resilience under sanctions and supply-chain constraints.
- The offer includes IT consulting and strategy, IT infrastructure design and modernization, security, engineering systems, equipment/software supply, and implementation.
- Target sectors include finance, government, retail, and healthcare.
- Differentiators include supplier networks, own logistics for foreign vendors, access to stock information in Russia, original products, unusual solutions such as AI infrastructure, and IT budget savings.

## Practical Company Pains

### 1. Pre-Sales Discovery Takes Repeated Manual Work

Infrastructure opportunities usually start with incomplete inputs: a short customer message, a voice note, a meeting summary, a tender fragment, or an old bill of materials. Sales and technical teams need to convert this into clear discovery questions, required documents, and next steps.

Bot implication: the assistant should add first-class `/audit`, `/followup`, and document analysis workflows while preserving generic chat.

### 2. Commercial Proposals Need Faster First Drafts

SURF needs to turn technical inputs into business-facing proposals: customer context, solution scope, options, assumptions, risks, expected effect, and next steps. The first draft is repetitive but still requires domain framing.

Bot implication: `/proposal` should become a core workflow, later backed by reusable templates and previous proposal examples.

### 3. Tender And RFP Analysis Is High-Leverage

RFPs and technical specifications contain mandatory requirements, hidden risks, unclear wording, compatibility traps, delivery constraints, and clarification questions. Missing these early creates commercial and delivery risk.

Bot implication: `/tender` and document mode should extract requirements, risks, gaps, clarification questions, and response plans.

### 4. Vendor Alternatives Need Human-Checked Structure

Because the company works with domestic and foreign vendors, the team often needs alternative shortlists and risk framing. The assistant must not invent stock availability, pricing, or delivery terms. It should prepare structured comparison logic and explicitly mark what must be checked with suppliers.

Bot implication: `/vendor` should produce decision support, not final procurement facts.

### 5. Supply And Delivery Risk Must Be Visible Before Commitments

Risks include sanctions, logistics, lead times, original-product verification, warranty, compatibility, security requirements, and implementation dependencies.

Bot implication: `/risk` should become a standard gate before sending commercial commitments or entering tenders.

### 6. Local-First Processing Matters

Customer documents, tenders, prices, and infrastructure details can be sensitive. A local Telegram + Ollama deployment on the Mac mini is strategically aligned with this need, but it requires strict access control, backups, logs, and operational discipline.

Bot implication: local processing is a product requirement, not only an implementation detail.

### 7. Corporate Channel Support Matters

Telegram is convenient for fast iteration, but SURF's internal and customer-facing workflows may need a corporate messenger. eXpress should be planned as a first-class channel because it is positioned around secure corporate messaging, chat-bots, SmartApps, and integrations with enterprise systems.

Bot implication: the assistant should move toward a channel adapter architecture before deeper case management is implemented.

## Repositioned Product

The project should evolve into a two-layer local assistant:

- a general AI assistant for daily work;
- a specialized pre-sales and delivery assistant for an IT infrastructure supplier.

Primary users:

- account managers;
- pre-sales engineers;
- project leads;
- procurement/vendor managers;
- leadership preparing executive communication.

Primary workflows:

- answer general work questions;
- draft, rewrite, shorten, and structure texts;
- help with shell commands and operational troubleshooting;
- process voice notes and documents;
- work through Telegram now and eXpress later;
- qualify a new customer request;
- prepare discovery questions for an infrastructure audit;
- analyze an RFP, tender, or technical specification;
- draft a commercial proposal;
- compare vendor alternatives;
- find delivery and commercial risks;
- produce meeting follow-ups and executive summaries;
- preserve internal knowledge in a local searchable base.

## Product Principles

- Keep sensitive inputs local by default.
- Never invent prices, stock, delivery terms, warranty status, or vendor commitments.
- Separate "assistant draft" from "commercially approved answer".
- Prefer structured outputs that can be reused in email, proposals, and internal notes.
- Make user access and auditability explicit.
- Build toward a company knowledge base: vendors, products, prior proposals, tender answers, risks, and successful project patterns.
