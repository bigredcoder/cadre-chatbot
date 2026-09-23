"""router.py: Jev confident / unsure / down, fallback, and handoff rules. No network."""
import asyncio

import httpx

from app import config, router


def _run(coro):
    return asyncio.run(coro)


HISTORY = [{"role": "user", "content": "How much does it cost?"}]


def _jev(topic, p, asks_p=0.1):
    async def fake(history, token):
        return {"topic": {"choice": topic, "probabilities": {topic: p}},
                "asks_for_human": {"probability": asks_p}}
    return fake


def test_confident_jev_is_used(monkeypatch):
    monkeypatch.setattr(router, "_ask_jev", _jev("industries", 0.98))
    r = _run(router.route(HISTORY, "tok"))
    assert (r.topic, r.router, r.handoff) == ("industries", "jev", False)


def test_pricing_always_offers_a_person(monkeypatch):
    monkeypatch.setattr(router, "_ask_jev", _jev("pricing", 0.99))
    assert _run(router.route(HISTORY, "tok")).handoff is True


def test_explicit_request_for_a_person_hands_off(monkeypatch):
    monkeypatch.setattr(router, "_ask_jev", _jev("services", 0.9, asks_p=0.95))
    r = _run(router.route(HISTORY, "tok"))
    assert r.asks_for_human and r.handoff


def test_unsure_jev_falls_back_to_model(monkeypatch):
    monkeypatch.setattr(router, "_ask_jev", _jev("services", 0.4))

    async def model(history):
        return "portal", False
    monkeypatch.setattr(router, "_ask_model", model)
    r = _run(router.route(HISTORY, "tok"))
    assert (r.topic, r.router) == ("portal", "fallback") and "unsure" in r.note


def test_jev_down_falls_back_to_model(monkeypatch):
    async def down(history, token):
        raise httpx.ConnectError("no route")

    async def model(history):
        return "pricing", False
    monkeypatch.setattr(router, "_ask_jev", down)
    monkeypatch.setattr(router, "_ask_model", model)
    r = _run(router.route(HISTORY, "tok"))
    assert r.router == "fallback" and r.handoff and "unavailable" in r.note


def test_everything_down_still_returns_a_route(monkeypatch):
    async def down(*a):
        raise httpx.ConnectError("no route")
    monkeypatch.setattr(router, "_ask_jev", down)
    monkeypatch.setattr(router, "_ask_model", down)
    r = _run(router.route(HISTORY, "tok"))
    assert r.router == "default" and r.topic in config.TOPICS


def test_no_credential_skips_jev(monkeypatch):
    monkeypatch.setattr(config, "gateway_token", lambda t=None: None)

    async def model(history):
        return "services", False
    monkeypatch.setattr(router, "_ask_model", model)
    r = _run(router.route(HISTORY, None))
    assert r.router == "fallback" and "no gateway credential" in r.note


def test_follow_up_state_includes_previous_message():
    state = router._state([{"role": "user", "content": "Do you do AI agents?"},
                           {"role": "assistant", "content": "Yes."},
                           {"role": "user", "content": "how much?"}])
    assert "Do you do AI agents?" in state and "how much?" in state
