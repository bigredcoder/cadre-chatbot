from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_ok():
    assert client.get("/api/health").json() == {"status": "ok"}


def test_home_serves_page():
    resp = client.get("/")
    assert resp.status_code == 200
    assert "Cadence" in resp.text
