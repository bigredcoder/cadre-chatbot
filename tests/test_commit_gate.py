"""The commit gate, .claude/hooks/pre_commit_gate.py: which commands count as a commit, and that
it blocks (exit 2) when the checks can't run. (09-25 review: it missed `git -C . commit`, and
with no .venv it exited 1, which Claude Code doesn't treat as a block.)"""
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

HOOK = Path(__file__).resolve().parent.parent / ".claude" / "hooks" / "pre_commit_gate.py"
_spec = importlib.util.spec_from_file_location("pre_commit_gate", HOOK)
assert _spec and _spec.loader
gate = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(gate)

COMMITS = [
    'git commit -m "Add x"',
    "git -C . commit -m x",
    "git -c user.name=x commit -m x",
    "git --git-dir=.git --work-tree . commit",
    "FOO=1 git commit -m x",
    "env SAVE_TURNS=1 git commit -m x",
    "/usr/bin/git commit -m x",
    "ruff check . && git commit -m x",
    "ruff check .; git commit -m x",
    "echo msg | git commit -F -",
    "cd /repo\ngit commit -m x",
    "git add .  # stage\ngit commit -m x",  # a comment must not hide the next line
    "echo a#b; git commit -m x",
    "if true; then git commit -m x; fi",
    "{ git commit -m x; }",
    "sudo git commit -m x",
    "time git commit -m x",
    "echo `git commit -m x`",
    "(git commit -m x)",
    'bash -c "git commit -m x"',
    "bash -lc 'git commit -m x'",
    "git commit -m \"$(cat <<'EOF'\nTitle\n\nBody with \"quotes\" and it's\nEOF\n)\"",
    'git commit -m "unbalanced',  # can't be split: the loose match still catches it
]

NOT_COMMITS = [
    "git status",
    "git log --grep commit",
    'echo "git commit"',
    "grep -n 'git commit' build-process.md",
    "echo done # git commit",
    "# commit it\ngit status",
    "git help commit",
    "git commit-tree HEAD",
    "ls commits/",
    "",
]


@pytest.mark.parametrize("command", COMMITS)
def test_commits_are_caught(command):
    assert gate.is_commit(command)


@pytest.mark.parametrize("command", NOT_COMMITS)
def test_other_commands_pass(command):
    assert not gate.is_commit(command)


def _run_hook(payload: str, cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(HOOK)], input=payload, cwd=cwd,
                          capture_output=True, text=True, timeout=30, check=False)


def test_commit_without_venv_is_blocked(tmp_path):
    # The hook runs its checks from its working directory; tmp_path has no .venv.
    payload = json.dumps({"tool_input": {"command": "git -C . commit -m x"}})
    result = _run_hook(payload, tmp_path)
    assert result.returncode == 2
    assert "Commit blocked" in result.stderr


def test_non_commit_passes_without_running_checks(tmp_path):
    payload = json.dumps({"tool_input": {"command": "git status"}})
    result = _run_hook(payload, tmp_path)
    assert result.returncode == 0
    assert result.stderr == ""
