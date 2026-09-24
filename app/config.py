"""Every model name, limit, and threshold in one place. No magic numbers elsewhere."""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent  # Vercel runs from the project root


def _load_dotenv() -> None:
    """Local dev only: read .env and .env.local into the environment without overriding
    real env vars. On Vercel, keys come from the project's environment settings instead.
    (.env.local holds the short-lived VERCEL_OIDC_TOKEN from `vercel link`.)"""
    for name in (".env", ".env.local"):
        path = ROOT / name
        if not path.exists():
            continue
        for line in path.read_text().splitlines():
            if "=" in line and not line.lstrip().startswith("#"):
                key, value = line.split("=", 1)
                if value.strip():
                    os.environ.setdefault(key.strip(), value.strip().strip('"'))


_load_dotenv()

# --- Answer model (OpenRouter) ---
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
# Chosen 2026-09-23 from an 11-model eval comparison (plan.md §5, "Why this model"):
# 52/52 with zero critical or major failures, and the fastest of the three perfect models.
ANSWER_MODEL = os.environ.get("ANSWER_MODEL", "google/gemini-2.5-flash")
ANSWER_MAX_TOKENS = 500      # hard cap per reply: keeps answers short and spend bounded
ANSWER_TEMPERATURE = 0.2     # low: we want consistent, grounded answers, not creativity
ANSWER_TIMEOUT_S = 15         # longest wait for the next piece of the answer
ANSWER_DEADLINE_S = 25        # whole answer; past this the visitor gets the fallback
# Deadlines per turn stage (audit 09-24: without them a hung provider meant 80s+ of waiting).
# Worst case now: route 10 + answer 25 + answer check 4 = 39s, then the fallback message.
ROUTE_DEADLINE_S = 10
ANSWER_CHECK_DEADLINE_S = 4

# --- Conversation limits (research findings #17) ---
MAX_MESSAGE_CHARS = 1000     # a single visitor message
MAX_HISTORY_MESSAGES = 8     # only the recent turns are sent to the model
# Per visitor IP. ESTIMATE: well above human typing speed. Evals raise these (one "visitor").
RATE_LIMIT_PER_MINUTE = int(os.environ.get("RATE_LIMIT_PER_MINUTE", "12"))
RATE_LIMIT_PER_DAY = int(os.environ.get("RATE_LIMIT_PER_DAY", "200"))

# --- Routing (Jev via Vercel AI Gateway) ---
JEV_URL = "https://ai-gateway.vercel.sh/v1/evaluate"
JEV_MODEL = "typesafe-ai/jev"
JEV_TIMEOUT_S = 6
JEV_RETRY_DELAY_S = 0.3   # one retry on 429/503 (measured 09-23: Jev rate-limits under load)
# Below this, Jev's topic isn't trusted and the chat model classifies instead.
# ESTIMATE: 0.6 is a starting point; Phase 6 evals tune it (research findings: validate
# confidence against labeled outcomes before trusting it as a threshold).
ROUTE_MIN_CONFIDENCE = 0.6
HUMAN_REQUEST_THRESHOLD = 0.7    # Jev's "explicitly asking for a person?" probability
ANSWERED_THRESHOLD = 0.7         # Jev's "did the reply fully answer it?" (ESTIMATE; evals tune)
OFF_TOPIC_CANNED_CONFIDENCE = 0.9  # this sure it's off-topic → canned reply, no model call

TOPICS = {  # key: description Jev uses to decide
    "services": "what Cadre does, its services, how an engagement works",
    "industries": "whether Cadre works with a specific industry or type of company",
    "booking": "booking a call, contacting Cadre, or talking to a strategist",
    "portal": "the Cadre client portal, logging in, accounts",
    "maturity_index": "the AI Maturity Index, pillars, or getting scored",
    "llm_security": "which AI models Cadre uses, data security, privacy, compliance",
    "pricing": "cost, pricing, budget, fees, how much something costs",
    "results": "case studies, results, examples of past work",
    "company": "who Cadre is, leadership, location, partners",
    "off_topic": "anything unrelated to Cadre AI or AI for business",
}
# "jev" (normal) or "model_only" (benchmark: skip Jev, the chat model routes everything)
ROUTER_MODE = os.environ.get("ROUTER_MODE", "jev")

# Topics where a person is always offered (plan.md: pricing is never quoted;
# booking's answer IS the handoff form).
HANDOFF_TOPICS = {"pricing", "booking"}

# --- Handoff ---
HANDOFF_TAG = "[HANDOFF]"    # the model ends a reply with this; the code shows the form

# --- Conversation storage (Supabase project "cadre-chatbot") ---
# The publishable key is public by design (like any website's analytics key). The table's
# row-level security lets it INSERT only: it can't read, change, or delete anything.
# Review conversations in the Supabase dashboard, never through the app.
SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://juvxbhiwpdbxfxgtaxcg.supabase.co")
SUPABASE_PUBLISHABLE_KEY = os.environ.get(
    "SUPABASE_PUBLISHABLE_KEY", "sb_publishable_ZvU8JpnOjhQqb6IlLiGlZw_6KF0nQvs"
)
SAVE_TURNS = os.environ.get("SAVE_TURNS", "1") != "0"   # evals set 0: tests aren't visitors
SAVE_TIMEOUT_S = 3            # saving must never slow the visitor down
RETENTION_DAYS = 30           # enforced by a nightly pg_cron job in the database

# --- Links the UI may render (research findings #7) ---
ALLOWED_LINK_HOSTS = ("cadre.ai", "www.cadre.ai", "portal.gocadre.ai")
CONTACT_EMAIL = "hello@gocadre.ai"

# --- Files ---
SYSTEM_PROMPT_PATH = ROOT / "prompts" / "system.md"
KNOWLEDGE_PATH = ROOT / "knowledge" / "cadre.md"


def openrouter_key() -> str | None:
    return os.environ.get("OPENROUTER_API_KEY") or None


def gateway_token(request_token: str | None = None) -> str | None:
    """AI Gateway credential: an explicit API key wins; on Vercel, the per-request OIDC
    token; locally, the OIDC token from .env.local."""
    return (os.environ.get("AI_GATEWAY_API_KEY") or request_token
            or os.environ.get("VERCEL_OIDC_TOKEN") or None)
