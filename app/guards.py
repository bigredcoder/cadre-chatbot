"""Abuse and budget guards (research findings #17).

A per-visitor rate limit: 12 messages a minute and 200 a day per IP address.

Honest limitation: this counter lives in memory, so each warm serverless instance counts
separately and a cold start resets it. It stops a casual script or a stuck retry loop, not a
determined attacker. The hard ceilings are the model key's own spend limit and the server-side
caps in main.py/config.py (message length, 8 messages of history, max tokens per reply, and
a deadline per turn). Production would move this to a shared store or Vercel's firewall rules (plan.md, "What's next").
"""
import time
from collections import defaultdict, deque

from app import config

_minute: dict[str, deque] = defaultdict(deque)
_day: dict[str, deque] = defaultdict(deque)
MAX_TRACKED = 10_000  # bound memory: forget everyone if this many IPs are tracked


def client_ip(headers) -> str:
    """Vercel puts the real visitor IP first in x-forwarded-for."""
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


def reset() -> None:
    """Tests only."""
    _minute.clear()
    _day.clear()
