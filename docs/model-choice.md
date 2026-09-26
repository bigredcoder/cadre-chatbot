# Results: Jev spike, knowledge, model choice and running costs

Split out of `plan.md` on 09-25. Sections keep their old plan.md numbers, which
`build-process.md` cites.

## 4a. Phase 1 findings (Jev spike, 2026-09-23)
Ran `spikes/jev_spike.py`: 3 messages via AI Gateway `/v1/evaluate`.

| Message | topic (choice) | p | needs_human (boolean) |
|---|---|---|---|
| "Do you guys work with construction companies?" | industries | 1.00 | 0.55 |
| "How much does an engagement cost?" | pricing | 0.99 | 0.35 |
| "What's the weather in San Diego?" | off_topic | 1.00 | 0.21 |

- **Topic routing is strong.** Use Jev's `choice` for the topic.
- **A vague "needs a human?" boolean is unreliable** (construction scored above pricing).
  Decision: handoff = topic rule (planned: pricing, security, portal login; built: pricing and
  booking, while security and login gaps are handed off by the model plus Jev's check) +
  a sharper Jev boolean, "is the visitor explicitly asking for a person?", with `criteria`
  defining true and false. Re-measure in Phase 6.
- Auth works with the Vercel OIDC token locally; AI Gateway requires a card on file.
- OpenRouter (Brian's dev key): gemini-2.5-flash-lite and gpt-4.1-nano answered; gpt-5-nano returned blank (reasoning ate the token budget).
- Live: https://cadre-chatbot-xi.vercel.app. `/api/health` returns ok.

## 4b. Phase 2 findings (knowledge, 2026-09-23)
- `knowledge/cadre.md`: 77 facts from 21 cadre.ai pages, each with an exact quote and URL.
- `tools/verify_knowledge.py` string-matches every quote against the live page: 77/77 pass.
- Research was split: a general-purpose helper, doing the `site-researcher` job, covered the
  services pages while I covered industries, case studies, and contact in parallel.
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

**Full grid, all 11 models with and without Jev:** `evals/results/full-grid.md`. The with-Jev
arm replays one recorded set of routes, so every model gets the same topic score by
construction (that recording scored 100%). On answer checks, Jev was better for 7 models, tied
for 3, worse for 1 (gpt-4o-mini: 4 vs 2 failures). Example: gpt-4.1-nano without Jev invented a
LinkedIn URL.

**Why Jev for routing** (benchmark, same model, same cases, `docs/jev-routing.md`): topic
labels 40/40 vs 34/40, median routing 0.38 s vs 0.66 s. Answers about the same (51 vs 50 of
52), p90 routing worse (1.3 s vs 0.8 s), Jev's cost unmeasured (recorded $0 on free credits),
and the baseline got only topic names, not Jev's definitions (`app/router.py:92` vs `:47`).
Kept for typed decisions with confidence (plan.md §3); its rate limits are covered by a
proven fallback.

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

## 5a. Running costs (Brian, 09-23)
Actual where measured; ESTIMATE / ASSUMED where not.

| Item | What it is | Cost now (demo) | At production scale |
|---|---|---|---|
| **Vercel hosting** | Hobby plan: the app, deploys, OIDC auth | **$0** | Hobby is for non-commercial use; a real Cadre deployment would need a paid plan (ASSUMED ~$20 per team member/month, check Vercel pricing) |
| **Supabase database** | Project `cadre-chatbot` (conversation storage) | **$10/month** (quoted by Supabase when created; Brian deleted another project to offset it) | Same, until storage or traffic outgrows the compute size |
| **Answer model** | gemini-2.5-flash via OpenRouter | ~**$0.91 per 1,000 answers** (measured in evals) | Scales with traffic: 10,000 answers/month ≈ $9 (ESTIMATE) |
| **Jev routing** | typesafe-ai/jev via Vercel AI Gateway | **$0 so far** (free credits); Jev's own price per call is unmeasured (recorded as $0 on every Jev-routed benchmark turn) | Unknown until billed; a higher rate-limit tier may cost more |
| **Domain** | Using the free `cadre-chatbot-xi.vercel.app` | $0 | ~$10–20/year for a custom domain (ESTIMATE) |
| **Build and testing spend** | Dev OpenRouter key: evals, 11-model comparisons, benchmarks | **$2.46 so far** (actual, 09-23) | Each full eval run of one model ≈ $0.02–0.25 depending on model |

**Demo total:** about **$10/month** fixed (Supabase), plus under $1 in model usage for the
review (ESTIMATE). **Cost per answer, variable:** ~$0.001 (answer model; Jev's cost unmeasured).
