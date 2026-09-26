# Full grid: every model, with and without Jev

Same 26 cases, critical ×3 (52 runs). *With Jev* = identical recorded Jev routes. *Without Jev* = the model routes and answers. Rescored with the corrected checker.
Cost includes routing. Speed: with-Jev runs replay routes, so add ~0.4 s for live Jev routing; without-Jev speed includes live model routing.
Read with care (added 09-25): every model replays the same routes, so *Topic w/* is the same for all by construction (that recording scored 100%). On answer checks alone (ignoring the label), Jev was better for 7 models, tied for 3, worse for 1 (gpt-4o-mini). *$/1k w/* has no Jev cost in it: the 28 recorded Jev routes show $0 (on free credits). gpt-oss-120b's 12% *Topic w/o*: all 52 of its routes came back `services`, which is also the fallback's default for a missing or unknown topic (`app/router.py:112`).

| Model | Correct w/ Jev | Correct w/o | Critical w/ | Critical w/o | Topic w/ | Topic w/o | Speed w/ (+0.4 s) | Speed w/o | $/1k w/ | $/1k w/o |
|---|---|---|---|---|---|---|---|---|---|---|
| google/gemini-2.5-flash | 52/52 | 44/52 | 0 | 1 | 100% | 85% | 1.0s | 1.6s | $0.91 | $1.04 |
| openai/gpt-4.1-mini | 52/52 | 48/52 | 0 | 0 | 100% | 92% | 1.3s | 2.5s | $0.55 | $0.71 |
| anthropic/claude-haiku-4.5 | 52/52 | 43/52 | 0 | 0 | 100% | 85% | 2.0s | 3.2s | $4.37 | $4.94 |
| openai/gpt-oss-120b | 51/52 | 16/52 | 0 | 0 | 100% | 12% | 5.0s | 6.8s | $0.24 | $0.24 |
| deepseek/deepseek-chat-v3.1 | 51/52 | 38/52 | 0 | 0 | 100% | 78% | 3.9s | 5.9s | $0.61 | $0.78 |
| google/gemini-2.5-flash-lite | 51/52 | 37/52 | 0 | 0 | 100% | 68% | 0.8s | 1.4s | $0.20 | $0.34 |
| mistralai/mistral-small-3.2-24b-instruct | 49/52 | 39/52 | 0 | 0 | 100% | 75% | 2.3s | 3.4s | $0.35 | $0.39 |
| openai/gpt-4o-mini | 48/52 | 43/52 | 0 | 0 | 100% | 82% | 1.5s | 2.5s | $0.38 | $0.40 |
| qwen/qwen3-235b-a22b-2507 | 46/52 | 44/52 | 0 | 1 | 100% | 95% | 2.1s | 4.0s | $0.19 | $0.22 |
| openai/gpt-4.1-nano | 48/52 | 35/52 | 0 | 2 | 100% | 70% | 1.1s | 2.0s | $0.17 | $0.21 |
| meta-llama/llama-4-maverick | 48/52 | 41/52 | 3 | 3 | 100% | 82% | 1.1s | 6.4s | $0.77 | $0.83 |
