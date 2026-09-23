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
6. Conversations saved for quality review: emails and phone numbers redacted, deleted
   after 30 days, disclosed on /privacy. Plus one event row per turn (topic, confidence,
   router, model, latency, tokens, cost, outcome).
7. Unit tests + ~20-case answer-quality test set, one command each
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
| Jev for routing, chat model for answers | Jev returns typed decisions with confidence; cheap and fast | New (Sept 2026) service → built a fallback |
| Model fallback when Jev is unsure or down | The demo can't depend on a week-old beta | Slightly more code |
| Knowledge in the prompt, not retrieval | Small corpus; simpler and more accurate | Won't scale to hundreds of pages as-is |
| Capture leads on handoff | The bot's job is to free up strategists | Needs a database and validation |
| Never quote prices | Not published; wrong numbers cost trust | Some visitors want a number |
| Named persona ("Cadence"), labeled as AI | Engagement plus honesty (AI disclosure) | No human face on the bot |
| ~~No transcripts stored~~ → **Transcripts kept, redacted, 30-day deletion** | Changed 09-23: research recommends routine transcript sampling (findings, §9 Lean level); you can't improve what you can't review | Holds some personal data briefly; mitigated by redaction, retention, disclosure |
| Dummy handoff form, honest confirmation | Brian's call: mirrors cadre.ai/contact without sending anything; the research warns against claiming a send that didn't happen | No real lead capture in the demo |
| Measure qualified handoffs, not lead count | Research: form completions aren't the outcome (findings §Where) | Harder to measure in a demo |
| Zero critical eval failures = launch gate | Research §8: never average a critical failure away | Stricter; may cut scope |
| Links rendered only to an allow-list | OWASP 2026: output rendering is an attack surface (findings #7) | Bot can't link elsewhere |

## 4. Phases
Each phase: build → verify → explain → approve → commit.

- [x] **0. Foundation:** repo, CLAUDE.md, this plan, .gitignore
- [x] **1. Risk spikes + deploy early:** one Jev call from Python via AI Gateway; one OpenRouter call; "hello" page live on Vercel
- [x] **2. Knowledge:** `knowledge/cadre.md` from cadre.ai, a source per fact, reviewed line by line
- [x] **3. Answering:** `prompts/system.md`, `answer.py`, streaming `/api/chat`, UI wired to the API
- [x] **4. Routing:** Jev topic + needs-human, confidence threshold, fallback, tests for each path
- [x] **5. Handoff + data:** contact-style form (dummy, honest confirmation), `/api/leads` validation + idempotency, Supabase `conversations` + `chat_events` with redaction and 30-day deletion
- [ ] **6. Measure:** ~20 eval cases, runner, 3-model comparison, pick the model
  - **Task (Brian, 09-23): justify the model choice with data.** Run the same eval set
    against every candidate answer model (not just 3 if more are viable) and record
    quality, invented facts, handoff accuracy, latency, and cost per conversation in §5.
    Write a short "Why this model" paragraph: why the winner, why not the runners-up.
    Also explain why Jev for routing (Phase 1 + Phase 4 measurements) vs. using the chat
    model for routing too. The current `google/gemini-2.5-flash-lite` is **provisional**.
- [ ] **7. Harden + ship:** guards, reviewer pass, README, what's next, submit

## 4a. Phase 1 findings (Jev spike, 2026-09-23)
Ran `spikes/jev_spike.py`: 3 messages via AI Gateway `/v1/evaluate`.

| Message | topic (choice) | p | needs_human (boolean) |
|---|---|---|---|
| "Do you guys work with construction companies?" | industries | 1.00 | 0.55 |
| "How much does an engagement cost?" | pricing | 0.99 | 0.35 |
| "What's the weather in San Diego?" | off_topic | 1.00 | 0.21 |

- **Topic routing is strong.** Use Jev's `choice` for the topic.
- **A vague "needs a human?" boolean is unreliable** (construction scored above pricing).
  Decision: handoff = topic rule (pricing, security, portal login always offer a human) +
  a sharper Jev boolean, "is the visitor explicitly asking for a person?", with `criteria`
  defining true and false. Re-measure in Phase 6.
- Auth works with the Vercel OIDC token locally; AI Gateway requires a card on file.
- OpenRouter (Brian's dev key): gemini-2.5-flash-lite and gpt-4.1-nano answered; gpt-5-nano returned blank (reasoning ate the token budget).
- Live: https://cadre-chatbot-xi.vercel.app. `/api/health` returns ok.

## 4b. Phase 2 findings (knowledge, 2026-09-23)
- `knowledge/cadre.md`: 77 facts from 21 cadre.ai pages, each with an exact quote and URL.
- `tools/verify_knowledge.py` string-matches every quote against the live page: 77/77 pass.
- Research was split: the `site-researcher` subagent (read-only, `.claude/agents/`) covered
  the services pages while I covered industries, case studies, and contact in parallel.
- Deeper research closed gaps the first scan missed: the 8 pillar names (/strategy),
  real security statements, plus support email, phone, and office address (/contact).

## 5. Model comparison
*(filled in during Phase 6: see the task under Phase 6)*

**Why this model:** *(to write after the comparison)*

| Model | Eval pass rate | Invented facts | p50 latency | Cost / conversation |
|---|---|---|---|---|

## 6. AI-bug log
Where AI output was wrong or weak, how it was caught, and what changed.

| Date | What the AI produced | What was wrong | How it was caught | Fix |
|---|---|---|---|---|
| 09-23 | Advised against Jev: "limited early access, not on OpenRouter" | Jev is generally available on Vercel AI Gateway | Brian found it in one search | Adopted Jev with a fallback; rule: research access paths before objecting |
| 09-23 | Stated website facts from a summarizer tool as fact | Unverified | Brian asked for the source | Re-read cadre.ai directly; every fact now cites a URL |
| 09-23 | UI prototype | Unreadable form fields and faint text | Brian reviewed it | Fixed contrast, tested at desktop and phone size before resharing |
| 09-23 | Jev routing design assumed one "needs a human?" question would work | Scores were fuzzy and inverted (pricing < construction) | Measured it in the Phase 1 spike before building | Topic-rule handoff + a sharper, criteria-defined Jev question |
| 09-23 | First deploy "succeeded" | Vercel served only static files; the Python app never ran (/api/health 404) | Checked the health endpoint, not just "Ready" | Set `"framework": "fastapi"` in vercel.json; added a .vercelignore so secrets are never uploaded |
| 09-23 | First site scan said the 8 pillar names and security statements weren't public | They're on /strategy; the scan only read the homepage | Subagent read every services page | Knowledge updated; gaps list corrected |
| 09-23 | Quote checker flagged 2 of 77 quotes | Not wrong facts: split markup and a non-breaking hyphen | Inspected the raw page text around each failure | Normalizer handles both; 77/77 pass |
| 09-23 | Prompt example answer (written by Claude) for construction | Included facts not in the knowledge file ("estimating, track project health"); the model repeated them word for word | Live test of the answer engine; compared the answer to knowledge/cadre.md | Example rewritten with knowledge-only facts; rule added: examples may only use knowledge facts; eval case added in Phase 6 |
| 09-23 | `/privacy` route returning `FileResponse(public/privacy.html)` | Worked locally, 500 on Vercel: `public/` isn't bundled into the Python function | Post-deploy check of each page; traceback in `vercel logs` | Link to the static `/privacy.html`; gotcha added to CLAUDE.md |
| 09-23 | Test call to gpt-5-nano | Blank reply: the model spent all its tokens reasoning | Checked the output, not just the HTTP status | Empty replies are treated as errors (CLAUDE.md rule 7) |

## 6a. Documentation tasks (for the review)
- **Jev integration write-up (Brian, 09-23):** explain how Jev is used. That means the
  10 topic definitions (`config.TOPICS`) and how Jev picks one, the "asks for a person"
  question and its true/false criteria, the confidence threshold and why it's 0.6, the
  model fallback path, how the topic feeds the answer prompt, the off-topic short-circuit,
  auth via Vercel OIDC, and the Phase 1 / Phase 4 measurements. Target:
  `docs/jev-routing.md` plus a diagram. Not started.

- **Benchmark with vs. without Jev (Brian, 09-23):** run the same eval set two ways,
  (a) Jev routing + rules and (b) chat-model-only routing (the fallback path, forced on),
  and compare topic accuracy, handoff accuracy, latency (median and slow tail), cost per
  conversation, and off-topic/injection handling. It answers "was Jev worth adding?" with
  data. Easy to run: `route()` already has both paths; add a flag to force the fallback.
  Do it in Phase 6 alongside the model comparison. Not started.

## 7. What's next (with more time)
*(filled in as we go)*
