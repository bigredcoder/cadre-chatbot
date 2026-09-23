"""answer.py: prompt assembly, handoff-tag stripping, and streaming. No real network calls."""
import asyncio
import json

import httpx
import pytest

from app import answer, config


def test_system_prompt_fills_knowledge_and_topic_and_drops_owner_notes():
    prompt = answer.build_system_prompt("pricing")
    assert "{{KNOWLEDGE}}" not in prompt and "{{TOPIC}}" not in prompt
    assert "hello@gocadre.ai" in prompt           # knowledge was inserted
    assert "classified as: pricing" in prompt      # topic was inserted
    assert "OWNER: Brian" not in prompt            # HTML comment header removed


def test_history_is_trimmed_to_recent_turns():
    history = [{"role": "user", "content": f"m{i}"} for i in range(20)]
    msgs = answer.build_messages(history, "unknown")
    assert msgs[0]["role"] == "system"
    assert len(msgs) == 1 + config.MAX_HISTORY_MESSAGES
    assert msgs[-1]["content"] == "m19"


@pytest.mark.parametrize("text,shown", [
    ("Hello", "Hello"),
    ("Hello [HAND", "Hello "),            # half-arrived tag is held back
    ("Hello [HANDOFF]", "Hello "),        # full tag removed
    ("Price [", "Price "),
])
def test_visible_never_shows_the_handoff_tag(text, shown):
    assert answer._visible(text) == shown


def _fake_openrouter(chunks, status=200):
    """An httpx transport that replays OpenRouter-style streaming lines."""
    def handler(request):
        lines = [": OPENROUTER PROCESSING"]
        lines += [f"data: {json.dumps({'choices': [{'delta': {'content': c}}]})}" for c in chunks]
        lines += [f"data: {json.dumps({'choices': [], 'usage': {'prompt_tokens': 10, 'completion_tokens': 5, 'cost': 0.0001}})}",
                  "data: [DONE]"]
        return httpx.Response(status, text="\n".join(lines) + "\n")
    return httpx.MockTransport(handler)


def _run(monkeypatch, chunks, status=200):
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    transport = _fake_openrouter(chunks, status)
    real = httpx.AsyncClient
    monkeypatch.setattr(answer.httpx, "AsyncClient", lambda **kw: real(transport=transport, **kw))

    async def collect():
        return [ev async for ev in answer.stream_answer([{"role": "user", "content": "hi"}], "x")]
    return asyncio.run(collect())


def test_stream_strips_tag_and_flags_handoff(monkeypatch):
    events = _run(monkeypatch, ["Pricing depends on ", "the engagement.\n[HAND", "OFF]"])
    text = "".join(e["text"] for e in events if e["type"] == "token")
    done = events[-1]
    assert "[HANDOFF]" not in text and "[HAND" not in text
    assert text.strip() == "Pricing depends on the engagement."
    assert done["handoff"] is True and done["cost_usd"] == 0.0001


def test_empty_reply_is_an_error_not_a_blank_bubble(monkeypatch):
    with pytest.raises(answer.AnswerError):
        _run(monkeypatch, ["", "  "])


def test_http_error_becomes_answer_error(monkeypatch):
    with pytest.raises(answer.AnswerError):
        _run(monkeypatch, ["x"], status=500)


def test_missing_key_is_an_answer_error(monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    async def go():
        return [e async for e in answer.stream_answer([{"role": "user", "content": "hi"}], "x")]
    with pytest.raises(answer.AnswerError):
        asyncio.run(go())
