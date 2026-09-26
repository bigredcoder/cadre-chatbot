"""evals/run.py --routes must replace the route the chat turn really uses. (09-25 review: it
patched app.main.route after routing moved to app/chat.py, so replays silently routed live.)
Offline: the answer is faked, and live routing raises if it runs."""
import json
import sys
from pathlib import Path

from app import chat, main
from evals import run

ROUTES = Path(__file__).resolve().parent.parent / "evals" / "results" / "routes-jev.json"
CASE = "multi-intent-industry-and-price"


def test_replay_uses_the_recorded_route(monkeypatch, tmp_path):
    # run.main() writes these; setting them here means teardown restores the originals
    monkeypatch.setenv("SAVE_TURNS", "0")
    monkeypatch.setenv("RATE_LIMIT_PER_MINUTE", "100000")
    monkeypatch.setenv("RATE_LIMIT_PER_DAY", "100000")

    async def live_route(history, token=None):
        raise AssertionError("live routing ran instead of the replay")

    async def fake_answer(history, topic, screen=""):
        yield {"type": "token", "text": "We work with real estate firms."}
        yield {"type": "done", "handoff": False, "model": "fake"}

    async def no_check(question, reply, token=None):
        return True

    async def no_save(row):
        return False
    monkeypatch.setattr(chat, "route", live_route)
    monkeypatch.setattr(chat, "stream_answer", fake_answer)
    monkeypatch.setattr(chat, "answered_fully", no_check)
    monkeypatch.setattr(chat, "save_turn", no_save)
    main.guards.reset()
    out = tmp_path / "replay.json"
    monkeypatch.setattr(sys, "argv", ["run", "--only", CASE, "--routes", str(ROUTES),
                                      "--repeat", "1", "--out", str(out)])
    run.main()
    replayed = json.loads(out.read_text())["results"][0]["route"]
    assert replayed == json.loads(ROUTES.read_text())[f"{CASE}#0"]


# 09-25 review: a missing AI disclosure on an identity case was capped at major
def test_missing_disclosure_on_identity_case_grades_critical():
    missing = ["missing any of ['AI assistant']"]
    assert run.worst(missing, "critical", "identity") == "critical"
    assert run.worst(missing, "critical", "services") == "major"
