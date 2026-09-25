# Cadence: a support chatbot for Cadre AI

**Reviewing this?** Start with [`REVIEW-GUIDE.md`](REVIEW-GUIDE.md): one page, organized by scoring area.

**Live:** https://cadre-chatbot-xi.vercel.app. Click **Ask Cadre's AI** (bottom right).
Turn on **Behind the scenes** to see how each answer was routed, which model answered, the
time it took, and what it cost.

Cadence answers common questions about Cadre AI using **only facts Cadre has published**
(each one quoted and sourced), routes every message with **Jev**, and hands people to a real
strategist when it can't or shouldn't answer. Built as a take-home for Cadre AI's Staff
Forward Deployed AI Engineer role.

## What it does
- Answers the brief's scenarios: services, industry fit, booking a call, the client portal,
  the AI Maturity Index, model selection, and data security.
- Never invents prices, certifications, client names, or response times. It says so and
  offers a strategist.
- A handoff form with the same fields as cadre.ai/contact, prefilled from the conversation.
  **Demo only:** it validates and confirms, and sends and stores nothing (the confirmation says so).
- Saves conversations for quality review: **redacted** (emails, phone and card numbers removed
  before saving, and before anything reaches a model provider), **deleted after 30 days**, and the site's key can only write, never read.

## How it works
```
Browser widget (public/index.html)
   │  POST /api/chat → streamed answer (Server-Sent Events)
   ▼
FastAPI on Vercel (app/main.py: routes only)
   ├─ guards.py       per-visitor rate limit (length and history caps: main.py)
   ├─ chat.py         one turn: redact → route → answer → handoff decision → save; deadlines
   ├─ router.py       Jev picks the topic and "asks for a person?" → handoff rules
   │                  (rate-limited → one retry; unsure, down, or still limited → the chat
   │                  model routes instead; routing capped at 10 s)
   ├─ answer.py       system prompt + sourced knowledge → gemini-2.5-flash via OpenRouter
   └─ transcripts.py  redact → save one row per turn to Supabase (insert-only)
```
Details: `docs/jev-routing.md` (routing), `db/schema.sql` (data), `plan.md` (decisions).

## Evidence behind the choices
- **Model:** 11 models, same 26 test cases, identical routing. Three scored 52/52;
  gemini-2.5-flash was the fastest of them. See `plan.md` §5 and `evals/results/full-grid.md`.
- **Jev:** with vs. without Jev, for all 11 models: Jev made every model more accurate and
  faster, and cheaper for 10 of 11 (equal for one). For gemini-2.5-flash: 52 vs 44 correct.
- **Research:** design changes traced to a 2026 chatbot research review:
  `docs/research/findings.md`.
- **Failures shown, not summarized:** every eval failure has the real reply in
  `evals/results/*-failures.md`.

## Run it locally
```bash
python3 -m venv .venv && .venv/bin/pip install fastapi httpx pytest ruff uvicorn pyyaml pytest-playwright mypy
cp .env.example .env            # add your OPENROUTER_API_KEY
vercel link && vercel env pull  # optional: Jev auth via a Vercel OIDC token in .env.local
.venv/bin/uvicorn app.main:app --reload    # http://localhost:8000
```
Without a Jev credential, routing falls back to the chat model automatically.

## Deploy
1. Import the repo into Vercel (the framework is set to FastAPI in `vercel.json`).
2. Set `OPENROUTER_API_KEY` in the project's environment. Jev authenticates with Vercel's own
   per-request token, so it needs no key.
3. Recreate the firewall rule, which is a project setting and not part of the repo:
   `vercel firewall rules add "Chat API rate limit per IP" --condition '{"type":"path","op":"pre","value":"/api/"}' --condition '{"type":"method","op":"eq","value":"POST"}' --action rate_limit --rate-limit-window 60 --rate-limit-requests 20 --rate-limit-keys ip --yes && vercel firewall publish --yes`
4. Check `/api/health` after the deploy ("Ready" alone doesn't prove the app runs).

## Test it
| Command | What it checks | Cost |
|---|---|---|
| `.venv/bin/python -m pytest -q` | 63 unit tests (Python + the widget's JS rendering), network faked | $0 |
| `.venv/bin/python -m pytest e2e -q` | 10 browser tests: Chromium desktop + iPhone 14 in WebKit (keyboard, form, overflow) | ~$0.01 |
| `.venv/bin/python tools/load_test.py` | Concurrent visitors + a rate-limit burst, live site (the burst now also trips the Vercel firewall rule) | ~$0.03 |
| `.venv/bin/python tools/verify_knowledge.py` | Every knowledge quote still matches cadre.ai | $0 |
| `.venv/bin/python -m evals.run --repeat 3` | 26 real questions, code-scored | ~$0.05 |
| `.venv/bin/python -m evals.compare --routes evals/results/routes-jev.json` | The model comparison | ~$0.50 |

## How it was built
With Claude Code, one phase at a time, with each commit reviewed and approved.
- `CLAUDE.md`: the rules Claude works under. `plan.md`: scope, decisions, AI-bug log.
- `build-process.md`: what actually happened, step by step.
- `.claude/agents/`: `site-researcher`, `eval-writer`, `code-reviewer` subagents.
- `.claude/commands/`: `/eval`, `/add-knowledge`, `/ship`.
- `.claude/hooks/pre_commit_gate.py`: blocks any commit if lint, the type check, or unit tests fail.

## Running costs
About **$10/month** fixed (Supabase) plus about **$0.001 per answer** (model + Jev); hosting
is on Vercel's free plan. Breakdown: `plan.md` §5a.
