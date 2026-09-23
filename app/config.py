"""Every model name, limit, and threshold in one place. No magic numbers elsewhere."""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent  # Vercel runs from the project root


def _load_dotenv() -> None:
    """Local dev only: read .env into the environment without overriding real env vars.
    On Vercel, keys come from the project's environment settings instead."""
    path = ROOT / ".env"
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        if "=" in line and not line.lstrip().startswith("#"):
            key, value = line.split("=", 1)
            if value.strip():
                os.environ.setdefault(key.strip(), value.strip().strip('"'))


_load_dotenv()

# --- Answer model (OpenRouter) ---
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
# Provisional pick from the Phase 1 spike (answered correctly, cheapest).
# Phase 6 replaces this with a model chosen by the eval comparison.
ANSWER_MODEL = os.environ.get("ANSWER_MODEL", "google/gemini-2.5-flash-lite")
ANSWER_MAX_TOKENS = 500      # hard cap per reply: keeps answers short and spend bounded
ANSWER_TEMPERATURE = 0.2     # low: we want consistent, grounded answers, not creativity
ANSWER_TIMEOUT_S = 30

# --- Conversation limits (research findings #17) ---
MAX_MESSAGE_CHARS = 1000     # a single visitor message
MAX_HISTORY_MESSAGES = 8     # only the recent turns are sent to the model
MAX_TURNS_PER_SESSION = 30   # beyond this, point them to a person

# --- Handoff ---
HANDOFF_TAG = "[HANDOFF]"    # the model ends a reply with this; the code shows the form

# --- Links the UI may render (research findings #7) ---
ALLOWED_LINK_HOSTS = ("cadre.ai", "www.cadre.ai", "portal.gocadre.ai")
CONTACT_EMAIL = "hello@gocadre.ai"

# --- Files ---
SYSTEM_PROMPT_PATH = ROOT / "prompts" / "system.md"
KNOWLEDGE_PATH = ROOT / "knowledge" / "cadre.md"


def openrouter_key() -> str | None:
    return os.environ.get("OPENROUTER_API_KEY") or None
