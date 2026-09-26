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

## Evidence (gemini-2.5-flash, same 26 cases, 52 runs: `evals/results/bench-*-jev.json`)
| | With Jev | Without Jev (chat model routes) |
|---|---|---|
| Topic labels correct (40 runs have an expected topic) | 40/40 | 34/40 |
| Answer checks passed (every check except the topic label) | 51/52 | 50/52 |
| Handoff decisions correct (36 runs whose case says hand off or not: 23 yes, 13 no) | 35/36 | 34/36 |
| Off-topic and injection runs passed | 7/7 | 7/7 |
| Critical failures | 0 | 0 |
| Routing time, median / p90 | 0.38 s / 1.3 s | 0.66 s / 0.8 s |
| Routing cost | Jev: unmeasured (recorded $0 on all 39 Jev-routed turns, on free credits); 13 fallback calls: $0.00089 | $0.0038 (52 calls) |
| Cost per turn (answer + routing) | $0.000997 | $0.000836 |

- 6 of the 8 misses without Jev are wrong labels on replies that passed every other check.
  Every miss, with its real reply: `evals/results/bench-failures.md`.
- Handoff misses: both arms offered a person needlessly on `portal-where-is-it`; without Jev
  it also missed the handoff on `gap-maturity-index-free`.
- The p90 is worse with Jev because 13 of 52 turns fell back to the chat model after trying
  Jev (11 on HTTP 429, 2 unsure).
- Cost per turn is higher with Jev because of the answer model's bill, not routing. The same
  case with the same input tokens was billed about $0.0014 in some runs and $0.0005 in others,
  likely prompt caching (the result files don't record cache hits). 31 of 52 turns with Jev
  were billed at the higher level, vs 17 of 52 without.
- 11-model grid (`evals/results/full-grid.md`): the with-Jev arm replays one recorded set of
  routes, so every model gets the same topic score by construction (that recording scored
  100%). On answer checks, Jev was better for 7 models, tied for 3, and worse for 1
  (gpt-4o-mini: 4 vs 2 failures).

How it was measured, including two invalid runs and why they were thrown out:
`build-process.md`, Phase 6 (its Jev figures are superseded by the 09-25 entry "Jev claims
match the data; route replay fixed", commit `33eb401`).

## Limits and next steps
- Not an equal test: the fallback classifier gets only the topic names (`app/router.py:92`);
  Jev gets their definitions (`app/router.py:47`). Next: give both the definitions and rerun.
- Rate limits: production needs a higher AI Gateway tier; alert when the fallback rate rises.
- The 10 topic definitions are hand-written. The next step is to tune them against labeled
  real questions from `chat_turns`.
