"""Runs the widget's JavaScript unit tests (tests/js) so `pytest -q` covers them too.
Skipped, not failed, on a machine without Node (the Python tests still run)."""
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent


@pytest.mark.skipif(shutil.which("node") is None, reason="Node.js not installed")
def test_render_js():
    result = subprocess.run(["node", "--test", "tests/js/"], cwd=ROOT,
                            capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stdout[-3000:] + result.stderr[-1000:]
