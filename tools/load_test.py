"""Small, planned load test. Runs against a local server by default; `--live` targets the
live site. Costs a few cents on the target server's key.

Two scenarios:
  1. Concurrency: N visitors ask at the same moment (different questions). Measures time to
     first token, total time, errors, and how often Jev fell back.
  2. Burst from one visitor: M rapid messages from this machine. Expect the app's limit
     (12/min per instance) to answer some of the excess with a friendly message, and Vercel's
     firewall to return HTTP 429 from request 21 (listed under "other"): no 500s, no model spend.
     The firewall exists only on the live site.

Usage: .venv/bin/python tools/load_test.py [--live | --base URL] [--concurrent 10] [--burst 25]
Local: start the server first (`SAVE_TURNS=0 .venv/bin/uvicorn app.main:app --port 8000`).
"""
import argparse
import asyncio
import json
import time
import uuid
from urllib.parse import urlparse

import httpx

LOCAL = "http://127.0.0.1:8000"
LIVE = "https://cadre-chatbot-xi.vercel.app"
QUESTIONS = [
    "What does Cadre do?", "Do you work with hotels?", "What is the AI Maturity Index?",
    "Where is the client portal?", "How long is the AI Transformation Intensive?",
    "Do you build AI agents?", "Which AI models do you use?", "Is Cadre a fit for a lender?",
    "What workshops do you offer executives?", "What results have clients seen?",
]


async def ask(client: httpx.AsyncClient, base: str, question: str) -> dict:
    started = time.monotonic()
    first, events, status = None, {}, None
    try:
        async with client.stream("POST", f"{base}/api/chat", json={
                "session_id": f"load-{uuid.uuid4().hex[:12]}",
                "messages": [{"role": "user", "content": question}]}) as resp:
            status = resp.status_code
            event = None
            async for line in resp.aiter_lines():
                if line.startswith("event: "):
                    event = line[7:]
                elif line.startswith("data: "):
                    if event == "token" and first is None:
                        first = time.monotonic() - started
                    events[event] = json.loads(line[6:])
    except httpx.HTTPError as err:
        return {"status": "network", "error": type(err).__name__}
    return {"status": status, "first_token_s": first, "total_s": time.monotonic() - started,
            "router": events.get("route", {}).get("router"),
            "note": events.get("route", {}).get("note", ""),
            "error": events.get("error", {}).get("message"),
            "rate_limited": "sending messages quickly" in json.dumps(events.get("error", {}))}


def pct(values, p):
    values = sorted(v for v in values if v is not None)
    return round(values[max(0, int(len(values) * p) - 1)], 2) if values else None


async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default=LOCAL, help=f"server to test (default {LOCAL})")
    ap.add_argument("--live", action="store_true", help=f"test the live site, {LIVE}")
    ap.add_argument("--concurrent", type=int, default=10)
    ap.add_argument("--burst", type=int, default=25)
    args = ap.parse_args()
    base = LIVE if args.live else args.base
    if urlparse(base).hostname not in ("127.0.0.1", "localhost"):
        print(f"WARNING: not a local server: {base}. This spends real model credit on its key.\n")

    async with httpx.AsyncClient(timeout=60) as client:
        print(f"1) {args.concurrent} visitors at once ({base})")
        runs = await asyncio.gather(*(ask(client, base, QUESTIONS[i % len(QUESTIONS)])
                                      for i in range(args.concurrent)))
        ok = [r for r in runs if r["status"] == 200 and not r["error"]]
        print(json.dumps({
            "answered": f"{len(ok)}/{len(runs)}",
            "errors_or_limited": [r.get("error") or r["status"] for r in runs if r not in ok],
            "first_token_p50_s": pct([r["first_token_s"] for r in ok], 0.5),
            "first_token_p90_s": pct([r["first_token_s"] for r in ok], 0.9),
            "total_p50_s": pct([r["total_s"] for r in ok], 0.5),
            "total_p90_s": pct([r["total_s"] for r in ok], 0.9),
            "routed_by": {k: sum(r["router"] == k for r in ok) for k in ("jev", "fallback", "default")},
            "fallback_reasons": sorted({r["note"] for r in ok if r["note"]}),
        }, indent=2))

        await asyncio.sleep(61)  # let the per-minute window clear before the burst
        print(f"\n2) burst: {args.burst} messages from one visitor, as fast as possible")
        burst = await asyncio.gather(*(ask(client, base, "What does Cadre do?")
                                       for _ in range(args.burst)))
        print(json.dumps({
            "answered": sum(r["status"] == 200 and not r["error"] for r in burst),
            "rate_limited_friendly": sum(r["rate_limited"] for r in burst),
            "server_errors_5xx": sum(isinstance(r["status"], int) and r["status"] >= 500
                                     for r in burst),
            "other": [r.get("error") or r["status"] for r in burst
                      if r["status"] != 200 or (r["error"] and not r["rate_limited"])],
        }, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
