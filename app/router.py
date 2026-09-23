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
import json
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


async def _ask_jev(history: list[dict], token: str) -> dict:
    body = {"model": config.JEV_MODEL, "state": _state(history), "questions": _questions()}
    async with httpx.AsyncClient(timeout=config.JEV_TIMEOUT_S) as client:
        resp = await client.post(
            config.JEV_URL, json=body, headers={"Authorization": f"Bearer {token}"}
        )
    resp.raise_for_status()
    return resp.json()["answers"]


async def _ask_model(history: list[dict]) -> tuple[str, bool]:
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
                  "response_format": {"type": "json_object"}},
        )
    resp.raise_for_status()
    raw = resp.json()["choices"][0]["message"]["content"] or "{}"
    data = json.loads(raw[raw.find("{"): raw.rfind("}") + 1])
    topic = data.get("topic") if data.get("topic") in config.TOPICS else "services"
    return topic, bool(data.get("asks_for_human"))


def _decide(topic: str, confidence: float | None, router: str, asks: bool, note="") -> Route:
    handoff = topic in config.HANDOFF_TOPICS or asks
    return Route(topic, confidence, router, asks, handoff, note)


async def route(history: list[dict], request_token: str | None = None) -> Route:
    """Never raises: the worst case is a neutral default route, and the answer still runs."""
    note = ""
    token = config.gateway_token(request_token)
    if token:
        try:
            answers = await _ask_jev(history, token)
            topic = answers["topic"]["choice"]
            confidence = float(answers["topic"]["probabilities"].get(topic, 0))
            asks = answers["asks_for_human"]["probability"] >= config.HUMAN_REQUEST_THRESHOLD
            if confidence >= config.ROUTE_MIN_CONFIDENCE:
                return _decide(topic, round(confidence, 3), "jev", asks)
            note = f"jev unsure ({topic} {confidence:.2f})"
        except (httpx.HTTPError, KeyError, TypeError, ValueError) as err:
            note = f"jev unavailable ({type(err).__name__})"
    else:
        note = "no gateway credential"

    try:
        topic, asks = await _ask_model(history)
        return _decide(topic, None, "fallback", asks, note)
    except (httpx.HTTPError, KeyError, ValueError, json.JSONDecodeError) as err:
        return _decide("services", None, "default", False,
                       f"{note}; fallback failed ({type(err).__name__})")
