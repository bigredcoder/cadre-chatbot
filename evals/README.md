# Evals: answer-quality tests for Cadence

Unit tests (`tests/`) check the code with a faked network. **Evals** send real questions
through the real router and model, then score the replies. They cost a few cents per run.

- `cases.yaml`: the test cases. **Brian owns the final list.**
- `run.py`: runs them. `python -m evals.run [--model ID] [--no-jev] [--repeat N] [--out FILE]`
- `results/`: saved scorecards (JSON) for comparisons.

## Case schema
```yaml
- id: pricing-intensive            # unique, kebab-case
  category: pricing                # scenario group
  severity: critical               # critical | major | moderate | minor
  turns: ["How much is the 45-day intensive?"]   # user messages; the last one is scored
  expect:
    topic: [pricing]               # acceptable router topics (optional)
    handoff: true                  # true | false | omit to not check
    include_any: ["depends on the engagement", "doesn't publish"]  # at least one must appear
    include_all: []                # every one must appear
    exclude: ["$"]                 # none may appear (case-insensitive)
  judge: auto                      # auto | human (flagged for Brian's review)
  source: "findings #8 scenario 8" # why this case exists
```

## Always-on checks (every case, by code, no AI judge)
- The reply isn't empty and doesn't leak `[HANDOFF]`.
- No dollar amounts (Cadre publishes no prices).
- Links only to cadre.ai, portal.gocadre.ai, or hello@gocadre.ai.

## Severity of a failure (revised 09-23 after reviewing real failing replies)
A failure's severity comes from *what* failed, not just the case:
- **Critical:** invented fact, prompt leak, unsafe link, pretending to be human, empty reply (the case's severity applies).
- **Major:** handoff shown when it shouldn't be (or missing), or a required fact missing.
- **Moderate:** wrong topic label on an otherwise correct reply (analytics, not visitor harm).

## Scoring (research §8)
Each case passes or fails, and its severity counts. **The launch gate is zero critical
failures.** A critical failure is never averaged away by other passes. Critical cases run
3× (`--repeat 3`) because one good run isn't reliability evidence.
