# Deep research brief: what makes a website AI chatbot successful (2026)

Commissioned by Brian on 2026-09-23 to inform Cadence's UX, knowledge, architecture,
safety, handoff, and evaluation choices. When the findings come back, they get summarized
in `docs/research/findings.md` and any design changes get logged in `plan.md`.

## Prompt (verbatim)

Act as a senior research team combining expertise in conversational UX, AI engineering, knowledge management, accessibility, security, customer support, and conversion optimization.
Conduct deep, evidence-based research into what makes an AI chatbot on a website successful in 2026. Determine what works, what fails, why, and how to apply the findings. Cover the complete experience, from the visitor discovering the chatbot to the systems and processes that keep its answers accurate.
I want a practical research report that can inform the design, implementation, and ongoing operation of a real website chatbot. Avoid generic advice, vendor marketing, and unsupported predictions.

### 1. Establish scope and research standards
Begin by stating the research date and defining what "best" means for different use cases:

* Customer support and self-service.
* Sales, product discovery, and lead qualification.
* SaaS onboarding and in-product assistance.
* Ecommerce recommendations and order support.
* Professional services and appointment booking.
* Content-heavy, educational, and public-service websites.

Separate practices that apply broadly from those that depend on the business, audience, risk, traffic, budget, and available data. Distinguish traditional scripted chatbots, retrieval-based AI assistants, and agents that take actions.
If website details are available, tailor the research to them. If they are missing, proceed with explicit assumptions and explain how recommendations would change across common business types. Do not stall the research waiting for clarification.
Use current sources, prioritizing evidence published or updated in 2025–2026. Include older foundational research when it remains relevant, but explain why it still applies. Do not present announcements, demos, or capabilities planned for later as proven production outcomes.
Prioritize:

1. Independent empirical research and usability studies.
2. Documented deployments with meaningful outcome data.
3. Official technical documentation, standards, and regulatory guidance.
4. Credible practitioner accounts and postmortems.
5. Vendor claims, clearly labeled and critically evaluated.

For every consequential recommendation, provide supporting sources and indicate the strength of the evidence. Distinguish established findings, emerging practices, and your own reasoned recommendations.

### 2. Research the complete user experience
Investigate:

Discovery and entry points
* Whether the site should have a chatbot at all.
* When search, navigation, forms, or human support serve users better.
* Floating widgets versus embedded assistants, full-page chat, and contextual assistance.
* Placement, labels, welcome messages, starter prompts, and proactive triggers.
* When proactive chat helps versus interrupts.
* Mobile behavior, screen obstruction, and interaction with cookie banners or other overlays.

Conversation and interaction design
* How to communicate purpose, capabilities, limits, and AI identity.
* How users learn what they can ask without reading instructions.
* Free text, suggested prompts, buttons, forms, and hybrid interfaces.
* When to clarify, answer directly, show choices, or escalate.
* Response length, formatting, tone, pacing, and progressive disclosure.
* Streaming, loading states, latency expectations, cancellation, and retries.
* Handling ambiguous requests, misspellings, multiple intents, and follow-up questions.
* Conversation history, memory, session continuity, and starting over.
* Recovering from wrong answers, dead ends, and repeated misunderstandings.
* Showing sources, uncertainty, freshness, and the basis for recommendations.
* Avoiding false confidence, excessive friendliness, manipulative persuasion, and fake human presentation.

Accessibility and inclusion
* Keyboard navigation, focus management, screen readers, live announcements, contrast, and reduced motion.
* Applicable accessibility standards and how to test the actual chat interaction.
* Plain language, cognitive load, multilingual support, and localization.
* Users with limited technical confidence, poor connectivity, or older devices.
* Equivalent ways to complete tasks without using the chatbot.

For major UI recommendations, include concrete examples of effective and ineffective patterns, sample microcopy, and descriptions or sketches of recommended layouts.

### 3. Go deep on knowledge and answer quality
Explain how to build and maintain a trustworthy knowledge system:

* What belongs in the knowledge base and what should remain outside it.
* Source-of-truth selection and ownership.
* Website content, documentation, FAQs, policies, product catalogs, support articles, and internal material.
* Content auditing, deduplication, contradictions, missing information, and outdated pages.
* How to structure content so the chatbot can retrieve and interpret it reliably.
* Metadata, document structure, chunking, indexing, semantic search, keyword search, hybrid retrieval, and reranking.
* When retrieval-augmented generation, long-context approaches, structured queries, fine-tuning, or simpler methods are appropriate.
* How to handle frequently changing information such as pricing, inventory, availability, policies, and account status.
* Citations that actually support the answer.
* Permission-aware retrieval and preventing exposure of private information.
* Rules for conflicting sources and source precedence.
* How to distinguish an answerable question from one that requires clarification or human help.
* Abstention, uncertainty, and why model-reported confidence alone may be unreliable.
* Refresh schedules, event-driven updates, versioning, rollback, and content expiration.
* Using unanswered questions to improve the website and knowledge base.

Show a concrete example of a poorly prepared source article and an improved version. Explain the editorial and technical changes separately.

### 4. Examine architecture and operational reliability
Research the tradeoffs behind:

* Buying a hosted chatbot, building a custom system, and hybrid approaches.
* Model selection, routing, fallback models, and vendor dependence.
* Speed, cost, quality, context limits, and reliability.
* Retrieval, business rules, conversation state, and tool integrations.
* CRM, help desk, ecommerce, scheduling, search, and analytics connections.
* Read-only assistance versus actions such as booking, updating accounts, or issuing refunds.
* Authentication, authorization, confirmations, and approval boundaries.
* Duplicate actions, retries, idempotency, timeouts, and partial failures.
* Monitoring, incident response, rollback, and emergency shutdown.
* Website performance, third-party scripts, and failures when the chatbot service is unavailable.
* Traffic spikes, rate limits, abuse, and cost controls.

Explain which engineering decisions materially affect the visitor's experience. Avoid recommending complicated infrastructure without a demonstrated need.

### 5. Investigate privacy, security, and trust
Cover:

* Data collection, minimization, consent where required, retention, deletion, and vendor data use.
* Sensitive information entered into chat and safe handling of transcripts.
* Prompt injection, malicious retrieved content, data leakage, and unauthorized tool use.
* Cross-user and cross-account information exposure.
* Safe rendering of links, files, and generated content.
* Appropriate treatment of high-stakes questions.
* Relevant jurisdiction-specific legal and regulatory requirements in effect as of the research date.

Separate legal requirements from voluntary best practices. Cite authoritative sources for legal claims and state jurisdiction and effective date.
Explain how to communicate necessary safeguards clearly without burying users in disclaimers.

### 6. Study human handoff and service design
Determine best practices for:

* Recognizing when a human is needed.
* Offering human support without making visitors fight the bot.
* Passing conversation context so users do not have to repeat themselves.
* Setting accurate expectations about wait times and availability.
* After-hours support and asynchronous follow-up.
* Assigning responsibility between support, sales, engineering, and content teams.
* Preventing a chatbot from becoming a barrier to service.

Distinguish genuine resolution from apparent "deflection" caused by abandonment or difficulty reaching a person.

### 7. Analyze where organizations succeed and fail
Find at least eight well-documented real-world cases, ideally balanced between successes and failures and covering several industries. Do not force balance by inventing evidence or treating weak anecdotes as proven findings.
For each case, report:

* Organization and chatbot use case.
* Deployment date and source dates.
* What was implemented.
* What succeeded or failed.
* Reported outcomes and how they were measured.
* Whether the evidence is independent, company-reported, or vendor-reported.
* Other plausible explanations for the results.
* The likely mechanism behind the outcome.
* What another organization should adopt or avoid.
* Limits on generalizing the lesson.

Investigate failure modes such as hallucinated policies, stale knowledge, weak retrieval, intrusive UI, poor handoffs, false claims of task completion, privacy breaches, and optimizing for containment at the expense of customer outcomes.
Where possible, inspect live public examples. Clearly distinguish your direct observations from published claims. Do not submit personal information, contact companies, or perform transactions merely to test a chatbot.

### 8. Define measurement and evaluation
Recommend a practical evaluation system covering:

* Task completion and verified resolution.
* Answer correctness, completeness, relevance, and source support.
* Retrieval quality and knowledge coverage.
* Appropriate abstention and clarification.
* Handoff quality and user effort.
* Customer satisfaction and qualitative feedback.
* Conversion quality and downstream business outcomes.
* Latency, reliability, and cost per successfully resolved task.
* Accessibility and performance across languages and user groups.
* Security failures and unauthorized actions.

Explain misleading metrics and how teams game them, intentionally or unintentionally.
Provide:

* A prelaunch evaluation plan.
* A representative test set with at least 25 example scenarios.
* A scoring rubric with definitions and severity levels.
* A method for human review and automated evaluation.
* Limits of using an LLM as a judge.
* Production monitoring and regression testing.
* A credible A/B testing approach that compares chat against existing alternatives.
* How to choose launch thresholds based on risk, rather than inventing universal benchmarks.

### 9. Identify what actually changed in 2026
Create a section distinguishing:

* Durable principles that remain unchanged.
* Practices that have materially changed by the research date.
* Emerging approaches with promising but incomplete evidence.
* Hype or claims that lack adequate support.

Investigate developments such as agentic actions, multimodal interfaces, voice, personalization, interoperability, and more advanced retrieval. Include them only where they matter for website use cases.
For each claimed change, explain the evidence and practical implication. Do not simply produce a list of trends.

### 10. Deliver a decision-ready report
Organize the final report as follows:

1. Executive findings: The most consequential conclusions, with evidence strength.
2. Should this site have a chatbot? A decision framework, including when the answer is no.
3. Detailed best practices: UX, knowledge, architecture, safety, handoff, and operations.
4. Success and failure case studies.
5. 2026 developments: Proven changes versus speculation.
6. Recommended experience: A visitor journey from first interaction through resolution or handoff, including example conversations.
7. Knowledge blueprint: Source structure, ownership, ingestion, retrieval, and maintenance.
8. Evaluation and measurement plan.
9. Prioritized implementation roadmap: First 30, 60, and 90 days, with dependencies and responsible roles.
10. Launch checklist and ongoing operating cadence.
11. Open questions and evidence gaps.
12. Annotated source list.

Include a prioritized recommendations table with:
| Recommendation | Problem addressed | Applicable use cases | Supporting evidence | Evidence strength | Impact | Effort | Risks or tradeoffs | How to validate |
Offer three implementation levels: a lean small-business setup, a growing-company setup, and a complex or regulated enterprise setup. Explain the minimum viable approach and what justifies moving to the next level.
Use plain language, define technical terms, and provide enough detail for a designer, content owner, engineering lead, and business owner to act on the report.
Quality bar: Cite sources beside the claims they support, include publication dates where available, verify that sources support the stated conclusions, and report uncertainty honestly. Prefer a smaller number of defensible findings over a large collection of generic recommendations. The report should help someone build and operate a chatbot that earns its place on the website.
