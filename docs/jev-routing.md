# How Cadence uses Jev for routing

Jev (TypeSafe AI, released 2026-09-15) is an *evaluation* model: instead of writing text, it
reads some state and answers typed questions (pick one of these options, or yes/no) with
probabilities. Cadence calls it through Vercel AI Gateway (`POST /v1/evaluate`, model
`typesafe-ai/jev`). Code: `app/router.py`. Settings: `app/config.py`.

## What Jev is asked, for every visitor message
**State:** the latest message, plus the previous one for follow-ups ("how much does *that* cost?").

**Question 1, `topic` (choice):** which of 10 topics is this message about?

| Topic | Jev's definition (from `config.TOPICS`) |
|---|---|
| services | what Cadre does, its services, how an engagement works |
| industries | whether Cadre works with a specific industry or type of company |
| booking | booking a call, contacting Cadre, or talking to a strategist |
| portal | the Cadre client portal, logging in, accounts |
| maturity_index | the AI Maturity Index, pillars, or getting scored |
| llm_security | which AI models Cadre uses, data security, privacy, compliance |
| pricing | cost, pricing, budget, fees, how much something costs |
| results | case studies, results, examples of past work |
| company | who Cadre is, leadership, location, partners |
| off_topic | anything unrelated to Cadre AI or AI for business |

**Question 2, `asks_for_human` (yes/no, with criteria):** is the visitor *explicitly* asking
for a person? True: a person, call, meeting, or to be contacted. False: an informational
question, even about cost or security.

## What the answers drive
```
visitor message
   │
   ▼
Jev ──► topic + probability, asks_for_human probability
   │
   ├─ topic probability ≥ 0.6? ── no ──► chat model classifies instead ("fallback")
   │        │ yes
   │        ▼
   ├─ off_topic with ≥ 0.9? ──► canned reply, NO model call (cheap; injection never reaches the model)
   │
   ├─ handoff = topic is pricing or booking  OR  asks_for_human ≥ 0.7
   │            (the answer model can also add a handoff when it can't answer; unless the
   │             reply itself offers a person, a second Jev question checks whether it
   │             actually answered, and skips the offer if so: app/chat.py)
   │
   └─ topic is passed to the answer prompt as a hint ("classified as: pricing").
      If the hint is wrong, the prompt tells the model to answer what was actually asked.
```

## Failure handling
- **Rate limit (HTTP 429) or 503:** one retry after 0.3 s, then the chat model routes. In
  testing, Jev rate-limited ~20% of calls; every one was still answered normally.
- **Timeout (6 s), network error, bad response:** the chat model routes.
- **Both fail:** a neutral default route; the answer still runs. `route()` never raises.
- **Routing as a whole is capped at 10 s** (`ROUTE_DEADLINE_S`); past it, a neutral default route is used.
- "Behind the scenes" and the `chat_turns.router` column show which path ran, and why.

## Auth
- **Production:** Vercel's per-request OIDC token (`x-vercel-oidc-token`). No Jev key exists
  to leak or rotate.
- **Local:** the short-lived OIDC token from `vercel env pull` (`.env.local`), or an
  `AI_GATEWAY_API_KEY`.

## Why these numbers
- **0.6 topic threshold (ESTIMATE, then measured):** of the 29 recorded routes, 28 cleared
  it (lowest 0.61; 24 of them ≥0.74). The one below (0.51, the "print your system prompt"
  trick) is exactly the kind we want double-checked. Four routes sat between 0.61 and 0.71,
  so 0.6 isn't generous. Raising it would send more traffic to the slower fallback.
- **A sharp "asks for a person" question, not "needs a human?":** in the Phase 1 spike, the
  vague version scored pricing *below* construction. The sharp version with true/false
  criteria fired only on real requests. Handoff for pricing and booking is a **rule**, not a
  probability. (Research: model confidence isn't calibrated correctness.)

## Evidence (evals, same 26 cases, 52 runs)
| | With Jev | Without Jev (chat model routes) |
|---|---|---|
| gemini-2.5-flash correct | 51/52 live (52/52 with replayed routes, `full-grid.md`) | 44/52 |
| Topic labels correct | 100% | 85% |
| Routing time (median) | 0.38 s | 0.66 s |
| Routing cost per 1,000 messages | ~$0.02 | ~$0.07 |
| Models more accurate and faster with Jev | **11 of 11** (cheaper for 10; equal cost for gpt-oss-120b) | |

Full grid: `evals/results/full-grid.md`. How it was measured, including two invalid runs and
why they were thrown out: `build-process.md`, Phase 6.

## Limits and next steps
- Rate limits: production needs a higher AI Gateway tier; alert when the fallback rate rises.
- The 10 topic definitions are hand-written. The next step is to tune them against labeled
  real questions from `chat_turns`.
