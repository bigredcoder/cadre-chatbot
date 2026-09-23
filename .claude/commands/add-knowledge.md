---
description: Add facts from a cadre.ai page to the knowledge file, each with an exact quote
argument-hint: "<cadre.ai URL>"
---
Add knowledge from $ARGUMENTS to `knowledge/cadre.md`.

1. Only cadre.ai pages. Use the `site-researcher` subagent to extract candidate facts, each
   with a short exact quote and the URL.
2. Show Brian the proposed lines and wait for approval. Don't edit the file before that.
3. After approval, add the lines in the right section (format: fact — "exact quote" — URL).
4. Run `.venv/bin/python tools/verify_knowledge.py`. Every quote must match the live page.
5. Add or update an eval case in `evals/cases.yaml` that exercises the new fact, run it with
   `/eval --only <id>`, and log the change in build-process.md.
