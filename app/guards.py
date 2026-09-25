"""Abuse and budget guards (research findings #17).

A per-visitor rate limit: 12 messages a minute and 200 a day per IP address.

Two layers:
1. Vercel's firewall (set 09-24, rule "Chat API rate limit per IP"): 20 POSTs a minute per IP
   on /api/, counted across ALL instances. It's a project setting, NOT in this repo: a new
   deployment must recreate it (README → Deploy). Over it, Vercel answers 429 before the app
   runs, and the widget says to slow down. Verified live: request 21 got 429.
2. This module: a friendlier 12/minute and 200/day inside each instance. The strategist form
   (/api/leads) shares the same budget as chat messages.

Limitation of layer 2: this counter lives in memory, so each warm serverless instance counts
separately and a cold start resets it. It stops a casual script or a stuck retry loop, not a
determined attacker. The hard ceilings are the model key's own spend limit and the server-side
caps in main.py/config.py (message length, 8 messages of history, max tokens per reply, and
a deadline per turn). Production would move layer 2 to a shared store (plan.md, "What's next").
"""
import time
import unicodedata
from collections import defaultdict, deque

from app import config

_minute: dict[str, deque] = defaultdict(deque)
_day: dict[str, deque] = defaultdict(deque)
MAX_TRACKED = 10_000  # bound memory: forget everyone if this many IPs are tracked


def client_ip(headers) -> str:
    """Vercel puts the real visitor IP in x-forwarded-for, and overwrites any value the
    visitor sends, so it can't be spoofed (vercel.com/docs/headers/request-headers)."""
    forwarded = headers.get("x-forwarded-for", "")
    return (forwarded.split(",")[0].strip() or headers.get("x-real-ip") or "unknown")[:64]


def allow(ip: str, now: float | None = None) -> bool:
    """Record one message from `ip`; False if it's over either limit."""
    now = time.time() if now is None else now
    if len(_day) > MAX_TRACKED:
        _minute.clear()
        _day.clear()
    for window, limit, span in ((_minute[ip], config.RATE_LIMIT_PER_MINUTE, 60),
                                (_day[ip], config.RATE_LIMIT_PER_DAY, 86_400)):
        while window and now - window[0] > span:
            window.popleft()
        if len(window) >= limit:
            return False
    _minute[ip].append(now)
    _day[ip].append(now)
    return True


def clean_text(text: str) -> str:
    """Remove invisible and control characters from a visitor's message (audit 09-25).

    Zero-width spaces, direction overrides, and Unicode "tag" characters can hide instructions a
    human reviewer can't see (a known prompt-injection trick), and a null byte makes the database
    reject the row. Keeps line breaks and tabs; letters, accents, and emoji are untouched.
    """
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    return "".join(ch for ch in text
                   if ch in "\n\t" or unicodedata.category(ch) not in ("Cc", "Cf"))


def reset() -> None:
    """Tests only."""
    _minute.clear()
    _day.clear()
