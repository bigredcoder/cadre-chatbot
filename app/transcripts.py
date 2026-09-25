"""Saves one redacted row per chat turn to Supabase, for quality review.

- Emails, phone numbers and card-like numbers are removed BEFORE anything leaves the app
  (chat.py uses the same redact() before any model call).
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
# Phone-like runs (optional +, spaces, dots, dashes, parentheses); judged by digit count below
PHONE = re.compile(r"(?<![\w(])\+?\(?\d[\d\s().-]{5,}\d(?!\w)")
ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
# Card-like numbers: 13-19 digits, optionally grouped by spaces or dashes (audit 09-24: a
# 16-digit card slipped past the phone rule, which stops at 15 digits)
CARD = re.compile(r"(?<!\d)\d(?:[ -]?\d){12,18}(?!\d)")
KEEP_EMAILS = {"hello@gocadre.ai"}   # Cadre's own published contact details
KEEP_PHONE_DIGITS = {"6193243223"}


def _phone_shaped(text: str, digits: str) -> bool:
    """True if a digit run is grouped the way phone numbers are (/ship review, 09-24: digit count
    alone turned a budget of "25000-50000" into "[phone removed]" before it reached the model).
    - grouped by spaces, dots, dashes or parentheses: every group is 1-4 digits
      ("858-555-0199", "+44 20 7946 0958" yes; "25000-50000" no)
    - one bare run of digits: 10 or more ("6195550134" yes; "1200000" no)
    """
    groups = [g for g in re.split(r"\D+", text) if g]
    if len(groups) > 1:
        return all(len(g) <= 4 for g in groups)
    return len(digits) >= 10


def redact(text: str | None) -> str | None:
    """Replace personal emails, card-like numbers, and phone numbers; keep Cadre's contact info."""
    if text is None:
        return None

    def email(m: re.Match) -> str:
        return m.group(0) if m.group(0).lower() in KEEP_EMAILS else "[email removed]"

    def phone(m: re.Match) -> str:
        text, digits = m.group(0), re.sub(r"\D", "", m.group(0))
        if (len(digits) < 7 or len(digits) > 15 or ISO_DATE.match(text.strip())
                or not _phone_shaped(text, digits)):
            return text                      # too short/long, a date, or not shaped like a phone
        return text if digits[-10:] in KEEP_PHONE_DIGITS else "[phone removed]"

    return PHONE.sub(phone, CARD.sub("[number removed]", EMAIL.sub(email, text)))


async def save_turn(row: dict) -> bool:
    """Insert one turn. Returns True if saved. Never raises."""
    if not config.SAVE_TURNS:
        return False
    # Redaction can lengthen text ("a@b.co" → "[email removed]"): re-cap to the column limits
    user, reply = redact(row.get("user_message")), redact(row.get("assistant_message"))
    row = {**row, "user_message": user[:1000] if user else user,
           "assistant_message": reply[:8000] if reply else reply}
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
    except Exception:  # deliberate: saving must never break a chat (audit 09-25: only network
        # errors were caught, so any other failure escaped after the answer was already sent)
        log.warning("transcript save failed", exc_info=True)
        return False
