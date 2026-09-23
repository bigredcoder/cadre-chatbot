"""Decides what a visitor's message is about, and whether a person should be offered.

Order of decisions:
1. Jev (TypeSafe AI, via Vercel AI Gateway) classifies the topic and answers one sharp
   yes/no: "is the visitor explicitly asking for a person?"
2. If Jev is unsure (topic probability below ROUTE_MIN_CONFIDENCE) or unreachable, the
   chat model classifies instead. The demo never depends on a week-old service.
3. Handoff is decided by rules, not by the model's enthusiasm:
   the topic is in HANDOFF_TOPICS, or the visitor explicitly asked for a person.
   (Phase 1 spike: a vague "needs a human?" score was unreliable. Research findings:
   model confidence isn't calibrated correctness.)
"""
import asyncio
import json
import time
from dataclasses import asdict, dataclass

import httpx

from app import config


@dataclass
class Route:
    topic: str
    confidence: float | None      # Jev's probability for the chosen topic; None for fallback
    router: str                   # "jev" | "fallback" | "default"
    asks_for_human: bool
    handoff: bool                 # rule-based: offer a person regardless of the answer
    note: str = ""                # why the fallback ran, for "Behind the scenes"
    route_ms: int = 0             # time spent deciding (for the with/without-Jev benchmark)
    route_cost_usd: float = 0.0   # what routing cost (Jev and/or the fallback model call)

    def as_dict(self) -> dict:
        return asdict(self)


def _questions() -> dict:
    return {
        "topic": {
            "type": "choice",
            "instructions": "Which topic is this website visitor's latest message about?",
            "criteria": config.TOPICS,
        },
        "asks_for_human": {
            "type": "boolean",
            "instructions": "Is the visitor explicitly asking to talk to a person or be contacted?",
            "criteria": {
                "true": "they ask for a person, a call, a meeting, a human, or to be contacted",
                "false": "they ask an informational question, even about cost or security",
            },
        },
    }


def _state(history: list[dict]) -> str:
    """What Jev reads: the latest message, with the previous one for follow-ups."""
    user_msgs = [m["content"] for m in history if m["role"] == "user"]
    latest = user_msgs[-1]
    if len(user_msgs) > 1:
        return f"Previous message: {user_msgs[-2]}\nLatest message: {latest}"
    return latest


async def _ask_jev(history: list[dict], token: str) -> tuple[dict, float]:
    body = {"model": config.JEV_MODEL, "state": _state(history), "questions": _questions()}
    async with httpx.AsyncClient(timeout=config.JEV_TIMEOUT_S) as client:
        for attempt in range(2):  # one quick retry: Jev rate-limits (HTTP 429) under load
            resp = await client.post(
                config.JEV_URL, json=body, headers={"Authorization": f"Bearer {token}"}
            )
            if resp.status_code not in (429, 503) or attempt == 1:
                break
            await asyncio.sleep(config.JEV_RETRY_DELAY_S)
    resp.raise_for_status()
    data = resp.json()
    cost = float(data.get("providerMetadata", {}).get("gateway", {}).get("cost") or 0)
    return data["answers"], cost


async def _ask_model(history: list[dict]) -> tuple[str, bool, float]:
    """Fallback classifier: the chat model returns JSON with the same two answers."""
    topics = ", ".join(config.TOPICS)
    prompt = (
        f"Classify the visitor's latest message for Cadre AI's website assistant.\n"
        f"Topics: {topics}.\n"
        'Reply with JSON only: {"topic": "<one topic>", "asks_for_human": true|false}\n\n'
        f"{_state(history)}"
    )
    async with httpx.AsyncClient(timeout=config.ANSWER_TIMEOUT_S) as client:
        resp = await client.post(
            config.OPENROUTER_URL,
            headers={"Authorization": f"Bearer {config.openrouter_key()}"},
            json={"model": config.ANSWER_MODEL, "max_tokens": 60, "temperature": 0,
                  "messages": [{"role": "user", "content": prompt}],
                  "response_format": {"type": "json_object"}, "usage": {"include": True}},
        )
    resp.raise_for_status()
    body = resp.json()
    cost = float((body.get("usage") or {}).get("cost") or 0)
    raw = body["choices"][0]["message"]["content"] or "{}"
    data = json.loads(raw[raw.find("{"): raw.rfind("}") + 1])
    topic = data.get("topic") if data.get("topic") in config.TOPICS else "services"
    return topic, bool(data.get("asks_for_human")), cost


def _decide(topic: str, confidence: float | None, router: str, asks: bool, note="",
            cost: float = 0.0) -> Route:
    handoff = topic in config.HANDOFF_TOPICS or asks
    return Route(topic, confidence, router, asks, handoff, note, route_cost_usd=round(cost, 8))


async def route(history: list[dict], request_token: str | None = None) -> Route:
    """Never raises: the worst case is a neutral default route, and the answer still runs."""
    started = time.monotonic()
    decision = await _route(history, request_token)
    decision.route_ms = int((time.monotonic() - started) * 1000)
    return decision


async def _route(history: list[dict], request_token: str | None) -> Route:
    note, spent = "", 0.0
    token = config.gateway_token(request_token)
    if config.ROUTER_MODE == "model_only":
        token, note = None, "jev disabled (benchmark)"
    if token:
        try:
            answers, spent = await _ask_jev(history, token)
            topic = answers["topic"]["choice"]
            confidence = float(answers["topic"]["probabilities"].get(topic, 0))
            asks = answers["asks_for_human"]["probability"] >= config.HUMAN_REQUEST_THRESHOLD
            if confidence >= config.ROUTE_MIN_CONFIDENCE:
                return _decide(topic, round(confidence, 3), "jev", asks, cost=spent)
            note = f"jev unsure ({topic} {confidence:.2f})"
        except httpx.HTTPStatusError as err:
            note = f"jev unavailable (HTTP {err.response.status_code})"
        except (httpx.HTTPError, KeyError, TypeError, ValueError) as err:
            note = f"jev unavailable ({type(err).__name__})"
    elif not note:
        note = "no gateway credential"

    try:
        topic, asks, cost = await _ask_model(history)
        return _decide(topic, None, "fallback", asks, note, cost=spent + cost)
    except (httpx.HTTPError, KeyError, ValueError, json.JSONDecodeError) as err:
        return _decide("services", None, "default", False,
                       f"{note}; fallback failed ({type(err).__name__})")
