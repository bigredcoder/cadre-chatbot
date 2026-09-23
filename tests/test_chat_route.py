"""/api/chat: streaming events, limits, and friendly failure. The model is faked."""
from fastapi.testclient import TestClient

from app import main
from app.answer import AnswerError

client = TestClient(main.app)


def _post(messages):
    return client.post("/api/chat", json={"session_id": "test-session-1", "messages": messages})


def test_streams_route_tokens_and_done(monkeypatch):
    async def fake(history, topic):
        yield {"type": "token", "text": "Yes."}
        yield {"type": "done", "handoff": False, "model": "m"}
    monkeypatch.setattr(main, "stream_answer", fake)
    body = _post([{"role": "user", "content": "Do you work with construction?"}]).text
    assert "event: route" in body and "event: token" in body and "event: done" in body


def test_model_failure_gives_friendly_fallback_with_contact(monkeypatch):
    async def broken(history, topic):
        raise AnswerError("boom")
        yield  # makes this an async generator
    monkeypatch.setattr(main, "stream_answer", broken)
    body = _post([{"role": "user", "content": "hi"}]).text
    assert "event: error" in body and "hello@gocadre.ai" in body and "boom" not in body


def test_overlong_message_is_rejected_politely():
    body = _post([{"role": "user", "content": "x" * 1500}]).text
    assert "event: error" in body and "1,000 characters" in body


def test_bad_request_shape_is_422():
    assert client.post("/api/chat", json={"session_id": "short", "messages": []}).status_code == 422
