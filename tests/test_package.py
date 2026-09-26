"""tools/package.sh builds the submission zip from a fresh clone of HEAD. This checks the zip
has .git, stays small, and holds no .env, .vercel/, .venv/ or other local-only files.
--allow-dirty so it also passes while a commit is being staged."""
import re
import shutil
import subprocess
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
FORBIDDEN = re.compile(r"(^|/)(\.env(\.[^/]+)?|\.DS_Store)(/|$)"
                       r"|(^|/)(\.vercel|\.venv|node_modules|__pycache__|dist|build)(/|$)")
MISSING = [tool for tool in ("bash", "git", "zip", "unzip") if shutil.which(tool) is None]


@pytest.mark.skipif(bool(MISSING), reason=f"not installed: {MISSING}")
@pytest.mark.skipif(not (ROOT / ".git").exists(), reason="not a git checkout")
def test_package_zip_is_clean(tmp_path):
    out = tmp_path / "submission.zip"
    result = subprocess.run(["bash", "tools/package.sh", "--allow-dirty", str(out)], cwd=ROOT,
                            capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stdout + result.stderr

    with zipfile.ZipFile(out) as z:
        names = z.namelist()
    assert "cadre-chatbot/.git/HEAD" in names
    assert "cadre-chatbot/app/main.py" in names
    assert [n for n in names if FORBIDDEN.search(n) and not n.endswith("/.env.example")] == []
    assert out.stat().st_size < 5 * 1024 * 1024
