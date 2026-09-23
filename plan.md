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

**Known gaps in public info:** pricing, the names of the eight Maturity Index pillars,
portal login steps, a data-security policy. The bot says it doesn't know and hands off.
It doesn't guess.

## 2. Scope
**In**
1. Answers the brief's six scenarios plus pricing, grounded only in `knowledge/`
2. Jev routing (topic + needs-a-human, with confidence) and a model fallback
3. Human handoff: inline form → `leads` table, plus the /contact link
4. Guardrails: on-topic only, no invented facts or prices, resists prompt injection
5. Chat bubble UI in Cadre's style, streaming answers, starter questions, "Behind the scenes" toggle
6. One event row per turn (topic, confidence, router, model, latency, tokens, cost, outcome)
7. Unit tests + ~20-case answer-quality test set, one command each
8. Model comparison on the same test set (quality / speed / cost)
9. Budget and abuse guards

**Out, and why**
- *Portal login / integration:* the bot explains the portal; it isn't an auth system.
- *Vector DB / retrieval:* the knowledge fits in the prompt. At this size, retrieval
  adds moving parts and can miss facts. Add it when the content outgrows the prompt.
- *Admin dashboard:* the event table is the data layer; a dashboard is next.
- *Full transcript storage:* privacy. Less personal data held, less risk.
- *Multi-language, voice, history across visits, CRM sync, one-line embed for cadre.ai:* next.

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
| No transcripts stored | Privacy by default | Less data for tuning |

## 4. Phases
Each phase: build → verify → explain → approve → commit.

- [x] **0. Foundation:** repo, CLAUDE.md, this plan, .gitignore
- [x] **1. Risk spikes + deploy early:** one Jev call from Python via AI Gateway; one OpenRouter call; "hello" page live on Vercel
- [ ] **2. Knowledge:** `knowledge/cadre.md` from cadre.ai, a source per fact, reviewed line by line
- [ ] **3. Answering:** `prompts/system.md`, `answer.py`, streaming `/api/chat`, UI wired to the API
- [ ] **4. Routing:** Jev topic + needs-human, confidence threshold, fallback, tests for each path
- [ ] **5. Handoff + data:** Supabase schema, `/api/leads`, validation, event logging
- [ ] **6. Measure:** ~20 eval cases, runner, 3-model comparison, pick the model
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

## 5. Model comparison
*(filled in during Phase 6)*

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
| 09-23 | Test call to gpt-5-nano | Blank reply: the model spent all its tokens reasoning | Checked the output, not just the HTTP status | Empty replies are treated as errors (CLAUDE.md rule 7) |

## 7. What's next (with more time)
*(filled in as we go)*
