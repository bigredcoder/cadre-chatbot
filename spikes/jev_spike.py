"""Phase 1 spike: prove we can call Jev (TypeSafe AI) from Python via Vercel AI Gateway.

Throwaway script. It answers one question before we build on Jev:
does the real request/response match Vercel's docs?
Docs: https://vercel.com/docs/ai-gateway/modalities/evaluation

Auth: AI_GATEWAY_API_KEY from .env, or VERCEL_OIDC_TOKEN from .env.local
(created by `vercel link`, short-lived). Secrets are never printed.
Run: python spikes/jev_spike.py
"""
import json
import pathlib
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
URL = "https://ai-gateway.vercel.sh/v1/evaluate"


def load_env(*names):
    """Read KEY=value lines from the given env files without printing anything."""
    env = {}
    for name in names:
        path = ROOT / name
        if path.exists():
            for line in path.read_text().splitlines():
                if "=" in line and not line.lstrip().startswith("#"):
                    key, value = line.split("=", 1)
                    env[key.strip()] = value.strip().strip('"')
    return env


env = load_env(".env", ".env.local")
token = env.get("AI_GATEWAY_API_KEY") or env.get("VERCEL_OIDC_TOKEN")
if not token:
    raise SystemExit("No AI Gateway credential found in .env or .env.local")
print("auth:", "api key" if env.get("AI_GATEWAY_API_KEY") else "vercel oidc token")

TOPICS = {
    "services": "what Cadre does, its services, how it works",
    "industries": "whether Cadre works with a specific industry",
    "booking": "booking a call or talking to a strategist",
    "portal": "accessing the Cadre client portal",
    "maturity_index": "the AI Maturity Index or getting scored",
    "llm_security": "which AI models Cadre uses, data security, privacy",
    "pricing": "cost, pricing, budget",
    "off_topic": "anything unrelated to Cadre AI",
}

for message in [
    "Do you guys work with construction companies?",
    "How much does an engagement cost?",
    "What's the weather in San Diego?",
]:
    body = {
        "model": "typesafe-ai/jev",
        "state": message,
        "questions": {
            "topic": {
                "type": "choice",
                "instructions": "Which topic is this website visitor's message about?",
                "criteria": TOPICS,
            },
            "needs_human": {
                "type": "boolean",
                "instructions": "Should a human from Cadre's team handle this instead of an FAQ bot?",
            },
        },
    }
    req = urllib.request.Request(
        URL,
        data=json.dumps(body).encode(),
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = json.load(resp)
    except urllib.error.HTTPError as err:
        print("HTTP", err.code, err.read().decode()[:300])
        raise SystemExit(1)
    topic = data["answers"]["topic"]
    human = data["answers"]["needs_human"]
    print(f"\n{message!r}")
    print("  topic:", topic.get("choice"), "| p =", round(topic.get("probabilities", {}).get(topic.get("choice"), 0), 3))
    print("  needs_human p =", round(human.get("probability", 0), 3))
    print("  cost $", data.get("providerMetadata", {}).get("gateway", {}).get("cost"))
