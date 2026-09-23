from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_ok_and_never_reveals_key_values():
    body = client.get("/api/health").json()
    assert body["status"] == "ok"
    assert isinstance(body["openrouter_key"], bool)  # present or not, never the value


def test_home_and_privacy_pages_serve():
    assert "Cadence" in client.get("/").text
    assert "How chat data is used" in client.get("/privacy").text
