"""One chat turn, start to finish: route → answer → decide the handoff → save.

main.py turns these events into Server-Sent Events; this module decides what to say.
Every path ends in a reply the visitor can read: a canned answer, a streamed answer, or
the friendly fallback. Never a blank bubble, a stack trace, or a spinner that never stops.
"""
import asyncio
import logging
import re
from collections.abc import AsyncIterator

from app import config
from app.answer import AnswerError, stream_answer
from app.router import Route, answered_fully, route
from app.transcripts import save_turn

log = logging.getLogger("cadence")

OFF_TOPIC_REPLY = (
    "I can only help with questions about Cadre AI. For example, I can explain Cadre's "
    "services, the AI Maturity Index, or connect you with a strategist."
)
FALLBACK = (
    "Sorry, I couldn't answer that just now. You can reach the Cadre team at "
    f"{config.CONTACT_EMAIL} or cadre.ai/contact."
)
# The reply itself offers a person ("I can connect you with a strategist"). Then the button
# must show, whatever the answer check says: never promise what the screen doesn't offer.
OFFERS_A_PERSON = re.compile(r"(connect|put) you (with|in touch)|talk (to|with) an? (AI )?strategist\?",
                             re.IGNORECASE)


async def _route(history: list[dict], oidc: str | None) -> Route:
    """Routing has its own deadline; past it, answer anyway with a neutral topic."""
    try:
        return await asyncio.wait_for(route(history, oidc), config.ROUTE_DEADLINE_S)
    except TimeoutError:
        return Route("services", None, "default", False, False, note="routing timed out")


async def _offer_after_answer(decision: Route, model_handoff: bool, question: str, reply: str,
                              oidc: str | None) -> tuple[bool, str | None]:
    """Show the strategist offer? Rules first; a model-only offer gets a second opinion."""
    if decision.handoff:
        return True, None
    if not model_handoff:
        return False, None
    if OFFERS_A_PERSON.search(reply):
        return True, "reply offers a person: offer kept"
    try:
        answered = await asyncio.wait_for(answered_fully(question, reply, oidc),
                                          config.ANSWER_CHECK_DEADLINE_S)
    except TimeoutError:
        answered = None
    note = {True: "answered: offer skipped", False: "not answered: offer kept",
            None: "check unavailable: offer kept"}[answered]
    return answered is not True, note


async def run_turn(session_id: str, history: list[dict], oidc: str | None) -> AsyncIterator[tuple[str, dict]]:
    """Yield (event, data) pairs: route, token..., done; or error. Saves the turn at the end."""
    latest = history[-1]
    turn = {"session_id": session_id, "user_message": latest["content"]}
    try:
        decision = await _route(history, oidc)
    except Exception:  # deliberate: the visitor must always get a reply
        log.exception("router crashed")  # visible in Vercel logs
        yield "error", {"message": FALLBACK}
        return
    yield "route", decision.as_dict()
    turn.update(topic=decision.topic, confidence=decision.confidence,
                router=decision.router, asks_for_human=decision.asks_for_human)

    confident_off_topic = (
        decision.topic == "off_topic" and decision.router == "jev"
        and (decision.confidence or 0) >= config.OFF_TOPIC_CANNED_CONFIDENCE
    )
    if confident_off_topic and not decision.handoff:
        # No model call: cheaper, and prompt-injection attempts never reach the model
        yield "token", {"text": OFF_TOPIC_REPLY}
        yield "done", {"handoff": False, "model": "none (canned reply)"}
        await save_turn({**turn, "assistant_message": OFF_TOPIC_REPLY,
                         "outcome": "off_topic", "handoff": False})
        return

    reply, done = "", {}
    try:
        async for item in stream_answer(history, decision.topic):
            kind = item.pop("type")
            if kind == "token":
                reply += item["text"]
            if kind == "done":
                item["model_handoff"] = item["handoff"]
                item["handoff"], check = await _offer_after_answer(
                    decision, item["handoff"], latest["content"], reply, oidc)
                if check:
                    item["handoff_check"] = check
                done = item
            yield kind, item
    except Exception as err:  # AnswerError or anything unexpected
        # Never show a blank bubble or a stack trace (research findings #11)
        if not isinstance(err, AnswerError):
            log.exception("answer stream crashed")
        yield "error", {"message": FALLBACK}
        await save_turn({**turn, "assistant_message": None, "outcome": "error"})
        return

    # Saved after the visitor already has the full answer, so it never slows the chat
    await save_turn({
        **turn, "assistant_message": reply, "handoff": done.get("handoff"),
        "model_handoff": done.get("model_handoff"),
        "outcome": "handoff" if done.get("handoff") else "answered",
        "model": done.get("model"), "latency_ms": done.get("latency_ms"),
        "input_tokens": done.get("input_tokens"), "output_tokens": done.get("output_tokens"),
        "cost_usd": done.get("cost_usd"),
    })
