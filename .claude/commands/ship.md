---
description: Pre-commit gate - lint, tests, quote check, review, then propose a commit
---
Get the current changes ready to commit. Stop at the first failure and report it.

1. `.venv/bin/ruff check .`, `.venv/bin/python -m mypy app`, and `.venv/bin/python -m pytest -q`:
   all must pass.
2. If `knowledge/` changed: `.venv/bin/python tools/verify_knowledge.py` must pass.
3. If `app/`, `prompts/`, or `knowledge/` changed: run `/eval --only` on the affected cases.
4. Ask the `code-reviewer` subagent to review the diff (`git diff --cached` or `git diff`).
   Fix critical/major findings, or explain why a finding is wrong.
5. Scan the diff for secrets (`sk-or-v1-`, JWTs). Never commit `.env*`.
6. Update `docs/build-process.md` (did / found / decided / checked; name the commit by its
   subject, never make a hash-only commit). Append at the end; read only its last ~40 lines
   for the format, never the whole file.
7. Show Brian a plain-English summary and the proposed commit message. **Commit only after
   he approves.**
