"""Saves one redacted row per chat turn to Supabase, for quality review.

- Emails and phone numbers are removed BEFORE anything leaves the app.
- Rows are deleted after 30 days by a nightly job in the database.
- The app's key can only insert: it can't read conversations back.
- Saving never breaks or slows a chat: failures are logged and swallowed.
"""
import logging
import re

import httpx

from app import config

log = logging.getLogger("cadence.transcripts")

EMAIL = re.compile(r"[\w.+-]+@[\w-]+(\.[\w-]+)+")
# 10+ digit phone-like runs, with optional +, spaces, dots, dashes, parentheses
PHONE = re.compile(r"(?<![\w(])\+?\(?\d[\d\s().-]{8,}\d(?!\w)")
KEEP_EMAILS = {"hello@gocadre.ai"}   # Cadre's own published contact details
KEEP_PHONE_DIGITS = {"6193243223"}


def redact(text: str | None) -> str | None:
    """Replace personal emails and phone numbers; keep Cadre's published contact info."""
    if text is None:
        return None

    def email(m: re.Match) -> str:
        return m.group(0) if m.group(0).lower() in KEEP_EMAILS else "[email removed]"

    def phone(m: re.Match) -> str:
        digits = re.sub(r"\D", "", m.group(0))[-10:]
        return m.group(0) if digits in KEEP_PHONE_DIGITS else "[phone removed]"

    return PHONE.sub(phone, EMAIL.sub(email, text))


async def save_turn(row: dict) -> bool:
    """Insert one turn. Returns True if saved. Never raises."""
    row = {**row, "user_message": redact(row.get("user_message")),
           "assistant_message": redact(row.get("assistant_message"))}
    try:
        async with httpx.AsyncClient(timeout=config.SAVE_TIMEOUT_S) as client:
            resp = await client.post(
                f"{config.SUPABASE_URL}/rest/v1/chat_turns",
                json=row,
                headers={
                    "apikey": config.SUPABASE_PUBLISHABLE_KEY,
                    "Authorization": f"Bearer {config.SUPABASE_PUBLISHABLE_KEY}",
                    "Prefer": "return=minimal",
                },
            )
        if resp.status_code >= 300:
            log.warning("transcript save failed: HTTP %s", resp.status_code)
            return False
        return True
    except httpx.HTTPError as err:
        log.warning("transcript save failed: %s", type(err).__name__)
        return False
