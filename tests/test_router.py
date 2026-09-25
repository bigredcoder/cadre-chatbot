"""router.py: Jev confident / unsure / down, fallback, and handoff rules. No network."""
import asyncio

import httpx

from app import config, router


def _run(coro):
    return asyncio.run(coro)


HISTORY = [{"role": "user", "content": "How much does it cost?"}]


def _jev(topic, p, asks_p=0.1):
    async def fake(history, token):
        return ({"topic": {"choice": topic, "probabilities": {topic: p}},
                 "asks_for_human": {"probability": asks_p}}, 0.00001)
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
        return "portal", False, 0.0001
    monkeypatch.setattr(router, "_ask_model", model)
    r = _run(router.route(HISTORY, "tok"))
    assert (r.topic, r.router) == ("portal", "fallback") and "unsure" in r.note


def test_jev_down_falls_back_to_model(monkeypatch):
    async def down(history, token):
        raise httpx.ConnectError("no route")

    async def model(history):
        return "pricing", False, 0.0001
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
        return "services", False, 0.0001
    monkeypatch.setattr(router, "_ask_model", model)
    r = _run(router.route(HISTORY, None))
    assert r.router == "fallback" and "no gateway credential" in r.note


def test_follow_up_state_includes_previous_message():
    state = router._state([{"role": "user", "content": "Do you do AI agents?"},
                           {"role": "assistant", "content": "Yes."},
                           {"role": "user", "content": "how much?"}])
    assert "Do you do AI agents?" in state and "how much?" in state


def test_jev_rate_limit_is_retried_once(monkeypatch):
    calls = {"n": 0}

    def handler(request):
        calls["n"] += 1
        if calls["n"] == 1:
            return httpx.Response(429)
        return httpx.Response(200, json={"answers": {
            "topic": {"choice": "industries", "probabilities": {"industries": 0.99}},
            "asks_for_human": {"probability": 0.1}}})
    real = httpx.AsyncClient
    monkeypatch.setattr(router.httpx, "AsyncClient",
                        lambda **kw: real(transport=httpx.MockTransport(handler), **kw))
    monkeypatch.setattr(config, "JEV_RETRY_DELAY_S", 0)
    r = _run(router.route(HISTORY, "tok"))
    assert calls["n"] == 2 and r.router == "jev" and r.topic == "industries"


def test_odd_responses_never_crash_routing(monkeypatch):
    # Audit 09-25: route() promised "never raises", but a malformed Jev answer (probabilities
    # as a list → AttributeError) or an empty model reply (choices [] → IndexError) escaped.
    async def odd_jev(history, token):
        return ({"topic": {"choice": "pricing", "probabilities": ["not", "a", "dict"]},
                 "asks_for_human": {"probability": 0.1}}, 0.0)

    async def empty_model(history):
        raise IndexError("list index out of range")   # like an empty "choices" list
    monkeypatch.setattr(router, "_ask_jev", odd_jev)
    monkeypatch.setattr(router, "_ask_model", empty_model)
    r = _run(router.route(HISTORY, "tok"))
    assert (r.topic, r.router) == ("services", "default")
    assert "AttributeError" in r.note and "IndexError" in r.note
