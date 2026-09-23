"""guards.py: per-IP rate limits."""
from fastapi.testclient import TestClient

from app import config, guards, main


def setup_function():
    guards.reset()


def test_minute_limit_blocks_then_recovers():
    for i in range(config.RATE_LIMIT_PER_MINUTE):
        assert guards.allow("1.2.3.4", now=1000 + i)
    assert not guards.allow("1.2.3.4", now=1030)
    assert guards.allow("1.2.3.4", now=1000 + 61 + config.RATE_LIMIT_PER_MINUTE)


def test_limits_are_per_ip():
    for i in range(config.RATE_LIMIT_PER_MINUTE):
        guards.allow("1.1.1.1", now=2000 + i)
    assert guards.allow("2.2.2.2", now=2005)


def test_client_ip_uses_first_forwarded_address():
    assert guards.client_ip({"x-forwarded-for": "9.9.9.9, 10.0.0.1"}) == "9.9.9.9"
    assert guards.client_ip({}) == "unknown"


def test_chat_returns_friendly_message_when_limited(monkeypatch):
    monkeypatch.setattr(guards, "allow", lambda ip, now=None: False)
    body = TestClient(main.app).post("/api/chat", json={
        "session_id": "test-session-1", "messages": [{"role": "user", "content": "hi"}]}).text
    assert "event: error" in body and "hello@gocadre.ai" in body
