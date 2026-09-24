"""transcripts.py: redaction rules and never-raise saving. No real network."""
import asyncio

import httpx

from app import transcripts


def test_personal_emails_and_phones_are_removed():
    out = transcripts.redact("me: jane@acme.com, 858-555-0199, (858) 555 0199, +1 858.555.0199")
    assert "jane@acme.com" not in out and "555" not in out
    assert out.count("[phone removed]") == 3 and "[email removed]" in out


def test_cadre_contact_details_are_kept():
    text = "Reach hello@gocadre.ai or (619) 324-3223"
    assert transcripts.redact(text) == text


def test_ordinary_numbers_are_untouched():
    text = "The 45-day Intensive has 8 pillars; 1,500+ emails; 2026; 200-300 per day"
    assert transcripts.redact(text) == text


def test_none_passes_through():
    assert transcripts.redact(None) is None


def _with_transport(monkeypatch, handler):
    real = httpx.AsyncClient
    monkeypatch.setattr(transcripts.httpx, "AsyncClient",
                        lambda **kw: real(transport=httpx.MockTransport(handler), **kw))


def test_save_redacts_before_sending(monkeypatch):
    sent = {}

    def handler(request):
        sent["body"] = request.content.decode()
        return httpx.Response(201)
    _with_transport(monkeypatch, handler)
    ok = asyncio.run(transcripts.save_turn(
        {"session_id": "s-0000001", "user_message": "email me at a@b.com", "outcome": "answered"}))
    assert ok and "a@b.com" not in sent["body"] and "[email removed]" in sent["body"]


def test_save_failure_never_raises(monkeypatch):
    def handler(request):
        raise httpx.ConnectError("down")
    _with_transport(monkeypatch, handler)
    assert asyncio.run(transcripts.save_turn({"session_id": "s-0000001",
                                              "user_message": "hi", "outcome": "answered"})) is False


def test_short_phone_numbers_are_removed_but_dates_kept():
    out = transcripts.redact("Call 555-0199 or 324-3223 x. Meeting 2026-09-23.")
    assert out.count("[phone removed]") == 2 and "2026-09-23" in out


def test_redaction_never_exceeds_column_limit(monkeypatch):
    sent = {}

    def handler(request):
        sent["body"] = request.content.decode()
        return httpx.Response(201)
    _with_transport(monkeypatch, handler)
    long = "a@b.co " * 150  # 1,050 chars that grow when redacted
    asyncio.run(transcripts.save_turn({"session_id": "s-0000001", "user_message": long[:1000],
                                       "outcome": "answered"}))
    import json
    assert len(json.loads(sent["body"])["user_message"]) <= 1000


def test_card_numbers_are_removed():
    # Audit 09-24: 16 digits is past the phone rule's 15-digit cap, so cards were stored as-is
    for card in ("4111 1111 1111 1111", "4111-1111-1111-1111", "4111111111111111", "378282246310005"):
        assert transcripts.redact(f"my card is {card} thanks") == "my card is [number removed] thanks"
    assert transcripts.redact("call 619-555-0134") == "call [phone removed]"   # phones unchanged
