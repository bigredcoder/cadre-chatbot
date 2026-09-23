"""Web routes for Cadence. Routes only: logic lives in the other app/ modules."""
import json
from typing import Literal

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel, Field

from app import config
from app.answer import AnswerError, stream_answer
from app.router import route

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
        if len(history) > config.MAX_TURNS_PER_SESSION * 2:
            yield sse("token", {"text": "We've covered a lot. A strategist can take it from here."})
            yield sse("done", {"handoff": True, "reason": "turn_limit"})
            return
        decision = await route(history, oidc)
        yield sse("route", decision.as_dict())
        confident_off_topic = (
            decision.topic == "off_topic" and decision.router == "jev"
            and (decision.confidence or 0) >= config.OFF_TOPIC_CANNED_CONFIDENCE
        )
        if confident_off_topic and not decision.handoff:
            # No model call: cheaper, and prompt-injection attempts never reach the model
            yield sse("token", {"text": OFF_TOPIC_REPLY})
            yield sse("done", {"handoff": False, "model": "none (canned reply)"})
            return
        try:
            async for item in stream_answer(history, decision.topic):
                kind = item.pop("type")
                if kind == "done":
                    item["model_handoff"] = item["handoff"]
                    item["handoff"] = decision.handoff or item["handoff"]
                yield sse(kind, item)
        except AnswerError:
            # Never show a blank bubble or a stack trace (research findings #11)
            yield sse("error", {"message": FALLBACK})

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.get("/api/health")
def health() -> dict:
    """Lets us (and Vercel) confirm the app is up. Never reveals key values."""
    return {"status": "ok", "answer_model": config.ANSWER_MODEL,
            "openrouter_key": bool(config.openrouter_key())}


@app.get("/")
def home() -> FileResponse:
    """The demo page with the chat bubble."""
    return FileResponse(config.ROOT / "public" / "index.html")


@app.get("/privacy")
def privacy() -> FileResponse:
    """What chat data we store (research findings #8)."""
    return FileResponse(config.ROOT / "public" / "privacy.html")
