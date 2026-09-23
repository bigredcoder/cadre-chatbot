---
description: Run the answer-quality evals and summarize failures with real examples
argument-hint: "[--model ID] [--no-jev] [--only id1,id2]"
---
Run the Cadence answer-quality evals and report back.

1. Run `.venv/bin/python -m evals.run --repeat 3 --out evals/results/latest.json $ARGUMENTS`.
2. For every failure, show: the question, the check that failed, and the bot's actual reply
   (read it from the results file). Never report a failure without its real reply (CLAUDE.md).
3. Classify each failure: **bot bug** (the reply is wrong) or **test bug** (the reply is fine and
   the check is too strict). Don't change a check to make a real bot bug pass.
4. Summarize: passed/runs, critical and major counts, median latency, cost per turn.
   The launch gate is zero critical failures.
