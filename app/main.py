"""Web routes for Cadence. Routes only: logic lives in the other app/ modules."""
import json
import re
from typing import Literal

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from app import config, guards
from app.chat import run_turn

app = FastAPI(title="Cadence", docs_url=None, redoc_url=None)


class Message(BaseModel):
    role: Literal["user", "assistant"]
    # Assistant replies can be longer than visitor messages; both are capped server-side
    content: str = Field(min_length=1, max_length=config.MAX_MESSAGE_CHARS * 4)


class ChatRequest(BaseModel):
    session_id: str = Field(min_length=8, max_length=64)
    # The client sends history; the server only accepts the recent turns (code review #2)
    messages: list[Message] = Field(min_length=1, max_length=config.MAX_HISTORY_MESSAGES)


@app.exception_handler(RequestValidationError)
async def bad_request(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Malformed requests get one plain sentence, not the framework's field-by-field dump.
    (The widget never sends these; this is for anyone calling the API directly.)"""
    fields = {str(err["loc"][-1]) for err in exc.errors() if err.get("loc")}
    if "content" in fields:
        message = "Each message needs text, and must be under the length limit."
    elif "messages" in fields:
        message = f"Send between 1 and {config.MAX_HISTORY_MESSAGES} messages."
    else:
        message = "That request wasn't in the expected format."
    return JSONResponse(status_code=422, content={"error": message})


def sse(event: str, data: dict) -> str:
    """One Server-Sent Event: the browser reads these as the answer streams in."""
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


@app.post("/api/chat")
async def chat(req: ChatRequest, request: Request) -> StreamingResponse:
    history = [m.model_dump() for m in req.messages]
    oidc = request.headers.get("x-vercel-oidc-token")  # Vercel's per-request identity
    allowed = guards.allow(guards.client_ip(request.headers))

    async def events():
        if not allowed:
            yield sse("error", {"message": "You're sending messages quickly. Please wait a "
                                "minute, or reach the team at hello@gocadre.ai."})
            return
        too_long = any(m["role"] == "user" and len(m["content"]) > config.MAX_MESSAGE_CHARS
                       for m in history)
        if history[-1]["role"] != "user" or too_long:
            yield sse("error", {"message": "Please keep messages under 1,000 characters."})
            return
        async for event, data in run_turn(req.session_id, history, oidc):
            yield sse(event, data)

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
def lead(req: LeadRequest, request: Request) -> dict:
    """DEMO handoff form (Brian's decision): validates like a real form, sends nothing,
    stores nothing, and says so. A repeat submit with the same key returns the same
    result instead of creating a second request (research findings #10)."""
    if not guards.allow(guards.client_ip(request.headers)):
        return {"ok": False, "field": None, "message": "Please wait a minute and try again."}
    if not EMAIL_OK.match(req.email.strip()):
        return {"ok": False, "field": "email", "message": "Enter a valid email address."}
    duplicate = req.idempotency_key in _seen_leads
    if len(_seen_leads) > 5000:  # keep memory bounded
        _seen_leads.clear()
    _seen_leads.add(req.idempotency_key)
    first = (req.name.split() or ["there"])[0]
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


# Local dev only (Vercel serves public/ itself; check_dir=False so a missing folder can't crash it)
app.mount("/vendor", StaticFiles(directory=config.ROOT / "public" / "vendor", check_dir=False),
          name="vendor")


@app.get("/render.js")
def render_js() -> FileResponse:
    """Local dev only (Vercel serves public/ itself): the widget's safe-rendering code."""
    return FileResponse(config.ROOT / "public" / "render.js", media_type="text/javascript")


@app.get("/privacy.html")
def privacy() -> FileResponse:
    """What chat data we store (research findings #8)."""
    return FileResponse(config.ROOT / "public" / "privacy.html")
