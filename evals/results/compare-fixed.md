# Model comparison (fixed Jev routes, same for every model)

26 cases; critical cases x3. Ranked: critical failures, pass rate, cost. Rescored with the corrected checker (09-23).
Real example of every failure: see the matching *-failures.md file.

| Model | Passed | Critical fails | Major fails | Topic acc. | Handoff acc. | Median ms | p90 ms | Route ms | $/turn |
|---|---|---|---|---|---|---|---|---|---|
| openai/gpt-4.1-mini | 52/52 | 0 | 0 | 100% | 100% | 1319 | 1619 | 383 | 0.000548 |
| google/gemini-2.5-flash | 52/52 | 0 | 0 | 100% | 100% | 952 | 1323 | 383 | 0.000914 |
| anthropic/claude-haiku-4.5 | 52/52 | 0 | 0 | 100% | 100% | 2037 | 2855 | 383 | 0.004373 |
| google/gemini-2.5-flash-lite | 51/52 | 0 | 1 | 100% | 97% | 808 | 1039 | 383 | 0.000204 |
| openai/gpt-oss-120b | 51/52 | 0 | 0 | 100% | 100% | 4992 | 10604 | 383 | 0.000237 |
| deepseek/deepseek-chat-v3.1 | 51/52 | 0 | 1 | 100% | 97% | 3944 | 9081 | 383 | 0.000615 |
| mistralai/mistral-small-3.2-24b-instruct | 49/52 | 0 | 3 | 100% | 97% | 2294 | 4353 | 383 | 0.000353 |
| openai/gpt-4.1-nano | 48/52 | 0 | 4 | 100% | 94% | 1127 | 1427 | 383 | 0.000169 |
| openai/gpt-4o-mini | 48/52 | 0 | 3 | 100% | 89% | 1475 | 2356 | 383 | 0.000376 |
| qwen/qwen3-235b-a22b-2507 | 46/52 | 0 | 3 | 100% | 86% | 2131 | 2959 | 383 | 0.000187 |
| meta-llama/llama-4-maverick | 48/52 | 3 | 1 | 100% | 97% | 1124 | 6297 | 383 | 0.000772 |
