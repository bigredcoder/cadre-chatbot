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
from collections.abc import AsyncIterator

import httpx

from app import config


class AnswerError(Exception):
    """The model couldn't produce a usable answer. The caller shows a friendly fallback."""


def build_system_prompt(topic: str) -> str:
    """System prompt with the knowledge and the router's topic filled in."""
    template = config.SYSTEM_PROMPT_PATH.read_text()
    template = re.sub(r"<!--.*?-->", "", template, flags=re.DOTALL).strip()  # drop owner notes
    return template.replace("{{KNOWLEDGE}}", config.KNOWLEDGE_PATH.read_text()).replace(
        "{{TOPIC}}", topic
    )


def build_messages(history: list[dict], topic: str) -> list[dict]:
    """System prompt + only the most recent turns (keeps cost and context bounded)."""
    recent = history[-config.MAX_HISTORY_MESSAGES :]
    return [{"role": "system", "content": build_system_prompt(topic)}, *recent]


def _visible(text: str) -> str:
    """Text safe to show so far: tag removed, and any half-arrived tag held back."""
    clean = text.replace(config.HANDOFF_TAG, "")
    for n in range(len(config.HANDOFF_TAG) - 1, 0, -1):
        if clean.endswith(config.HANDOFF_TAG[:n]):
            return clean[:-n]
    return clean


async def stream_answer(history: list[dict], topic: str) -> AsyncIterator[dict]:
    """Yield {"type": "token", "text": ...} chunks, then one {"type": "done", ...} summary."""
    key = config.openrouter_key()
    if not key:
        raise AnswerError("OPENROUTER_API_KEY is not configured")

    body = {
        "model": config.ANSWER_MODEL,
        "messages": build_messages(history, topic),
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
                if time.monotonic() - started > config.ANSWER_DEADLINE_S:
                    raise AnswerError("answer took too long")
                chunk = json.loads(line[6:])
                if "error" in chunk:
                    raise AnswerError(str(chunk["error"].get("message", "model error")))
                usage = chunk.get("usage") or usage
                for choice in chunk.get("choices", []):
                    full += (choice.get("delta") or {}).get("content") or ""
                visible = _visible(full)
                if len(visible) > sent:
                    yield {"type": "token", "text": visible[sent:]}
                    sent = len(visible)
    except httpx.HTTPError as err:
        raise AnswerError(f"network error: {type(err).__name__}") from err

    final = full.replace(config.HANDOFF_TAG, "").rstrip()
    if not final.strip():
        raise AnswerError("empty reply from model")
    if len(final) > sent:
        yield {"type": "token", "text": final[sent:]}

    yield {
        "type": "done",
        "handoff": config.HANDOFF_TAG in full,
        "model": config.ANSWER_MODEL,
        "latency_ms": int((time.monotonic() - started) * 1000),
        "input_tokens": usage.get("prompt_tokens"),
        "output_tokens": usage.get("completion_tokens"),
        "cost_usd": usage.get("cost"),
    }
