"""Run the eval set against several answer models in parallel and write a comparison table.

Usage:
  .venv/bin/python -m evals.compare                 # all CANDIDATES, Jev routing
  .venv/bin/python -m evals.compare --no-jev        # same, model-only routing (benchmark)
  .venv/bin/python -m evals.compare --routes evals/results/routes-jev.json   # same recorded routes for every model
Writes evals/results/<label>-<model>.json and evals/results/<label>.md.
"""
import argparse
import json
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RESULTS = ROOT / "evals" / "results"

# Fast, low-cost models from several providers (all verified on OpenRouter 2026-09-23).
CANDIDATES = [
    "google/gemini-2.5-flash-lite", "google/gemini-2.5-flash",
    "openai/gpt-4.1-nano", "openai/gpt-4.1-mini", "openai/gpt-4o-mini",
    "openai/gpt-oss-120b",
    # Excluded 09-23: openai/gpt-5-nano and gpt-5-mini returned blank replies on 48-49 of 52
    # runs (reasoning used the whole 500-token budget). They'd need reasoning settings; see plan.md.
    "anthropic/claude-haiku-4.5",
    "mistralai/mistral-small-3.2-24b-instruct", "meta-llama/llama-4-maverick",
    "qwen/qwen3-235b-a22b-2507", "deepseek/deepseek-chat-v3.1",
]


def run(model: str, label: str, no_jev: bool, repeat: int, routes: str | None) -> dict:
    out = RESULTS / f"{label}-{model.replace('/', '_')}.json"
    cmd = [sys.executable, "-m", "evals.run", "--model", model, "--repeat", str(repeat),
           "--out", str(out)] + (["--no-jev"] if no_jev else [])
    if routes:
        cmd += ["--routes", routes]
    subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=1800, check=False)  # exit 1 = critical fails; still read results
    if not out.exists():
        return {"model": model, "error": "no results"}
    return json.loads(out.read_text())["summary"]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-jev", action="store_true")
    ap.add_argument("--repeat", type=int, default=3)
    ap.add_argument("--models", help="comma-separated override of CANDIDATES")
    ap.add_argument("--routes", help="fixed routing file from `evals.run --record-routes`")
    ap.add_argument("--workers", type=int, default=2)
    ap.add_argument("--table-only", action="store_true",
                    help="rebuild the table from saved (e.g. rescored) results; no new calls")
    args = ap.parse_args()
    label = "compare-nojev" if args.no_jev else ("compare-fixed" if args.routes else "compare-jev")
    models = args.models.split(",") if args.models else CANDIDATES
    RESULTS.mkdir(parents=True, exist_ok=True)
    # 2 at a time: at 7 in parallel, Jev rejected most calls under load and the fallback
    # routed them, which contaminated the first comparison (09-23).
    if args.table_only:
        rows = [json.loads(Path(f).read_text())["summary"]
                for f in sorted(RESULTS.glob(f"{label}-*.json"))]
    else:
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            rows = list(pool.map(lambda m: run(m, label, args.no_jev, args.repeat, args.routes),
                                 models))

    # Rank: zero critical failures first, then pass rate, then cost (research §8 gate)
    def key(r):
        if "error" in r:
            return (1, 99, 0, 9)
        return (0, r["critical_failures"], -r["passed"] / r["runs"], r["avg_cost_per_turn_usd"])
    rows.sort(key=key)
    note = " Rescored with the corrected checker (09-23)." if any(r.get("rescored") for r in rows) else ""
    mode = ("model-only routing" if args.no_jev else
            "fixed Jev routes, same for every model" if args.routes else "live Jev routing")
    lines = [f"# Model comparison ({mode})",
             "", f"{rows[0].get('cases', '?') if rows else '?'} cases; critical cases x{args.repeat}. Ranked: critical failures, pass rate, cost.{note}",
             "Real example of every failure: see the matching *-failures.md file.", "",
             "| Model | Passed | Critical fails | Major fails | Topic acc. | Handoff acc. | Median ms | p90 ms | Route ms | $/turn |",
             "|---|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        if "error" in r:
            lines.append(f"| {r['model']} | error | | | | | | | | |")
            continue
        lines.append(f"| {r['model']} | {r['passed']}/{r['runs']} | {r['critical_failures']} | "
                     f"{r['major_failures']} | {r['topic_accuracy']:.0%} | {r['handoff_accuracy']:.0%} | "
                     f"{r['median_ms']} | {r['p90_ms']} | {r['median_route_ms']} | "
                     f"{r['avg_cost_per_turn_usd']:.6f} |")
    (RESULTS / f"{label}.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))
    from evals.report import main as write_failures  # every error gets a real example
    print(f"\nFailure examples: {write_failures(label)}")


if __name__ == "__main__":
    main()
