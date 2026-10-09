from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_ok_and_never_reveals_key_values():
    body = client.get("/api/health").json()
    assert body["status"] == "ok"
    assert isinstance(body["openrouter_key"], bool)  # present or not, never the value


def test_home_and_privacy_pages_serve():
    assert "Cadence" in client.get("/").text
    assert "How chat data is used" in client.get("/privacy.html").text


def test_health_reports_public_storage_target_without_storage_key(monkeypatch):
    from app import config

    monkeypatch.setattr(config, "SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setattr(config, "SUPABASE_SCHEMA", "cadre_chatbot")
    monkeypatch.setattr(config, "SUPABASE_PUBLISHABLE_KEY", "test-private-sentinel")
    monkeypatch.setattr(config, "SAVE_TURNS", True)
    response = client.get("/api/health")
    assert response.json()["storage"] == {
        "enabled": True, "url": "https://example.supabase.co", "schema": "cadre_chatbot"
    }
    assert "test-private-sentinel" not in response.text
