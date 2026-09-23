"""Web routes for Cadence. Routes only: logic lives in the other app/ modules."""
import json
from typing import Literal

from fastapi import FastAPI
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel, Field

from app import config
from app.answer import AnswerError, stream_answer

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


FALLBACK = (
    "Sorry, I couldn't answer that just now. You can reach the Cadre team at "
    f"{config.CONTACT_EMAIL} or cadre.ai/contact."
)


@app.post("/api/chat")
async def chat(req: ChatRequest) -> StreamingResponse:
    history = [m.model_dump() for m in req.messages]
    latest = history[-1]

    async def events():
        if latest["role"] != "user" or len(latest["content"]) > config.MAX_MESSAGE_CHARS:
            yield sse("error", {"message": "Please keep messages under 1,000 characters."})
            return
        if len(history) > config.MAX_TURNS_PER_SESSION * 2:
            yield sse("token", {"text": "We've covered a lot. A strategist can take it from here."})
            yield sse("done", {"handoff": True, "reason": "turn_limit"})
            return
        topic = "unknown"  # Phase 4 replaces this with Jev routing
        yield sse("route", {"topic": topic, "router": "none"})
        try:
            async for item in stream_answer(history, topic):
                kind = item.pop("type")
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
