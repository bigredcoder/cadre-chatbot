# plan.md: Cadence, a support chatbot for Cadre AI

## 1. Discovery
**The problem:** Cadre's inbound team fields the same questions again and again. What do
you do, do you work with my industry, how do I book a call, how do I get into the
portal, what's the AI Maturity Index. That time should go to high-value conversations.

**Who shows up**
- Prospects: what Cadre does, industry fit, how to talk to someone
- Existing clients: getting into the portal
- Business leaders: the AI Maturity Index and how to get scored
- Evaluators / IT: model choice and data security

**What the bot is for:** answer the repetitive questions instantly and accurately, and
turn the high-value ones into leads for a strategist.

**How we'd know it works**
- Share of questions answered without a human
- Leads captured
- Correct handoffs (it doesn't answer what it shouldn't)
- Zero invented facts
- Cost per conversation and response time

**Sources of truth:** cadre.ai (read 2026-09-23) and the take-home brief. Nothing else.

**Known gaps in public info:** pricing, whether the Maturity Index is free, portal login
steps, security certifications and data hosting. The bot says it doesn't know and hands off.
It doesn't guess.

## 2. Scope
**In**
1. Answers the brief's six scenarios plus pricing, grounded only in `knowledge/`
2. Jev routing (topic + needs-a-human, with confidence) and a model fallback
3. Human handoff: an inline form mirroring cadre.ai/contact (Name, Email, Subject, Message),
   prefilled and validated server-side. Demo only: nothing is sent or stored, and the
   confirmation says so honestly.
4. Guardrails: on-topic only, no invented facts or prices, resists prompt injection
5. Chat bubble UI in Cadre's style, streaming answers, starter questions, "Behind the scenes" toggle
6. Conversations saved for quality review: one row per turn in `chat_turns` (message,
   reply, topic, confidence, router, model, latency, tokens, cost, outcome). Emails, phone
   and card numbers are redacted before the models see them and before saving; rows are
   deleted after 30 days; described on `/privacy.html`.
7. Unit tests + ~20-case answer-quality test set, one command each (shipped: 118 unit tests,
   31 eval cases, 12 browser tests)
8. Model comparison on the same test set (quality / speed / cost)
9. Budget and abuse guards

**Out, and why**
- *Portal login / integration:* the bot explains the portal; it isn't an auth system.
- *Vector DB / retrieval:* the knowledge fits in the prompt. At this size, retrieval
  adds moving parts and can miss facts. Add it when the content outgrows the prompt.
- *Admin dashboard:* the event table is the data layer; a dashboard is next.
- *Storing handoff form submissions:* it's a demo. No lead data is kept.
- *Multi-language, voice, history across visits, CRM sync, one-line embed for cadre.ai:* next.

## 2a. Research basis
Design choices from Phase 3 onward follow `docs/research/findings.md`, a summary of a
deep-research report on website chatbots in 2026 (`docs/research/website-ai-chatbot-research-2026.md`).
It confirmed 8 existing decisions and added 17 changes: a labeled launcher, an answer
contract, recover-once-then-hand-off, accessible focus and announcements, safe link
rendering, a privacy line, prefilled handoff, idempotent lead submit, graceful failure,
and severity-based evals with a zero-critical launch gate.
Cadence fits the report's "Lean" level: approved public content, few tasks, a human route,
no autonomous actions.

## 3. Key decisions and trade-offs
| Decision | Why | Trade-off accepted |
|---|---|---|
| Python + FastAPI + one HTML page | Readable, matches the role, fast to deploy on Vercel | Less UI polish than a React stack |
| **Chat window = Deep Chat** (changed 09-23) | A proven component for the solved problem (streaming, scroll, mobile); our effort goes to grounding, routing, and evals. Research: hybrid is the most practical deployment | A 387 KB dependency; self-hosted so no third-party script can take the page down |
| Jev for routing, chat model for answers | Jev returns typed decisions with confidence; faster median routing (`docs/jev-routing.md`, Evidence) | New (Sept 2026) service → built a fallback; cost unmeasured (recorded $0 on free credits) |
| Model fallback when Jev is unsure or down | The demo can't depend on a week-old beta | Slightly more code |
| Knowledge in the prompt, not retrieval | Small corpus; simpler and more accurate | Won't scale to hundreds of pages as-is |
| ~~Capture leads on handoff~~ → replaced 09-23 by the demo form below | The bot's job is to free up strategists | Real capture is designed (`db/schema.sql`), not built |
| Never quote prices | Not published; wrong numbers cost trust | Some visitors want a number |
| Named persona ("Cadence"), labeled as AI | Engagement plus honesty (AI disclosure) | No human face on the bot |
| ~~No transcripts stored~~ → **Transcripts kept, redacted, 30-day deletion** | Changed 09-23: research recommends routine transcript sampling (findings, §9 Lean level); you can't improve what you can't review | Holds some personal data briefly; mitigated by redaction, retention, disclosure |
| Dummy handoff form, honest confirmation | Brian's call: mirrors cadre.ai/contact without sending anything; the research warns against claiming a send that didn't happen | No real lead capture in the demo |
| Measure qualified handoffs, not lead count | Research: form completions aren't the outcome (findings §Where) | Harder to measure in a demo |
| Zero critical eval failures = launch gate | Research §8: never average a critical failure away | Stricter; may cut scope |
| Links rendered only to an allow-list | OWASP 2026: output rendering is an attack surface (findings #7) | Bot can't link elsewhere |

## 3a. Changed by Brian after device testing (09-24)
- The privacy banner (09-23) and the "How chat data is used" menu link (09-24) were removed at
  Brian's request. Trade-off: the research recommends a short privacy note in the chat
  (findings #8). The `/privacy.html` page still exists and is accurate; in production it would
  be linked from the site footer or the chat.

## 4. Phases
Each phase: build → verify → explain → approve → commit.

- [x] **0. Foundation:** repo, CLAUDE.md, this plan, .gitignore
- [x] **1. Risk spikes + deploy early:** one Jev call from Python via AI Gateway; one OpenRouter call; "hello" page live on Vercel
- [x] **2. Knowledge:** `knowledge/cadre.md` from cadre.ai, a source per fact, reviewed line by line
- [x] **3. Answering:** `prompts/system.md`, `answer.py`, streaming `/api/chat`, UI wired to the API
- [x] **4. Routing:** Jev topic + needs-human, confidence threshold, fallback, tests for each path
- [x] **5. Handoff + data:** contact-style form (dummy, honest confirmation), `/api/leads` validation + idempotency, Supabase with redaction and 30-day deletion (planned as two tables, `conversations` + `chat_events`; built as one table, `chat_turns`, one row per turn: simpler, and every review query still works)
- [x] **6. Measure:** 26 eval cases, runner, 11-model comparison (planned: 3), pick the model
  - **Task (Brian, 09-23): justify the model choice with data.** Run the same eval set
    against every candidate answer model (not just 3 if more are viable) and record
    quality, invented facts, handoff accuracy, latency, and cost per conversation in §5
    (now `docs/model-choice.md` §5). Write a short "Why this model" paragraph: why the
    winner, why not the runners-up. Also explain why Jev for routing (Phase 1 + Phase 4
    measurements) vs. using the chat model for routing too. **Done:** `google/gemini-2.5-flash`
    chosen (`docs/model-choice.md` §5); Jev benchmark in `docs/jev-routing.md`.
- [x] **7. Harden:** rate limits, code review pass (8 fixes), README, browser and load tests
- [x] **8. Device testing + UI rebuild (09-23/24):** chat window rebuilt on Deep Chat after
  iPhone testing; iPhone tests in Safari's engine (§3a)
- [x] **9. Pre-submission audit (09-24):** skeptical-reviewer audit of code, docs, and the live
  bot; fixes for a chat freeze, card-number redaction, time limits, redaction before model
  calls, a shared firewall rate limit, and `REVIEW-GUIDE.md`
- [ ] **10. Submit:** swap in Cadre's key (Brian approves), package with `tools/package.sh`
  (a fresh clone, zipped with `.git`), upload

## Moved out (09-25)
- Old §4a, §4b, §5, §5a (Jev spike, knowledge, model comparison, running costs):
  `docs/model-choice.md`, same numbers.
- Old §6 (AI-bug log): `docs/ai-bug-log.md`.
- Old §6a (documentation tasks, all done): deleted; the Jev benchmark is in `docs/jev-routing.md`.
- Old §6b is now §3a.

## 7. What's next (with more time)
- **Jev usage tier (Brian, 09-23):** Jev returned HTTP 429 (rate limited) on ~20% of calls in
  sequential testing. For production traffic, move to a paid or higher AI Gateway tier. The
  **fallback is already built and proven:** on 429/503 the router retries once after 0.3 s,
  then the chat model routes the message. In evals, all 11 rate-limited calls were answered
  normally. Optional next steps: a short-lived route cache for repeated questions, and an
  alert when the fallback rate passes a threshold (the `router` column in `chat_turns`
  already records it).
- Reasoning models (GPT-5 family): test with reasoning effort set to minimal and a larger token budget.
- **Rate limiting that holds across instances:** **Proven necessary 09-23:** a 25-message
  burst from one visitor spread across instances and none was limited. **Done 09-24:** a
  Vercel firewall rule (20 POSTs a minute per IP on `/api/`, all instances). Remaining: move
  the app's own friendlier counter (`guards.py`) to a shared store.
- **Server-side conversation history:** today the browser sends the last 8 messages, so a
  script could forge an earlier assistant turn (tested live: the bot refused). Store history
  per session on the server.
- **Real lead capture:** replace the demo form with a `leads` table (insert-only) plus a CRM
  sync (schema sketched in `db/schema.sql`); measure qualified meetings, not form fills.
- **One-line embed for cadre.ai:** a `<script>` tag that loads the widget on any page.
- **Content-gap review:** a weekly query on `chat_turns` (top handoff and off-topic topics)
  feeding `/add-knowledge`; a small dashboard later.
- **Evals in CI:** run unit tests on every push, and `evals.run` nightly with a zero-critical gate.
- **Tune Jev's topic definitions** against labeled real questions from `chat_turns`.
- **Accessibility:** a manual pass with a screen reader user, beyond the automated checks.
- **A/B test** the widget against the plain contact page for qualified-meeting rate (research §8).
