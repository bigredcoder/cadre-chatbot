# Failures with examples: bench

Each entry: the question, the check that failed, and the bot's actual reply.

## google/gemini-2.5-flash: 1 failed of 52 runs

**MAJOR · portal-where-is-it** (run 1)
- Question: "Where do I find the client portal?"
- Caught: handoff True != False
- Routed as: portal via jev; handoff shown: True
- Actual reply: "Cadre gives you a centralized portal to track tools, agents, training, and results. You can access it at portal.gocadre.ai. More: cadre.ai.  If you need help logging in or with your account, I can connect you with a strategist."

## google/gemini-2.5-flash: 8 failed of 52 runs

**MAJOR · gap-maturity-index-free** (run 3)
- Question: "Is the AI Maturity Index free?"
- Caught: handoff False != True
- Routed as: maturity_index via fallback; handoff shown: False
- Actual reply: "I don't have information on whether the AI Maturity Index is free. You can get your AI Maturity Index score at portal.gocadre.ai/ai-maturity-index. You can also talk to an AI strategist about it."

**MAJOR · portal-where-is-it** (run 1)
- Question: "Where do I find the client portal?"
- Caught: handoff True != False
- Routed as: portal via fallback; handoff shown: True
- Actual reply: "You can find the client portal at portal.gocadre.ai. More: cadre.ai. If you need help logging in, I can connect you with a strategist."

**MODERATE · gap-client-names** (run 1)
- Question: "Which companies have you worked with? Name a few clients."
- Caught: topic company not in ['results']
- Routed as: company via fallback; handoff shown: False
- Actual reply: "Cadre's website doesn't name specific clients, but it does share results from anonymized case studies. For example, one client processed over 1,500 emails and 650 leads monthly using an AI Agent across 5 branches. Another saved over 8,000 hours annually. More: cadre.ai/case-studies.  Would you like to discuss how Cadre's services might apply to your company?"

**MODERATE · gap-client-names** (run 2)
- Question: "Which companies have you worked with? Name a few clients."
- Caught: topic company not in ['results']
- Routed as: company via fallback; handoff shown: False
- Actual reply: "Cadre's website doesn't name specific clients, but it does share results from anonymized case studies. For example, one client processed over 1,500 emails and 650 leads monthly with an AI Agent across 5 branches. Another saved over 8,000 hours annually. More: cadre.ai/case-studies.  Would you like to discuss how Cadre could help your company?"

**MODERATE · gap-client-names** (run 3)
- Question: "Which companies have you worked with? Name a few clients."
- Caught: topic company not in ['results']
- Routed as: company via fallback; handoff shown: False
- Actual reply: "Cadre's case studies are anonymized on the website. For example, one client processes 1,500+ emails and 650+ leads monthly through an AI Agent across 5 branches. Another processes 200-300 supplier confirmations automatically each day. More: cadre.ai/case-studies.  Would you like to talk to an AI strategist about how Cadre could help your company?"

**MODERATE · gap-soc2-certification** (run 1)
- Question: "Are you SOC 2 certified?"
- Caught: topic company not in ['llm_security']
- Routed as: company via fallback; handoff shown: True
- Actual reply: "I don't have information about specific security certifications like SOC 2. If you'd like to discuss Cadre's security practices, I can connect you with a strategist. You can also reach Cadre directly at hello@gocadre.ai or cadre.ai/contact."

**MODERATE · gap-soc2-certification** (run 2)
- Question: "Are you SOC 2 certified?"
- Caught: topic company not in ['llm_security']
- Routed as: company via fallback; handoff shown: True
- Actual reply: "I don't have information about specific security certifications like SOC 2. If you'd like to discuss Cadre's security practices, I can connect you with a strategist. You can also reach Cadre directly at hello@gocadre.ai or cadre.ai/contact."

**MODERATE · gap-soc2-certification** (run 3)
- Question: "Are you SOC 2 certified?"
- Caught: topic company not in ['llm_security']
- Routed as: company via fallback; handoff shown: True
- Actual reply: "I don't have information about specific security certifications like SOC 2. If you'd like to discuss Cadre's security practices, I can connect you with a strategist. You can also reach Cadre directly at hello@gocadre.ai or cadre.ai/contact."
