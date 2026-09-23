# Model comparison (Jev routing)

26 cases; critical cases x3. Ranked: critical failures, pass rate, cost.

| Model | Passed | Critical fails | Major fails | Topic acc. | Handoff acc. | Median ms | p90 ms | Route ms | $/turn |
|---|---|---|---|---|---|---|---|---|---|
| anthropic/claude-haiku-4.5 | 49/52 | 1 | 2 | 98% | 100% | 2545 | 3440 | 389 | 0.004412 |
| google/gemini-2.5-flash | 49/52 | 2 | 1 | 95% | 97% | 1817 | 4444 | 848 | 0.000964 |
| qwen/qwen3-235b-a22b-2507 | 47/52 | 2 | 2 | 100% | 92% | 3038 | 5028 | 351 | 0.000245 |
| openai/gpt-4.1-mini | 48/52 | 3 | 1 | 100% | 97% | 2284 | 3859 | 846 | 0.000596 |
| deepseek/deepseek-chat-v3.1 | 48/52 | 3 | 1 | 100% | 97% | 4545 | 8116 | 334 | 0.000713 |
| google/gemini-2.5-flash-lite | 47/52 | 4 | 1 | 92% | 97% | 1612 | 6152 | 704 | 0.000343 |
| meta-llama/llama-4-maverick | 44/52 | 6 | 2 | 100% | 94% | 6142 | 12111 | 354 | 0.000770 |
| openai/gpt-4o-mini | 42/52 | 7 | 3 | 90% | 86% | 2240 | 3033 | 525 | 0.000377 |
| mistralai/mistral-small-3.2-24b-instruct | 43/52 | 8 | 1 | 95% | 100% | 3152 | 5221 | 331 | 0.000346 |
| openai/gpt-4.1-nano | 38/52 | 8 | 5 | 80% | 86% | 2139 | 3158 | 1060 | 0.000194 |
| openai/gpt-oss-120b | 36/52 | 12 | 2 | 92% | 100% | 6037 | 13922 | 390 | 0.000222 |
