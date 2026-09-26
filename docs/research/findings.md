# Research findings → what changes in Cadence

Source: `docs/research/website-ai-chatbot-research-2026.md` (deep research, 23 Sep 2026).
The prompt that produced it is in `docs/research/deep-research-prompt.md`.
Section numbers (§) refer to the report. Evidence labels are the report's own:
Strong / Moderate / Limited / Proposed.

## Where Cadence sits
- **Use case:** professional services, meaning explain scope, route inquiries, and connect
  people to a strategist (§2). The report's outcome for this is "suitable appointments
  attended," not forms filled. So we measure qualified handoffs, not raw lead count.
- **System type:** retrieval-style assistant over a small approved source pack, with a human
  route. It takes no actions on anyone's account (§2, "Hybrid").
- **Implementation level:** "Lean": approved public content, few tasks, direct contact
  route, no autonomous transactions, named owner, cost cap (§9). This confirms our scope.

## What the research confirms (no change needed)
| Our decision | Research support | Strength |
|---|---|---|
| Knowledge in the prompt, not a vector DB | "Long context: small, bounded source pack can be supplied directly" (§3 knowledge methods) | Proposed, reasoned |
| Every fact sourced; "not public" list | Knowledge as a maintained publication; exclude unapproved promises (§3, §7) | Proposed |
| Never quote prices; hand off | Don't invent business info; state the gap and give a route (§8, scenario 8) | Proposed |
| Always-visible human option | Gatekeeper aversion; keep human access (§1.4, §3 handoff) | Moderate |
| Say it's an AI; no human face | EU AI Act Art. 50 transparency applies from 2 Aug 2026; avoid fake human presentation (§3 legal table) | Strong (law, EU scope) |
| Handoff decided by topic rules, not Jev's "needs a human?" score | "Do not equate model self-confidence with calibrated correctness… validate any confidence score against labeled outcomes" (§3) | Proposed; matches our Phase 1 measurement |
| Answer first, collect contact details only on handoff | "Answer first; request contact information when needed for a requested follow-up" (§3 table) | Proposed, from NN/g evidence |
| No transcripts stored | Collect only task-necessary data; minimize logs (§3 privacy) | Proposed; GDPR/CCPA principles |

## What changes
| # | Finding | Evidence | Change to Cadence | Where |
|---|---|---|---|---|
| 1 | Visitors can't tell what a site bot is for | NN/g Mar 2026, Moderate | Launcher gets a **text label** ("Ask Cadre's AI"), not just an icon. The welcome says scope and AI identity in one sentence. **No auto-open**; the teaser stays quiet and dismissible. | UI (Phase 3) |
| 2 | Direct, scannable answers beat chatty text | NN/g Apr 2026, Moderate | **Answer contract:** direct answer → key condition → source link → next action. Short by default. | prompt |
| 3 | Recover once, then change path | §3, Proposed | If the visitor says the answer didn't help or repeats themselves, **offer a person on the second miss**, not a third rephrase. | prompt + router |
| 4 | Stop / Retry / Start over | §3, Proposed | Add **New chat** to the panel. Retrying must never submit a lead twice. | UI |
| 5 | Truthful loading states; streaming exposes unchecked text | §3 speed, GDS 2026 | Loading shows Deep Chat's typing indicator (we don't claim to "check" anything live). **Strip the `[HANDOFF]` tag server-side before it reaches the screen.** Measure time to a useful answer, median and slow tail. | answer.py, UI, events |
| 6 | Accessibility is interaction-level, not just contrast | WCAG 2.2, Strong (standard) | Focus moves into the panel on open and back to the launcher on close. Labeled input and buttons. New answers announced **once when complete** via `aria-live`, not token by token. Respect reduced motion. Keyboard-only use. | UI + Phase 7 checks |
| 7 | Output rendering is a security surface | OWASP 2026, §3 | Render model text as **plain text + safe links only**. Links allowed only to `cadre.ai`, `portal.gocadre.ai`, and `mailto:hello@gocadre.ai`. No raw HTML. | UI + answer.py |
| 8 | Brief privacy line, not a wall of disclaimers | §3 privacy | Under the input: "Please don't share passwords or payment details. How chat data is used." The link goes to a short page listing exactly what we store. (Removed 09-24 at Brian's request; /privacy.html remains. See plan.md §3a.) | UI + `public/privacy.html` |
| 9 | Handoff should carry context | §3 handoff packet | **Pre-fill** the form's question with the visitor's last question (editable). Store the topic and the page with the lead (production design; the demo form stores nothing: `db/schema.sql`). Promise **no response time** (we can't verify one). | UI + leads |
| 10 | Double-click must not duplicate | Stripe idempotency, Strong pattern; §8 scenario 22 | Lead submit uses a client-generated **idempotency key**; the server recognizes a repeat key and returns the same confirmation (`duplicate: true`). The button disables while sending. | main.py + UI |
| 11 | The site must work if chat fails | web.dev, §3 | If the API errors or times out, the panel shows a friendly message with **hello@gocadre.ai and /contact**. The page never breaks. | UI |
| 12 | Evaluate retrieval, answers, and journeys separately, with severity | Anthropic 2026, §8 | Eval cases get a **severity** (critical / major / moderate / minor) and pass/fail per check. **Zero critical failures is the launch gate.** A critical failure is never averaged away. High-risk cases run 3×. | evals (Phase 6) |
| 13 | LLM judges are biased; prefer deterministic checks | Zheng 2023, §8 | Check by code wherever possible: no dollar amounts, handoff as expected, links on the allow-list, no leaked tag; AI disclosure and invented names via per-case include/exclude checks. Use an LLM judge only for correctness triage, checked against Brian's labels. | evals |
| 14 | Measure abstention both ways | §8 metrics | Track **appropriate refusals** and **inappropriate refusals** separately (refusing an answerable question is a failure too). | evals |
| 15 | Unanswered questions should improve content | §7 content-gap queue | `chat_turns` outcome and topic let us list the top handoff and off-topic topics, feeding a "content gaps" review. | transcripts.py + what's next |
| 16 | Knowledge needs owner, date, review | §7 source record | `knowledge/cadre.md` header gets a read date (owner and review date: next). `verify_knowledge.py` doubles as a **freshness check** that can run on a schedule. | knowledge + what's next |
| 17 | Cost and abuse controls | OWASP 2026, §3 | Message length and 8-message history caps (main.py), per-IP rate limit (Vercel firewall 20/min + guards.py 12/min), `max_tokens` cap, per-stage deadlines (chat.py). Friendly "busy" message. | guards.py, main.py, chat.py |

## Test scenarios adopted from the report's 30 (§8)
Kept or adapted: 1–3, 6, 8–12, 17, 19, 20, 26–28, 30, plus Cadre-specific cases (pricing,
industry fit, pillars, portal login, security certification, "are you human?").
**Not applicable, with reason:** 4–5, 7, 14–16, 21–25, 29. Cadence has no accounts, orders,
bookings, inventory, or localization. The report itself says to use N/A rather than
inflate scores.
