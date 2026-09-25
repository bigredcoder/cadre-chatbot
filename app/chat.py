"""One chat turn, start to finish: clean → redact → route → answer → decide the handoff → save.

main.py turns these events into Server-Sent Events; this module decides what to say.
Every path ends in a reply the visitor can read: a canned answer, a streamed answer, or
the friendly fallback. Never a blank bubble, a stack trace, or a spinner that never stops.
"""
import asyncio
import logging
import re
from collections.abc import AsyncGenerator, AsyncIterator

from app import config
from app.answer import AnswerError, stream_answer
from app.guards import clean_text
from app.router import Route, answered_fully, route
from app.transcripts import redact, save_turn

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


# Tell the model what the widget will show under its reply, so the text matches the screen
# (Brian, 09-24: "How do I book a call?" said "look for the button on our website" while the
# form was right there). Mirrors the widget's rule in public/index.html: explicit request or
# booking → the form; any other rule handoff → a "Talk to a strategist" button.
SCREEN_FORM = ("A contact form to reach a strategist (name, email, subject, message). Tell them "
               "to fill in the form below. Also mention hello@gocadre.ai or cadre.ai/contact.")
SCREEN_OFFER = "A \"Talk to a strategist\" button that opens a short contact form."


def _screen(decision: Route) -> str:
    if not decision.handoff:
        return ""
    return SCREEN_FORM if decision.asks_for_human or decision.topic == "booking" else SCREEN_OFFER


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
    if OFFERS_A_PERSON.search(reply):   # checked first: the words and the screen must agree
        return True, "reply offers a person: offer kept"
    if not model_handoff:
        return False, None
    try:
        answered = await asyncio.wait_for(answered_fully(question, reply, oidc),
                                          config.ANSWER_CHECK_DEADLINE_S)
    except Exception:  # timeout or anything unexpected: an optional check never breaks an answer
        log.warning("answer check failed", exc_info=True)
        answered = None
    note = {True: "answered: offer skipped", False: "not answered: offer kept",
            None: "check unavailable: offer kept"}[answered]
    return answered is not True, note


async def _within(stream: AsyncGenerator[dict, None], seconds: float) -> AsyncIterator[dict]:
    """Pass the answer stream through, but stop it at a hard total deadline. (Audit 09-25: the
    deadline was only checked between chunks, so one slow read could stretch it to ~40 s.)"""
    loop = asyncio.get_running_loop()
    end = loop.time() + seconds
    try:
        while True:
            try:
                yield await asyncio.wait_for(stream.__anext__(), max(end - loop.time(), 0.01))
            except StopAsyncIteration:
                return
            except TimeoutError as err:
                raise AnswerError("answer took too long") from err
    finally:
        await stream.aclose()


async def run_turn(session_id: str, history: list[dict], oidc: str | None) -> AsyncIterator[tuple[str, dict]]:
    """Yield (event, data) pairs: route, token..., done; or error. Saves the turn at the end."""
    # Invisible characters are stripped, then personal details are redacted, before anything
    # reaches the model providers (OpenRouter, Jev) or the database
    history = [{**m, "content": redact(clean_text(m["content"])) or ""} if m["role"] == "user"
               else m for m in history]
    latest = history[-1]
    if not latest["content"].strip():  # nothing left once invisible characters are removed
        yield "error", {"message": "Please type a question about Cadre AI."}
        return
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
        stream = stream_answer(history, decision.topic, _screen(decision))
        async for item in _within(stream, config.ANSWER_DEADLINE_S):
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

    # Saved after the last event is sent. The widget still waits for the stream to close, so a
    # slow save can hold the input for up to SAVE_TIMEOUT_S (3 s); usually well under a second.
    await save_turn({
        **turn, "assistant_message": reply, "handoff": done.get("handoff"),
        "model_handoff": done.get("model_handoff"),
        "outcome": "handoff" if done.get("handoff") else "answered",
        "model": done.get("model"), "latency_ms": done.get("latency_ms"),
        "input_tokens": done.get("input_tokens"), "output_tokens": done.get("output_tokens"),
        "cost_usd": done.get("cost_usd"),
    })
