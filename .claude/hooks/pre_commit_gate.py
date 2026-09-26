"""Claude Code hook: before any `git commit`, run lint, the type check, and unit tests; block
the commit if any fails. Reads the tool call from stdin (Claude Code hook protocol) and exits 2
to block. It runs from the project root (`cd "$CLAUDE_PROJECT_DIR"` in .claude/settings.json)
and loads only when Claude Code is started in this folder.

What counts as a commit: the command is split at `&&`, `||`, `;`, `|`, `&`, parentheses,
backticks, redirections and line breaks, respecting quotes. `#` comments aren't stripped, so a
comment can't hide the next line. A part is a commit when, after any `NAME=value` prefixes and
leading words in LEADING (`env`, `sudo`, `time`, `then`, `{`, ...), the program is `git` and its
first word that isn't one of git's own options is `commit`. Git options before it are skipped,
including `-C <path>` and `-c <name>=<value>`. `bash -c "..."` (or `-lc`) is checked inside. So
`git -C . commit`, `FOO=1 git commit` and `ruff check . && git commit` count;
`git log --grep commit` and `echo "git commit"` don't. Not caught: git aliases (`git ci`),
`xargs`, `eval`, and wrappers given their own options (`sudo -u x`, `env -i`). If the command
can't be split (unbalanced quotes), any `git ... commit` on one line counts.

Fails closed: once a commit is detected, anything that stops a check from running (no .venv, an
exception, a check hanging past TIMEOUT_S) exits 2. Everything else exits 0 at once.
"""
import json
import os
import re
import shlex
import subprocess
import sys

CHECKS = ([".venv/bin/ruff", "check", "."], [".venv/bin/python", "-m", "mypy", "app"],
          [".venv/bin/python", "-m", "pytest", "-q"])
# Per check. 3 x 120 s stays under Claude Code's default 600 s hook timeout, and a hook that
# times out doesn't block, so a hang has to end here.
TIMEOUT_S = 120

SEPARATORS = set("();<>|&`\n")
LEADING = {"env", "sudo", "time", "command", "exec", "nohup", "!", "{", "if", "elif", "then",
           "else", "while", "until", "do"}
GIT_OPTIONS_WITH_VALUE = {"-C", "-c", "--git-dir", "--work-tree", "--namespace", "--config-env",
                          "--super-prefix"}
SHELLS = {"bash", "sh", "zsh"}
ASSIGNMENT = re.compile(r"[A-Za-z_][A-Za-z0-9_]*=")
FALLBACK = re.compile(r"\bgit\b[^\n]*\bcommit\b")


def _parts(command: str) -> list[list[str]]:
    """Split a shell command into simple commands (lists of words)."""
    lex = shlex.shlex(command, posix=True, punctuation_chars="".join(sorted(SEPARATORS)))
    lex.whitespace = " \t\r"  # line breaks separate commands, so they're punctuation here
    lex.whitespace_split = True
    lex.commenters = ""  # shlex would drop a `#` comment and the line break after it
    parts: list[list[str]] = [[]]
    for token in lex:
        if token and set(token) <= SEPARATORS:
            parts.append([])
        else:
            parts[-1].append(token)
    return [part for part in parts if part]


def _part_is_commit(words: list[str]) -> bool:
    i = 0
    while i < len(words) and (ASSIGNMENT.match(words[i]) or words[i] in LEADING):
        i += 1
    if i == len(words):
        return False
    program = os.path.basename(words[i])
    if program in SHELLS:  # `bash -c "script"` or `bash -lc "script"`
        flags = [j for j in range(i + 1, len(words) - 1)
                 if words[j].startswith("-") and not words[j].startswith("--") and "c" in words[j]]
        return bool(flags) and is_commit(words[flags[0] + 1])
    if program != "git":
        return False
    i += 1
    while i < len(words) and words[i].startswith("-"):
        i += 2 if words[i] in GIT_OPTIONS_WITH_VALUE else 1
    return i < len(words) and words[i] == "commit"


def is_commit(command: str) -> bool:
    """True if running `command` in a shell would run `git commit` (rules in the docstring)."""
    if "commit" not in command:
        return False
    try:
        parts = _parts(command)
    except ValueError:  # unbalanced quotes: match loosely, so a commit still gets checked
        return bool(FALLBACK.search(command))
    return any(_part_is_commit(words) for words in parts)


def run_checks() -> int:
    for check in CHECKS:
        name = " ".join(check)
        try:
            result = subprocess.run(check, capture_output=True, text=True, check=False,
                                    timeout=TIMEOUT_S)
        # Deliberately broad: no .venv, a timeout, or anything else blocks the commit.
        except Exception as exc:  # noqa: BLE001
            print(f"Commit blocked: couldn't run `{name}` in {os.getcwd()}: {exc}\n"
                  "Set up .venv (see Commands in CLAUDE.md) or run the checks by hand.",
                  file=sys.stderr)
            return 2
        if result.returncode != 0:
            print(f"Commit blocked: `{name}` failed.\n{result.stdout[-1500:]}", file=sys.stderr)
            return 2
    return 0


def main() -> int:
    raw = sys.stdin.read()
    try:
        call = json.loads(raw)
        command = call.get("tool_input", {}).get("command", "")
    except (ValueError, AttributeError):  # unreadable payload: scan the raw text instead
        command = raw
    if not isinstance(command, str):
        command = str(command)
    return run_checks() if is_commit(command) else 0


if __name__ == "__main__":
    sys.exit(main())
