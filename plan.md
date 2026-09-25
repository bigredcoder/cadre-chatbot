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
| **Chat window = Deep Chat** (changed 09-23) | A proven component for the solved problem (streaming, scroll, mobile); our effort goes to grounding, routing, and evals. Research: hybrid is the most practical deployment | A 387 KB dependency; self-hosted so no third-party script can take the page down |
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
- [x] **6. Measure:** ~20 eval cases, runner, 3-model comparison, pick the model
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

**Why this model: `google/gemini-2.5-flash` (Brian's decision, 09-23)**
- **Accuracy first:** 52/52 with no critical or major failures, one of only three perfect
  models of the 11 tested with identical routing.
- **Speed decided among the perfect three:** 1.0 s median vs 1.3 s (gpt-4.1-mini) and 2.0 s
  (claude-haiku-4.5). Speed is what a visitor feels.
- **Cost is acceptable, not the lowest:** ~$0.91 per 1,000 answers (ESTIMATE from eval runs):
  about 1.7× gpt-4.1-mini, and about 5× cheaper than claude-haiku-4.5. A $5 key covers
  roughly 5,000 answers.
- **Why not the runners-up:** gemini-2.5-flash-lite is faster and 4.5× cheaper but made one
  major error (a needless handoff); gpt-4.1-mini is a strong, cheaper backup if cost matters
  more than 0.3 s; llama-4-maverick printed its system prompt 3/3 times.
- **Limits:** 52 runs on one test set can't prove zero failures (research §8). Rerun the evals
  whenever the prompt, knowledge, or model changes.

**Full grid, all 11 models with and without Jev:** `evals/results/full-grid.md`. Jev improved
accuracy and speed for **every** model (11/11), and cost for 10 of 11 (gpt-oss-120b: equal). Examples: gemini-2.5-flash 52 vs 44
correct; gpt-oss-120b 51 vs 16 (it misrouted 88% of messages on its own); gpt-4.1-nano
without Jev invented a LinkedIn URL.

**Why Jev for routing** (benchmark, same model, same cases): 51 vs 44 passes, topic labels
100% vs 85%, routing 0.38 s vs 0.66 s, and 4× cheaper per decision than letting the chat model
route. Its rate limits are covered by a proven fallback. Full write-up: task in §6a.

Fair comparison, 2026-09-23 (**corrected** the same day after reviewing every failing reply;
see "Correction" below): 26 cases, critical cases ×3 (52 runs per model), **identical Jev
routing for every model** (`evals/results/routes-jev.json`), code-only scoring.
Failure examples: `evals/results/compare-fixed-failures.md`. Latency excludes routing (+~0.4 s live).

| Model | Passed | Critical | Major | Median | $/answer |
|---|---|---|---|---|---|
| **google/gemini-2.5-flash** | **52/52** | 0 | 0 | **1.0 s** | 0.00091 |
| openai/gpt-4.1-mini | 52/52 | 0 | 0 | 1.3 s | 0.00055 |
| anthropic/claude-haiku-4.5 | 52/52 | 0 | 0 | 2.0 s | 0.00437 |
| openai/gpt-oss-120b | 51/52 | 0 | 0 | 5.0 s | 0.00024 |
| deepseek/deepseek-chat-v3.1 | 51/52 | 0 | 1 | 3.9 s | 0.00061 |
| google/gemini-2.5-flash-lite | 51/52 | 0 | 1 | 0.8 s | 0.00020 |
| mistralai/mistral-small-3.2-24b-instruct | 49/52 | 0 | 3 | 2.3 s | 0.00035 |
| openai/gpt-4o-mini | 48/52 | 0 | 3 | 1.5 s | 0.00038 |
| qwen/qwen3-235b-a22b-2507 | 46/52 | 0 | 3 | 2.1 s | 0.00019 |
| openai/gpt-4.1-nano | 48/52 | 0 | 4 | 1.1 s | 0.00017 |
| meta-llama/llama-4-maverick | 48/52 | **3** | 1 | 1.1 s | 0.00077 |
| openai/gpt-5-nano, gpt-5-mini | excluded | | | | |

(GPT-5 nano/mini: blank replies on 48–49 of 52 runs; reasoning consumed the 500-token budget.)
Only real critical failure: llama-4-maverick printed its full system prompt, 3 of 3 times.
The most common real major failure: showing the strategist form for simple questions
("Where's the portal?").

**Correction (09-23):** an earlier version of this table claimed "7 of 11 models implied a
SOC 2 certification." False. Reviewing the actual replies (Brian asked for examples) showed
they were correct ("Cadre doesn't publish its security certifications publicly"). The checker
was too strict: exact wording, curly apostrophes, non-breaking hyphens, markdown bold. Fixed
the checker, scored failures by *what* failed (see evals/README.md), and rescored the saved
replies with no new calls.

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
| 09-23 | eval-writer subagent claimed 3 knowledge quotes didn't match cadre.ai | False: its web tool summarizes pages and loses detail | Re-ran `verify_knowledge.py`: 77/77 still match live HTML | Kept the facts; rule: facts are checked by script, never by an AI's reading |
| 09-23 | 2 eval cases written too strictly | They failed correct, safe answers (test bugs, not bot bugs) | Read each failing reply before judging | Widened the expected wording; logged as test fixes |
| 09-23 | Claude's summary of the model comparison: "7 of 11 models implied a SOC 2 certification"; "without Jev the handoff never fired" | Both false. The replies were correct; the checker was too strict (wording, curly quotes, bold) and scored a wrong topic label as critical | Brian asked for real examples of each error; reading them exposed it | Checker normalizes text; severity comes from what failed; saved replies rescored; failure-example reports generated automatically |
| 09-23 | Code written across Phases 3–5 | code-reviewer subagent found 8 issues: a stream that could end silently ("Writing an answer…" forever), client-controlled history size, transcript save delaying the UI, a form promising a follow-up the demo never sends, a whitespace name 500, Start over leaking into the new chat, short phones unredacted, a stale .env.example | Pre-submission review by the `code-reviewer` subagent; each claim checked against the code first (it had been wrong once before) | All 8 fixed with regression tests (50 unit tests); verifying #7 also exposed dates being redacted as phones, now fixed |
| 09-23 | The chat window: hand-built by Claude (Phases 3–7) | Never put build-vs-use-a-component in front of Brian, though the research weighs buy vs. build vs. hybrid and the brief allows component libraries. The result jumped, overflowed on iPhone, and zoomed on input focus | Brian's own iPhone (screenshots); Claude had tested only Chromium at phone size, never Safari's engine | Replaced with Deep Chat (MIT, self-hosted); WebKit iPhone tests added that fail on any horizontal overflow or sub-16px input |
| 09-23 | Test call to gpt-5-nano | Blank reply: the model spent all its tokens reasoning | Checked the output, not just the HTTP status | Empty replies are treated as errors (CLAUDE.md rule 7) |
| 09-24 | Source-link rendering, the redaction rule, and the answer check (Claude, 09-23/24) | The label code threw on a path like `cadre.ai/foo-` and froze the input; 16-digit card numbers passed the phone rule unredacted; the answer check could hide the button while the reply promised a strategist; main.py had grown logic that CLAUDE.md said it doesn't hold | A skeptical pre-submission audit (Claude reviewing its own work, with the live bot and the code) | All fixed with regression tests: 7 JS render tests, card redaction test, offer and timeout tests; logic moved to `app/chat.py` |
| 09-24 | Redaction moved before the model call (Claude) | The phone rule judged digit count, so "budget 25000-50000" reached the model as "[phone removed]", breaking pricing questions; 26/26 evals passed because no case had numbers | The `/ship` command's code-reviewer subagent, in a headless Claude Code run (`docs/claude-code-runs/`) | Phone *shape* rule plus a regression test for budgets, revenue, and team sizes |

## 5a. Running costs (Brian, 09-23)
Actual where measured; ESTIMATE / ASSUMED where not.

| Item | What it is | Cost now (demo) | At production scale |
|---|---|---|---|
| **Vercel hosting** | Hobby plan: the app, deploys, OIDC auth | **$0** | Hobby is for non-commercial use; a real Cadre deployment would need a paid plan (ASSUMED ~$20 per team member/month, check Vercel pricing) |
| **Supabase database** | Project `cadre-chatbot` (conversation storage) | **$10/month** (quoted by Supabase when created; Brian deleted another project to offset it) | Same, until storage or traffic outgrows the compute size |
| **Answer model** | gemini-2.5-flash via OpenRouter | ~**$0.91 per 1,000 answers** (measured in evals) | Scales with traffic: 10,000 answers/month ≈ $9 (ESTIMATE) |
| **Jev routing** | typesafe-ai/jev via Vercel AI Gateway | **$0 so far** (free credits); ~$0.02 per 1,000 messages at list price (measured cost field) | ~$0.20 per 10,000 messages (ESTIMATE); a higher rate-limit tier may cost more (unknown) |
| **Domain** | Using the free `cadre-chatbot-xi.vercel.app` | $0 | ~$10–20/year for a custom domain (ESTIMATE) |
| **Build and testing spend** | Dev OpenRouter key: evals, 11-model comparisons, benchmarks | **$2.46 so far** (actual, 09-23) | Each full eval run of one model ≈ $0.02–0.25 depending on model |

**Demo total:** about **$10/month** fixed (Supabase), plus under $1 in model usage for the
review (ESTIMATE). **Cost per answer, all-in variable:** ~$0.001.

## 6a. Documentation tasks (for the review)
- **Jev integration write-up (Brian, 09-23):** explain how Jev is used. That means the
  10 topic definitions (`config.TOPICS`) and how Jev picks one, the "asks for a person"
  question and its true/false criteria, the confidence threshold and why it's 0.6, the
  model fallback path, how the topic feeds the answer prompt, the off-topic short-circuit,
  auth via Vercel OIDC, and the Phase 1 / Phase 4 measurements. Target:
  `docs/jev-routing.md` plus a diagram. Not started.

- **DONE 09-23 (corrected). Benchmark with vs. without Jev.** Same model (gemini-2.5-flash),
  26 cases × critical ×3: **with Jev 51/52, topic labels 100%, handoff 97%, routing 0.38 s,
  $0.000017/route**; without Jev 44/52, topic labels 85%, handoff 94%, routing 0.66 s,
  $0.000072/route. **Neither had a critical failure**; without Jev, replies stayed safe but
  7 were mislabeled (e.g. "Are you SOC 2 certified?" filed as `company`). An earlier claim
  that "the handoff never fired" without Jev was wrong: the model's own tag still showed
  it. Caveat: Jev returned HTTP 429 on 11/52 calls even sequentially (the fallback covered
  them). Files: `evals/results/bench-*.json`, failure examples in `bench-failures.md`.
- *(original task)* **Benchmark with vs. without Jev (Brian, 09-23):** run the same eval set two ways,
  (a) Jev routing + rules and (b) chat-model-only routing (the fallback path, forced on),
  and compare topic accuracy, handoff accuracy, latency (median and slow tail), cost per
  conversation, and off-topic/injection handling. It answers "was Jev worth adding?" with
  data. Easy to run: `route()` already has both paths; add a flag to force the fallback.
  Do it in Phase 6 alongside the model comparison. Not started.

## 6b. Changed by Brian after device testing (09-24)
- The privacy banner (09-23) and the "How chat data is used" menu link (09-24) were removed at
  Brian's request. Trade-off: the research recommends a short privacy note in the chat
  (findings #8). The `/privacy.html` page still exists and is accurate; in production it would
  be linked from the site footer or the chat.

## 7. What's next (with more time)
- **Jev usage tier (Brian, 09-23):** Jev returned HTTP 429 (rate limited) on ~20% of calls in
  sequential testing. For production traffic, move to a paid or higher AI Gateway tier. The
  **fallback is already built and proven:** on 429/503 the router retries once after 0.3 s,
  then the chat model routes the message. In evals, all 11 rate-limited calls were answered
  normally. Optional next steps: a short-lived route cache for repeated questions, and an
  alert when the fallback rate passes a threshold (the `router` column in `chat_turns`
  already records it).
- Reasoning models (GPT-5 family): test with reasoning effort set to minimal and a larger token budget.
- **Rate limiting that holds across instances:** move `guards.py` counters to a shared store
  (or Vercel firewall rules). **Proven necessary 09-23:** a 25-message burst from one visitor
  spread across instances and none was limited (`evals/results/load-test.log`).
- **Real lead capture:** replace the demo form with a `leads` table (insert-only) plus a CRM
  sync (schema sketched in `db/schema.sql`); measure qualified meetings, not form fills.
- **One-line embed for cadre.ai:** a `<script>` tag that loads the widget on any page.
- **Content-gap review:** a weekly query on `chat_turns` (top handoff and off-topic topics)
  feeding `/add-knowledge`; a small dashboard later.
- **Evals in CI:** run unit tests on every push, and `evals.run` nightly with a zero-critical gate.
- **Tune Jev's topic definitions** against labeled real questions from `chat_turns`.
- **Accessibility:** a manual pass with a screen reader user, beyond the automated checks.
- **A/B test** the widget against the plain contact page for qualified-meeting rate (research §8).
