"""Web routes for Cadence. Routes only: logic lives in the other app/ modules."""
import json
import re
from typing import Literal

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel, Field

from app import config
from app.answer import AnswerError, stream_answer
from app.router import route
from app.transcripts import save_turn

app = FastAPI(title="Cadence", docs_url=None, redoc_url=None)


class Message(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=config.MAX_MESSAGE_CHARS * 4)


class ChatRequest(BaseModel):
    session_id: str = Field(min_length=8, max_length=64)
    messages: list[Message] = Field(min_length=1)


def sse(event: str, data: dict) -> str:
    """One Server-Sent Event: the browser reads these as the answer streams in."""
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


OFF_TOPIC_REPLY = (
    "I can only help with questions about Cadre AI. For example, I can explain Cadre's "
    "services, the AI Maturity Index, or connect you with a strategist."
)

FALLBACK = (
    "Sorry, I couldn't answer that just now. You can reach the Cadre team at "
    f"{config.CONTACT_EMAIL} or cadre.ai/contact."
)


@app.post("/api/chat")
async def chat(req: ChatRequest, request: Request) -> StreamingResponse:
    history = [m.model_dump() for m in req.messages]
    latest = history[-1]
    oidc = request.headers.get("x-vercel-oidc-token")  # Vercel's per-request identity

    async def events():
        if latest["role"] != "user" or len(latest["content"]) > config.MAX_MESSAGE_CHARS:
            yield sse("error", {"message": "Please keep messages under 1,000 characters."})
            return
        turn = {"session_id": req.session_id, "user_message": latest["content"]}
        if len(history) > config.MAX_TURNS_PER_SESSION * 2:
            reply = "We've covered a lot. A strategist can take it from here."
            yield sse("token", {"text": reply})
            yield sse("done", {"handoff": True, "reason": "turn_limit"})
            await save_turn({**turn, "assistant_message": reply, "outcome": "turn_limit",
                             "handoff": True})
            return

        decision = await route(history, oidc)
        yield sse("route", decision.as_dict())
        turn.update(topic=decision.topic, confidence=decision.confidence,
                    router=decision.router, asks_for_human=decision.asks_for_human)

        confident_off_topic = (
            decision.topic == "off_topic" and decision.router == "jev"
            and (decision.confidence or 0) >= config.OFF_TOPIC_CANNED_CONFIDENCE
        )
        if confident_off_topic and not decision.handoff:
            # No model call: cheaper, and prompt-injection attempts never reach the model
            yield sse("token", {"text": OFF_TOPIC_REPLY})
            yield sse("done", {"handoff": False, "model": "none (canned reply)"})
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
                    item["handoff"] = decision.handoff or item["handoff"]
                    done = item
                yield sse(kind, item)
        except AnswerError:
            # Never show a blank bubble or a stack trace (research findings #11)
            yield sse("error", {"message": FALLBACK})
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

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


class LeadRequest(BaseModel):
    """Mirrors the fields on cadre.ai/contact."""
    name: str = Field(min_length=1, max_length=100)
    email: str = Field(min_length=3, max_length=200)
    subject: str = Field(min_length=1, max_length=200)
    message: str = Field(min_length=1, max_length=2000)
    idempotency_key: str = Field(min_length=8, max_length=64)


EMAIL_OK = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_seen_leads: set[str] = set()  # per-instance; enough to absorb double-clicks in a demo


@app.post("/api/leads")
def lead(req: LeadRequest) -> dict:
    """DEMO handoff form (Brian's decision): validates like a real form, sends nothing,
    stores nothing, and says so. A repeat submit with the same key returns the same
    result instead of creating a second request (research findings #10)."""
    if not EMAIL_OK.match(req.email.strip()):
        return {"ok": False, "field": "email", "message": "Enter a valid email address."}
    duplicate = req.idempotency_key in _seen_leads
    if len(_seen_leads) > 5000:  # keep memory bounded
        _seen_leads.clear()
    _seen_leads.add(req.idempotency_key)
    first = req.name.strip().split()[0]
    return {
        "ok": True,
        "duplicate": duplicate,
        "message": (
            f"Thanks, {first}. This is a demo, so nothing was sent to Cadre. In production "
            "this goes straight to their team and a strategist follows up by email. You can "
            f"also reach them now at {config.CONTACT_EMAIL}."
        ),
    }


@app.get("/api/health")
def health() -> dict:
    """Lets us (and Vercel) confirm the app is up. Never reveals key values."""
    return {"status": "ok", "answer_model": config.ANSWER_MODEL,
            "openrouter_key": bool(config.openrouter_key())}


# Local dev only. On Vercel, files in public/ are served as static files and are NOT
# bundled with this function, so these routes never run there (see CLAUDE.md gotchas).
@app.get("/")
def home() -> FileResponse:
    """The demo page with the chat bubble."""
    return FileResponse(config.ROOT / "public" / "index.html")


@app.get("/privacy.html")
def privacy() -> FileResponse:
    """What chat data we store (research findings #8)."""
    return FileResponse(config.ROOT / "public" / "privacy.html")
