"""Run the answer-quality evals against the REAL app (real router, real model).

Usage:
  .venv/bin/python -m evals.run                         # current config
  .venv/bin/python -m evals.run --model openai/gpt-4.1-nano --out evals/results/x.json
  .venv/bin/python -m evals.run --no-jev                # benchmark: model-only routing
  .venv/bin/python -m evals.run --repeat 3              # critical cases run 3x
  .venv/bin/python -m evals.run --only portal-where-is-it,gap-soc2-certification
  .venv/bin/python -m evals.run --record-routes r.json  # save each case's routing
  .venv/bin/python -m evals.run --routes r.json         # replay saved routing

Checks are deterministic string checks (research §8: prefer code over an AI judge).
Cases marked `judge: human` are scored by code too, but flagged for Brian's review.
Costs a few cents per run on the dev OpenRouter key. Nothing is saved to the database.
"""
import argparse
import json
import os
import re
import statistics
import sys
import time
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
ALLOWED_HOSTS = {"cadre.ai", "www.cadre.ai", "portal.gocadre.ai"}
URLISH = re.compile(r"\b((?:https?://)?(?:[\w-]+\.)+(?:ai|com|io|org|net|co)\b[^\s)\]]*)")


def parse_sse(text: str) -> dict:
    out = {"reply": "", "route": {}, "done": {}, "error": None}
    for block in text.split("\n\n"):
        ev = re.search(r"^event: (.*)$", block, re.MULTILINE)
        data = re.search(r"^data: (.*)$", block, re.MULTILINE)
        if not ev or not data:
            continue
        payload = json.loads(data.group(1))
        kind = ev.group(1)
        if kind == "token":
            out["reply"] += payload["text"]
        elif kind in ("route", "done"):
            out[kind] = payload
        elif kind == "error":
            out["error"] = payload.get("message")
    return out


def normalize(text: str) -> str:
    """Compare meaning, not typography: curly quotes, non-breaking hyphens, and markdown
    bold were failing correct answers (09-23 review of real failures)."""
    for a, b in (("\u2019", "'"), ("\u2018", "'"), ("\u201c", '"'), ("\u201d", '"'),
                 ("\u2011", "-"), ("\u2010", "-"), ("\u00a0", " "), ("**", "")):
        text = text.replace(a, b)
    return text


def always_on_checks(reply: str, error: str | None) -> list[str]:
    reply = normalize(reply)
    problems = []
    if error:
        problems.append(f"error event: {error[:60]}")
    if not reply.strip() and not error:
        problems.append("empty reply")
    if "[HANDOFF" in reply:
        problems.append("handoff tag leaked")
    if re.search(r"\$\s?\d", reply):
        problems.append("dollar amount in reply")
    for m in URLISH.findall(reply):
        host = re.sub(r"^https?://", "", m).split("/")[0].lower().rstrip(".,;:")
        if "@" in m or host in ALLOWED_HOSTS or host == "gocadre.ai":
            continue
        problems.append(f"link outside allow-list: {m}")
    return problems


def case_checks(case: dict, result: dict) -> list[str]:
    exp, reply = case.get("expect", {}), normalize(result["reply"]).lower()
    problems = []
    if "topic" in exp and result["route"].get("topic") not in exp["topic"]:
        problems.append(f"topic {result['route'].get('topic')} not in {exp['topic']}")
    if "handoff" in exp and bool(result["done"].get("handoff")) != exp["handoff"]:
        problems.append(f"handoff {bool(result['done'].get('handoff'))} != {exp['handoff']}")
    if exp.get("include_any") and not any(s.lower() in reply for s in exp["include_any"]):
        problems.append(f"missing any of {exp['include_any']}")
    for s in exp.get("include_all", []):
        if s.lower() not in reply:
            problems.append(f"missing {s!r}")
    for s in exp.get("exclude", []):
        if s.lower() in reply:
            problems.append(f"contains forbidden {s!r}")
    return problems


ROUTE_KEY = {"value": ""}  # which (case, turn) is running, for fixed-route mode


def severity_of(problem: str, case_severity: str) -> str:
    """Severity comes from WHAT failed, capped by how serious the case is (09-23 review:
    a wrong topic label on a safe answer is not a critical failure)."""
    if problem.startswith("topic"):
        return "moderate"                       # label for analytics; the answer can still be right
    if problem.startswith(("handoff", "missing")):
        return "major" if case_severity == "critical" else case_severity
    return case_severity                         # invented facts, leaks, unsafe links, errors


def worst(problems: list[str], case_severity: str) -> str | None:
    order = ["critical", "major", "moderate", "minor"]
    found = [severity_of(p, case_severity) for p in problems]
    return min(found, key=order.index) if found else None


def run_case(client, case: dict) -> dict:
    history, result, wall = [], None, 0
    for i, turn in enumerate(case["turns"]):
        ROUTE_KEY["value"] = f"{case['id']}#{i}"
        history.append({"role": "user", "content": turn})
        started = time.monotonic()
        resp = client.post("/api/chat", json={"session_id": f"eval-{case['id']}"[:60].ljust(8, "x"),
                                              "messages": history})
        wall = int((time.monotonic() - started) * 1000)
        result = parse_sse(resp.text)
        if i < len(case["turns"]) - 1:
            history.append({"role": "assistant", "content": result["reply"] or "(no reply)"})
    problems = always_on_checks(result["reply"], result["error"]) + case_checks(case, result)
    return {"id": case["id"], "severity": case["severity"], "category": case["category"],
            "passed": not problems, "failure_severity": worst(problems, case["severity"]), "problems": problems, "wall_ms": wall,
            "route": result["route"], "done": result["done"], "reply": result["reply"],
            "judge": case.get("judge", "auto")}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model")
    ap.add_argument("--no-jev", action="store_true")
    ap.add_argument("--repeat", type=int, default=1, help="runs per critical case")
    ap.add_argument("--only", help="comma-separated case ids")
    ap.add_argument("--out")
    ap.add_argument("--record-routes", help="save each case's routing decision to this file")
    ap.add_argument("--routes", help="replay routing from this file (holds routing constant "
                                     "so a model comparison only varies the answer model)")
    args = ap.parse_args()

    # Configure BEFORE importing the app (config reads the environment at import time)
    os.environ["SAVE_TURNS"] = "0"
    os.environ["RATE_LIMIT_PER_MINUTE"] = os.environ["RATE_LIMIT_PER_DAY"] = "100000"
    if args.model:
        os.environ["ANSWER_MODEL"] = args.model
    if args.no_jev:
        os.environ["ROUTER_MODE"] = "model_only"
    from fastapi.testclient import TestClient

    from app import chat as app_chat
    from app import config
    from app.main import app
    from app.router import Route

    # Patch `route` where the turn looks it up: app/chat.py (main.py stopped using it in fc12e50)
    recorded: dict = {}
    if args.routes:
        fixed = json.loads(Path(args.routes).read_text())

        async def replay(history, token=None):
            return Route(**fixed[ROUTE_KEY["value"]])
        app_chat.route = replay
    elif args.record_routes:
        real_route = app_chat.route

        async def record(history, token=None):
            decision = await real_route(history, token)
            recorded[ROUTE_KEY["value"]] = decision.as_dict()
            return decision
        app_chat.route = record

    cases = yaml.safe_load((ROOT / "evals" / "cases.yaml").read_text())
    if args.only:
        keep = set(args.only.split(","))
        cases = [c for c in cases if c["id"] in keep]
    client = TestClient(app)

    results = []
    for case in cases:
        runs = args.repeat if case["severity"] == "critical" else 1
        for n in range(runs):
            r = run_case(client, case)
            r["run"] = n + 1
            results.append(r)
            mark = "PASS" if r["passed"] else "FAIL"
            print(f"{mark} [{case['severity'][:4]}] {case['id']}"
                  + ("" if r["passed"] else f"  ← {'; '.join(r['problems'])}"))

    walls = [r["wall_ms"] for r in results]
    routes = [r["route"].get("route_ms", 0) for r in results if r["route"]]
    costs = [float(r["done"].get("cost_usd") or 0) + float(r["route"].get("route_cost_usd") or 0)
             for r in results]
    topic_cases = [r for r in results if "topic" in next(c for c in cases if c["id"] == r["id"]).get("expect", {})]
    hand_cases = [r for r in results if "handoff" in next(c for c in cases if c["id"] == r["id"]).get("expect", {})]
    summary = {
        "model": config.ANSWER_MODEL,
        "router_mode": config.ROUTER_MODE,
        "cases": len(cases), "runs": len(results),
        "passed": sum(r["passed"] for r in results),
        "critical_failures": sum(r["failure_severity"] == "critical" for r in results),
        "major_failures": sum(r["failure_severity"] == "major" for r in results),
        "topic_accuracy": round(sum(not any(p.startswith("topic") for p in r["problems"]) for r in topic_cases) / max(len(topic_cases), 1), 3),
        "handoff_accuracy": round(sum(not any(p.startswith("handoff") for p in r["problems"]) for r in hand_cases) / max(len(hand_cases), 1), 3),
        "median_ms": int(statistics.median(walls)) if walls else None,
        "p90_ms": int(sorted(walls)[int(len(walls) * 0.9) - 1]) if walls else None,
        "median_route_ms": int(statistics.median(routes)) if routes else None,
        "avg_cost_per_turn_usd": round(sum(costs) / max(len(results), 1), 6),
        "total_cost_usd": round(sum(costs), 5),
    }
    if args.routes:
        summary["router_mode"] = f"fixed routes from {Path(args.routes).name}"
    if args.record_routes:
        Path(args.record_routes).write_text(json.dumps(recorded, indent=2))
    print("\n" + json.dumps(summary, indent=2))
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(json.dumps({"summary": summary, "results": results}, indent=2))
    return 1 if summary["critical_failures"] else 0


if __name__ == "__main__":
    sys.exit(main())
