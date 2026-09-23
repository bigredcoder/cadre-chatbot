"""Re-apply the current checks to SAVED replies: no new model calls, no cost.

Use after fixing a check (a test bug) so earlier comparisons are scored consistently.
Usage: .venv/bin/python -m evals.rescore compare-fixed
"""
import glob
import json
import statistics
import sys
from pathlib import Path

import yaml

from evals.run import always_on_checks, case_checks, worst

ROOT = Path(__file__).resolve().parent.parent


def rescore_file(path: str, cases: dict) -> dict:
    data = json.loads(Path(path).read_text())
    for r in data["results"]:
        result = {"reply": r["reply"], "route": r["route"], "done": r["done"], "error": None}
        if not r["reply"] and any(p.startswith("error event") for p in r["problems"]):
            result["error"] = "error event"
        r["problems"] = always_on_checks(result["reply"], result["error"]) + \
            case_checks(cases[r["id"]], result)
        r["passed"] = not r["problems"]
        r["failure_severity"] = worst(r["problems"], r["severity"])
    rs, s = data["results"], data["summary"]
    s["passed"] = sum(r["passed"] for r in rs)
    s["critical_failures"] = sum(r["failure_severity"] == "critical" for r in rs)
    s["major_failures"] = sum(r["failure_severity"] == "major" for r in rs)
    topic = [r for r in rs if "topic" in cases[r["id"]].get("expect", {})]
    s["topic_accuracy"] = round(sum(not any(p.startswith("topic") for p in r["problems"])
                                    for r in topic) / max(len(topic), 1), 3)
    hand = [r for r in rs if "handoff" in cases[r["id"]].get("expect", {})]
    s["handoff_accuracy"] = round(sum(not any(p.startswith("handoff") for p in r["problems"])
                                      for r in hand) / max(len(hand), 1), 3)
    s["rescored"] = True
    walls = [r["wall_ms"] for r in rs]
    s["median_ms"] = int(statistics.median(walls))
    Path(path).write_text(json.dumps(data, indent=2))
    return s


if __name__ == "__main__":
    label = sys.argv[1]
    cases = {c["id"]: c for c in yaml.safe_load((ROOT / "evals" / "cases.yaml").read_text())}
    for f in sorted(glob.glob(str(ROOT / "evals" / "results" / f"{label}*.json"))):
        if "record-pass" in f:
            continue
        s = rescore_file(f, cases)
        print(f"{s['model']:45} {s['passed']}/{s['runs']}  critical={s['critical_failures']}")
