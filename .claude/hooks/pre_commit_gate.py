"""Claude Code hook: before any `git commit`, run lint and unit tests; block the commit if
either fails. Reads the tool call from stdin (Claude Code hook protocol) and exits 2 to block."""
import json
import subprocess
import sys

call = json.load(sys.stdin)
command = call.get("tool_input", {}).get("command", "")
if "git commit" not in command:
    sys.exit(0)

for check in ([".venv/bin/ruff", "check", "."], [".venv/bin/python", "-m", "pytest", "-q"]):
    result = subprocess.run(check, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        print(f"Commit blocked: `{' '.join(check)}` failed.\n{result.stdout[-1500:]}",
              file=sys.stderr)
        sys.exit(2)
sys.exit(0)
