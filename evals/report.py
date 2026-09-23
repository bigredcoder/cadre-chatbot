"""Write a readable failure report with real examples from saved eval results.

Every claimed error comes with the question, the bot's actual reply, and what the check
caught, so nobody has to take a pass/fail number on trust.

Usage: .venv/bin/python -m evals.report compare-fixed      # → evals/results/compare-fixed-failures.md
"""
import glob
import json
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
RESULTS = ROOT / "evals" / "results"
SEVERITY_ORDER = {"critical": 0, "major": 1, "moderate": 2, "minor": 3}


def main(label: str) -> Path:
    cases = {c["id"]: c for c in yaml.safe_load((ROOT / "evals" / "cases.yaml").read_text())}
    lines = [f"# Failures with examples: {label}", "",
             "Each entry: the question, the check that failed, and the bot's actual reply.", ""]
    for f in sorted(glob.glob(str(RESULTS / f"{label}-*.json"))):
        data = json.loads(Path(f).read_text())
        fails = [r for r in data["results"] if not r["passed"]]
        model = data["summary"]["model"]
        lines += [f"## {model}: {len(fails)} failed of {data['summary']['runs']} runs", ""]
        if not fails:
            lines += ["No failures.", ""]
        for r in sorted(fails, key=lambda r: (SEVERITY_ORDER.get(r.get("failure_severity") or
                                                                  r["severity"], 9), r["id"])):
            case = cases.get(r["id"], {})
            reply = (r["reply"] or "(no reply)").strip().replace("\n", " ")
            lines += [
                (f"**{(r.get('failure_severity') or r['severity']).upper()} · {r['id']}** "
                 f"(run {r.get('run', 1)})"),
                f"- Question: \"{case.get('turns', ['?'])[-1]}\""
                + (f" (after: \"{case['turns'][0]}\")" if len(case.get("turns", [])) > 1 else ""),
                f"- Caught: {'; '.join(r['problems'])}",
                (f"- Routed as: {r['route'].get('topic')} via {r['route'].get('router')}"
                 f"; handoff shown: {r['done'].get('handoff')}"),
                f"- Actual reply: \"{reply[:400]}{'…' if len(reply) > 400 else ''}\"",
                "",
            ]
    out = RESULTS / f"{label}-failures.md"
    out.write_text("\n".join(lines))
    return out


if __name__ == "__main__":
    print(main(sys.argv[1] if len(sys.argv) > 1 else "compare-fixed"))
