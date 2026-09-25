# CLAUDE.md: Cadence (Cadre AI support chatbot)

Read `plan.md` before starting any task. It holds scope, phases, and decisions.
This file tells you how to work in this repo. If the two ever disagree, stop and ask.

## What this is
Cadence is a customer-support chatbot for Cadre AI's website. It answers common
inbound questions using ONLY facts published by Cadre, routes every message with
Jev (TypeSafe AI) via Vercel AI Gateway, and hands people to a human strategist when
it can't or shouldn't answer. The live app is a chat bubble on a demo page.

## Stack (deliberately boring)
- Python 3.12+, FastAPI, deployed on Vercel (Python runtime, SSE streaming)
- UI: one HTML page (`public/index.html`) around Deep Chat, an MIT chat web component
  self-hosted at `public/vendor/` (no CDN, no build step). Answer rendering is in
  `public/render.js`. No frontend framework, no npm.
- OpenRouter for answer generation; Jev via Vercel AI Gateway for routing
- Supabase Postgres: one table, `chat_turns` (redacted, 30-day retention, insert-only key)
- pytest for unit tests (it also runs the JS tests in `tests/js/` via Node); Playwright
  browser tests in `e2e/`; `evals/` for answer-quality tests

Don't add a framework, ORM, vector DB, or new dependency without asking. Small and
explainable beats clever. Every file should be readable top to bottom by a non-specialist.

## Layout (target; check what exists before assuming)
- `app/main.py`: routes only (HTTP in, Server-Sent Events out). No business logic here.
- `app/chat.py`: one chat turn: redact → route → answer → decide the handoff → save. Per-stage deadlines.
- `app/config.py`: every model name, threshold, and limit. No magic numbers elsewhere.
- `app/router.py`: Jev routing plus the fallback to the chat model
- `app/answer.py`: builds the prompt, calls OpenRouter, streams
- `app/transcripts.py`: redacts, then saves one row per turn to Supabase `chat_turns`
  (insert-only key; schema in `db/schema.sql`). `/api/leads` in main.py is a DEMO form.
- `app/guards.py`: per-visitor rate limit (in memory, per instance: see its docstring)
- `prompts/system.md`: Cadence's instructions. **Brian owns this file. Propose edits, don't rewrite it.**
- `knowledge/cadre.md`: the ONLY source of facts about Cadre
- `evals/cases.yaml`: **Brian owns the final list.** `evals/run.py` runs them.
- `tests/`: unit tests. No network calls, ever. Mock OpenRouter, Jev, and Supabase.

## Research (read before UX, prompt, handoff, or eval work)
- `docs/research/findings.md`: what the 2026 chatbot research means for Cadence, as a
  numbered list of changes (#1–#17) with evidence strength. Cite the # when implementing one.
- `docs/research/website-ai-chatbot-research-2026.md`: the full report. `§` refs point here.
- Don't contradict a finding without logging why in plan.md → Key decisions.

## Hard rules
1. **No fact without a source.** Every line in `knowledge/` cites a cadre.ai URL or
   the brief. If you can't cite it, it doesn't go in.
2. **The bot never invents** prices, client names, results, security policies, or
   pillar names. Unknown → say so and offer the handoff.
3. **Cadence always identifies as an AI assistant.**
4. **Secrets live in `.env` only.** Never print, log, commit, or echo a key. Never
   read `.env` values into your context. Use `.env.example` for names.
5. **Cadre's OpenRouter key is off-limits** until Brian explicitly approves the final
   swap. All development uses Brian's own key.
6. **Transcripts are stored only redacted** (emails, phone and card numbers removed before
   saving), deleted after 30 days, and described on `/privacy.html` (not linked from the
   widget: Brian's call, plan.md §6b). Handoff form submissions are never stored (demo).
7. **Empty model replies are errors.** Some reasoning models return blank text when
   they run out of tokens (seen 2026-09-23 with gpt-5-nano). Never show a blank bubble.
8. Every behavior change ships with a unit test or an eval case.

## How we work
- One phase from `plan.md` at a time. Finish, verify, explain, then Brian approves the commit.
- Small commits, imperative messages ("Add Jev router with model fallback").
- Before any commit: `ruff check .`, `mypy app`, and `pytest -q` must pass (the hook in
  `.claude/hooks/` enforces it).
- When you're unsure, or the code gets bigger than the problem, stop and say so.
- When Brian rejects or corrects your output, log it in plan.md → "AI-bug log".
- **Never report an eval failure without its real example** (question, actual reply, what
  the check caught). Read failing replies before claiming a model failed: checks can be wrong.
  `python -m evals.report <label>` writes them.
- **Keep `build-process.md` current.** After every meaningful step (not just phase ends),
  append or update an entry: did / found / decided / checked / commit hash. Facts only,
  no marketing. It's the record of how the app was built, so never let it fall behind.

## Commands (always use the project venv: `.venv/bin/...`)
- First-time setup: `python3 -m venv .venv && .venv/bin/pip install fastapi httpx pytest ruff uvicorn pyyaml pytest-playwright mypy && .venv/bin/playwright install chromium webkit`
  (don't `pip install -e .`: the repo isn't laid out as a package, and it fails)
- Run locally: `.venv/bin/uvicorn app.main:app --reload` (then open http://localhost:8000)
- Unit tests (Python + JS): `.venv/bin/python -m pytest -q` (JS tests need Node; skipped without it)
- Browser tests: `.venv/bin/python -m pytest e2e -q` (live site; `BASE_URL=` for local)
- Answer-quality tests: `.venv/bin/python -m evals.run` (costs a few cents; uses the configured model)
- Lint and types: `.venv/bin/ruff check .` and `.venv/bin/python -m mypy app`
- Deploy: push to `main` on GitHub (Vercel auto-deploys). Preview: `vercel deploy`

## Gotchas
- "Ready" on Vercel doesn't mean the app runs. After every deploy, hit `/api/health`.
  The project's framework must be FastAPI (`vercel.json`), or Vercel serves only static files.
- `.vercelignore` keeps `.env*` out of uploads. Never delete it.
- Files in `public/` are served statically on Vercel and are NOT inside the Python
  function. Link to `/page.html` directly; never `FileResponse` them from a route that only
  exists in Python (that 500'd `/privacy` on 09-23).
- Vercel reads files relative to the project root, not the module's folder.
- OpenRouter returns usage/cost only when the request sets `"usage": {"include": true}`.
