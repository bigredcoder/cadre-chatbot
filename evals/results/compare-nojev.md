# Model comparison (model-only routing)

26 cases; critical cases x3. Ranked: critical failures, pass rate, cost. Rescored with the corrected checker (09-23).
Real example of every failure: see the matching *-failures.md file.

| Model | Passed | Critical fails | Major fails | Topic acc. | Handoff acc. | Median ms | p90 ms | Route ms | $/turn |
|---|---|---|---|---|---|---|---|---|---|
| openai/gpt-4.1-mini | 48/52 | 0 | 1 | 92% | 97% | 2453 | 3071 | 901 | 0.000710 |
| openai/gpt-4o-mini | 43/52 | 0 | 2 | 82% | 94% | 2473 | 3457 | 1079 | 0.000397 |
| anthropic/claude-haiku-4.5 | 43/52 | 0 | 3 | 85% | 92% | 3241 | 4273 | 963 | 0.004942 |
| mistralai/mistral-small-3.2-24b-instruct | 39/52 | 0 | 3 | 75% | 94% | 3361 | 4116 | 1012 | 0.000393 |
| deepseek/deepseek-chat-v3.1 | 38/52 | 0 | 6 | 78% | 94% | 5928 | 10241 | 1945 | 0.000783 |
| google/gemini-2.5-flash-lite | 37/52 | 0 | 5 | 68% | 94% | 1360 | 2099 | 558 | 0.000340 |
| openai/gpt-oss-120b | 16/52 | 0 | 2 | 12% | 97% | 6840 | 17900 | 2132 | 0.000238 |
| qwen/qwen3-235b-a22b-2507 | 44/52 | 1 | 3 | 95% | 86% | 4000 | 5036 | 1258 | 0.000222 |
| google/gemini-2.5-flash | 44/52 | 1 | 1 | 85% | 97% | 1645 | 1952 | 658 | 0.001038 |
| openai/gpt-4.1-nano | 35/52 | 2 | 4 | 70% | 83% | 1974 | 2546 | 813 | 0.000206 |
| meta-llama/llama-4-maverick | 41/52 | 3 | 1 | 82% | 97% | 6432 | 10814 | 1642 | 0.000831 |
