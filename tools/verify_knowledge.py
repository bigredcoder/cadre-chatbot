"""Check that every quote in knowledge/cadre.md appears on its cited source page.

Each fact line looks like:  - fact — "exact quote" — https://cadre.ai/page
We download each page once, flatten its text, and string-match the quote.
Run: .venv/bin/python tools/verify_knowledge.py   (exit code 1 if any quote fails)
"""
import html
import re
import sys
from pathlib import Path

import httpx

KNOWLEDGE = Path(__file__).resolve().parent.parent / "knowledge" / "cadre.md"
LINE = re.compile(r'"(?P<quote>[^"]+)"\s+[—-]+\s+(?P<url>https?://\S+)')


def page_text(raw: str) -> str:
    """Strip tags and collapse whitespace so quotes match regardless of markup."""
    raw = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", raw)
    text = html.unescape(re.sub(r"<[^>]+>", " ", raw))
    return normalize(text)


def normalize(s: str) -> str:
    s = s.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
    s = s.replace("—", "-").replace("–", "-").replace("‑", "-")
    s = s.replace(" ", " ")
    s = re.sub(r"\s+", " ", s)
    s = re.sub(r" ([.,!?;:])", r"\1", s)  # markup can split "Confidence" from its "."
    return s.strip().lower()


def main() -> int:
    cache: dict[str, str] = {}
    checked = failed = 0
    for n, line in enumerate(KNOWLEDGE.read_text().splitlines(), 1):
        m = LINE.search(line)
        if not m:
            continue
        url, quote = m["url"].rstrip(").,"), m["quote"]
        if url not in cache:
            cache[url] = page_text(httpx.get(url, follow_redirects=True, timeout=20).text)
        checked += 1
        if normalize(quote) not in cache[url]:
            failed += 1
            print(f"FAIL line {n}: {quote!r} not found on {url}")
    print(f"{checked} quotes checked, {failed} failed, {len(cache)} pages fetched")
    return 1 if failed or not checked else 0


if __name__ == "__main__":
    sys.exit(main())
