# Build process log

A running log of how Cadence was built: what we did, in what order, what we decided,
and how we checked it. Newest entries at the bottom. Updated after every meaningful step.

`plan.md` says what we're building and why. This file says what actually happened.
Each entry ends with a **Say in the review** line: the one-sentence version for the walkthrough.

---

## 2026-09-23 · Planning (before any code)
**Did**
- Read the take-home brief and the Staff FDE posting; summarized the scoring weights
  (Claude Code 30%, design 25%, scope 20%, quality 15%, communication 10%).
- Scanned cadre.ai to see which of the brief's 6 scenarios the public site can answer.
- Chose the stack: Python + FastAPI + one HTML page on Vercel (readable, matches the role).
- Chose the scope: grounded answers, human handoff with lead capture, never quote prices.
- Evaluated Jev (TypeSafe AI, released 2026-09-15) for routing. Adopted it, with a fallback.
- Researched chatbot UI conventions (chat bubble, bottom-right) and pulled cadre.ai's
  colors and fonts. Built a clickable prototype, reviewed it, fixed contrast, rechecked
  at desktop and phone size.
- Chose the persona "Cadence," labeled as AI (disclosure), with a brand mark, not a face.

**Decided**
- A development OpenRouter key for building and testing. Cadre's key goes in only for the
  final deployment.
- One version, AI-assisted, with me directing and approving every commit.

**Checked**
- Python on Vercel and Jev's Python access, against Vercel's docs, before committing to them.

**Say in the review:** "I treated you as the client: I read your site, found what it can and can't answer, and scoped the bot around that before writing code."

---

## 2026-09-23 · Phase 0: Foundation · commit `73b0d90`
**Did**
- Created the repo and a private GitHub remote. Commits authored as brian@editorr.com.
- Wrote `CLAUDE.md`: stack, file map, 8 hard rules (sourced facts only, no prices, AI
  disclosure, secrets, no transcripts, empty replies are errors), and the workflow.
- Wrote `plan.md`: discovery, scope in/out with reasons, decisions table, phases, AI-bug log.
- `.gitignore` and `.env.example` (key names only).

**Say in the review:** "CLAUDE.md is onboarding for a fast junior dev with no memory. It's short, opinionated, and every rule exists because of a real risk."

---

## 2026-09-23 · Phase 1: Risk spikes + deploy early · commit `59f3557`
**Did**
- Jev spike (`spikes/jev_spike.py`): 3 real messages through Vercel AI Gateway `/v1/evaluate`.
- OpenRouter spike on the dev key: 3 small models.
- FastAPI skeleton with `/api/health` and a placeholder page; 2 unit tests.
- Deployed to Vercel: https://cadre-chatbot-xi.vercel.app. Push-to-deploy from GitHub works.

**Found**
- Jev topic routing is excellent (1.00 / 0.99 / 1.00). Its vague "needs a human?" boolean
  was not reliable (pricing scored below construction). → Handoff now uses topic rules plus
  a sharper, criteria-defined question.
- gpt-5-nano returned a blank reply: reasoning used up the token budget. → Empty replies are
  errors (CLAUDE.md rule 7).
- First deploy showed "Ready" but served only static files; `/api/health` returned 404.
  → Pinned the FastAPI framework in `vercel.json`. Now always check `/api/health` after a deploy.
- Vercel's CLI rewrote `.gitignore` in a way that would hide `.env.example`. → Reverted it.
- Added `.vercelignore` so `.env*` is never uploaded. Confirmed `/.env` returns 404 live.

**Blocked / unblocked**
- AI Gateway requires a card on file, even for free credits. Card added; spike passed.

**Say in the review:** "Before building on Jev, I measured it. Topic routing was near perfect, but the vague 'needs a human' question wasn't, so I designed around that."

---

## 2026-09-23 · Phase 2: Knowledge · commit `c460fff`
**Did**
- Defined the `site-researcher` subagent (`.claude/agents/`): read-only, cadre.ai only,
  every fact needs an exact quote and URL.
- Ran research in parallel: the subagent read the 6 services pages; I read the industry,
  department, case study, and contact pages.
- Wrote `knowledge/cadre.md`: 77 facts from 21 pages, plus a "Not public" list the bot
  must never answer (pricing, portal login, certifications, and more).
- Wrote `tools/verify_knowledge.py`: downloads each cited page and string-matches the quote.

**Found**
- The first scan missed facts that deeper research found: all 8 Maturity Index pillar
  names, real data-security statements, support email/phone/address.
- The checker failed 2 of 77 quotes. Both were formatting (split markup, non-breaking
  hyphen), not wrong facts. Fixed the normalizer → 77/77 pass.

**Checked**
- `python tools/verify_knowledge.py` → 77 quotes checked, 0 failed.
- Brian reviewed the knowledge file and approved it as-is: only the CEO named, case-study
  numbers allowed (quoted exactly), and Cadre's own MIT statistic kept, attributed to Cadre.

**Say in the review:** "Every fact the bot can say has an exact quote and a source URL, and a script checks all 77 against your live site."

---

## 2026-09-23 · Process: build log + deep research
**Did**
- Started this file, `build-process.md`, backfilled from planning onward. Added a
  CLAUDE.md rule: append an entry at the end of every phase (did / found / decided / checked).
- Commissioned deep research on what makes a website AI chatbot succeed in 2026:
  UX, knowledge quality, architecture, privacy/security, handoff, real success and failure
  cases, and evaluation. The prompt is saved verbatim in `docs/research/deep-research-prompt.md`.

**Why**
- Phases 3–6 (answering, routing, handoff, evaluation) are where design choices matter
  most. Decisions there should rest on evidence, not habit.

**Next**
- When the report returns: summarize it in `docs/research/findings.md`, compare it with
  current decisions, and log any changes in `plan.md` before building Phase 3.

**Say in the review:** "I commissioned research on what makes website chatbots succeed and fail, and changed the design where the evidence said to."

---

## 2026-09-23 · Phase 3 prep: system prompt draft v1 · not committed yet
**Did**
- Drafted `prompts/system.md` (Brian owns it). Sections: identity and AI disclosure, the
  job, the grounding rule, handoff triggers, off-topic, answer style, safety, router hint,
  3 worked examples, and the knowledge inserted at runtime.

**Decided**
- **Handoff is a tag, not free text.** The model ends a reply with `[HANDOFF]` and the code
  shows the form. The model never collects names or emails itself: that stays in a real
  form with validation.
- **The router's topic is a hint, not a command.** If Jev's label is wrong, the model
  answers what was actually asked.
- Pricing always hands off; portal login, certifications, and contracts do too.

**Next**
- Revise after the deep-research findings, then Brian approves the final wording.

**Say in the review:** "The prompt has one rule above all: only say what's in the sourced knowledge. When the bot should hand off, it emits a tag and the code takes over, so the model never handles personal data."

---

## 2026-09-23 · Research received and applied to the design
**Did**
- Saved the deep-research report: `docs/research/website-ai-chatbot-research-2026.md`
  (sources dated through Sep 2026, each with an evidence-strength label).
- Wrote `docs/research/findings.md`: what it means for Cadence. 8 decisions confirmed and
  17 numbered changes, each tied to its evidence and the file or phase it affects.
- Linked the research from `CLAUDE.md` (read before UX, prompt, or eval work) and `plan.md`.

**Found**
- Our scope matches the report's "Lean" level for a professional-services site.
- Its guidance that model confidence isn't calibrated correctness matches what we measured
  with Jev in Phase 1.
- New work: a labeled launcher, an answer contract, recover-once-then-hand-off, focus and
  screen-reader handling, link allow-list, privacy line, prefilled handoff, idempotent lead
  submit, graceful failure, severity-scored evals with a zero-critical gate.
- 12 of the report's 30 test scenarios don't apply (no accounts, orders, bookings, or
  localization). Marked N/A with reasons instead of padding the test set.

**Decided (Brian approved)**
- System prompt v2: an answer contract (answer → condition → source → next step),
  recover-once-then-hand-off, a link allow-list, and no promised response times.

**Say in the review:** "I didn't design from habit. I commissioned research, kept what it confirmed, changed 17 things it challenged, and each change is traceable to a source."
