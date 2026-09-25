"""Builds the prompt, calls the answer model on OpenRouter, and streams the reply.

Flow: system prompt (prompts/system.md) + Cadre knowledge (knowledge/cadre.md)
      + recent conversation → OpenRouter (streaming) → text chunks for the browser.

Two safety details live here, not in the browser:
- The [HANDOFF] tag is stripped server-side, so a half-typed tag never flashes on
  screen (research findings #5). The caller gets handoff=True instead.
- An empty reply is an error, never a blank bubble (CLAUDE.md rule 7).
"""
import json
import re
import time
from collections.abc import AsyncGenerator

import httpx

from app import config

# The tag in any capitalization or spacing (audit 09-25: only exact "[HANDOFF]" was caught,
# so "[Handoff]" would have shown on screen and lost the offer)
TAG = re.compile(r"\[\s*handoff\s*\]", re.IGNORECASE)


class AnswerError(Exception):
    """The model couldn't produce a usable answer. The caller shows a friendly fallback."""


def build_system_prompt(topic: str, screen: str = "") -> str:
    """System prompt with the knowledge, the router's topic, and what the widget will show."""
    template = config.SYSTEM_PROMPT_PATH.read_text()
    template = re.sub(r"<!--.*?-->", "", template, flags=re.DOTALL).strip()  # drop owner notes
    return (template.replace("{{KNOWLEDGE}}", config.KNOWLEDGE_PATH.read_text())
            .replace("{{TOPIC}}", topic).replace("{{SCREEN}}", screen or "Nothing extra."))


def build_messages(history: list[dict], topic: str, screen: str = "") -> list[dict]:
    """System prompt + only the most recent turns (keeps cost and context bounded)."""
    recent = history[-config.MAX_HISTORY_MESSAGES :]
    return [{"role": "system", "content": build_system_prompt(topic, screen)}, *recent]


def _visible(text: str) -> str:
    """Text safe to show so far: tag removed, and any half-arrived tag held back."""
    clean = TAG.sub("", text)
    start = clean.rfind("[")
    if start != -1:
        tail = clean[start:].replace(" ", "").lower()
        if "[handoff]".startswith(tail):   # "[", "[Hand", "[ handof": may still become the tag
            return clean[:start]
    return clean


async def stream_answer(history: list[dict], topic: str, screen: str = "") -> AsyncGenerator[dict, None]:
    """Yield {"type": "token", "text": ...} chunks, then one {"type": "done", ...} summary."""
    key = config.openrouter_key()
    if not key:
        raise AnswerError("OPENROUTER_API_KEY is not configured")

    body = {
        "model": config.ANSWER_MODEL,
        "messages": build_messages(history, topic, screen),
        "max_tokens": config.ANSWER_MAX_TOKENS,
        "temperature": config.ANSWER_TEMPERATURE,
        "stream": True,
        "usage": {"include": True},  # OpenRouter only reports cost when asked
    }
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}

    started = time.monotonic()
    full, sent = "", 0
    usage: dict = {}
    try:
        async with (
            httpx.AsyncClient(timeout=httpx.Timeout(config.ANSWER_TIMEOUT_S, connect=5)) as client,
            client.stream("POST", config.OPENROUTER_URL, json=body, headers=headers) as resp,
        ):
            if resp.status_code != 200:
                raise AnswerError(f"OpenRouter returned HTTP {resp.status_code}")
            async for line in resp.aiter_lines():
                if not line.startswith("data: ") or line == "data: [DONE]":
                    continue  # skips keep-alive comments and the end marker
                try:
                    chunk = json.loads(line[6:])
                except ValueError as err:   # garbled line: a normal "couldn't answer", not a crash
                    raise AnswerError("malformed stream from the provider") from err
                if "error" in chunk:
                    err_info = chunk["error"]
                    message = err_info.get("message") if isinstance(err_info, dict) else err_info
                    raise AnswerError(str(message or "model error"))
                usage = chunk.get("usage") or usage
                for choice in chunk.get("choices", []):
                    full += (choice.get("delta") or {}).get("content") or ""
                visible = _visible(full)
                if len(visible) > sent:
                    yield {"type": "token", "text": visible[sent:]}
                    sent = len(visible)
    except httpx.HTTPError as err:
        raise AnswerError(f"network error: {type(err).__name__}") from err

    final = TAG.sub("", full).rstrip()
    if not final.strip():
        raise AnswerError("empty reply from model")
    if len(final) > sent:
        yield {"type": "token", "text": final[sent:]}

    yield {
        "type": "done",
        "handoff": bool(TAG.search(full)),
        "model": config.ANSWER_MODEL,
        "latency_ms": int((time.monotonic() - started) * 1000),
        "input_tokens": usage.get("prompt_tokens"),
        "output_tokens": usage.get("completion_tokens"),
        "cost_usd": usage.get("cost"),
    }
