"""Browser tests: drive the real widget like a visitor, on desktop Chromium AND an iPhone
profile in WebKit (Safari's engine). Phone tests fail if anything is wider than the screen.

Runs against a LOCAL server by default. Start one, then run the tests in another shell:
  RATE_LIMIT_PER_MINUTE=1000 SAVE_TURNS=0 .venv/bin/uvicorn app.main:app --port 8000
  .venv/bin/python -m pytest e2e -q
  (RATE_LIMIT_PER_MINUTE: repeated runs from one machine otherwise hit the per-visitor limit,
   12 messages/minute, and answers time out. SAVE_TURNS=0: test turns aren't saved.)
The 5 tests marked `model` call the real model on the server's key (a few cents per run);
`-m "not model"` skips them.
The live site only when you name it (real Jev, real model):
  BASE_URL=https://cadre-chatbot-xi.vercel.app .venv/bin/python -m pytest e2e -q
There, leave a minute between full runs: the suite sends 5 chat messages and the app allows
12 a minute per visitor, so back-to-back runs get "You're sending messages quickly" and the
answer tests time out (seen 09-25; the rate limit working as designed).
Not part of the default `pytest` run (unit tests live in tests/).
The chat window is Deep Chat (a web component); Playwright's CSS locators see inside it.
"""
import os
import re
import warnings
from urllib.parse import urlparse

import httpx
import pytest
from playwright.sync_api import Page, expect

BASE = os.environ.get("BASE_URL", "http://127.0.0.1:8000")
if urlparse(BASE).hostname not in ("127.0.0.1", "localhost"):
    warnings.warn(f"Browser tests are running against {BASE}, not a local server. "
                  "The `model` tests spend real model credit there.", stacklevel=1)
ANSWER = 30_000
INPUT = "deep-chat #text-input"
LAST_ANSWER = "deep-chat .cad-msg >> nth=-1"
NO_OVERFLOW = """() => {
  const W = innerWidth, sr = document.getElementById('chat').shadowRoot;
  const wide = (root) => [...root.querySelectorAll('*')].filter(e => {
    const r = e.getBoundingClientRect(); return r.width > 0 && r.right > W + 1; }).length;
  return { page: document.documentElement.scrollWidth <= W, pageItems: wide(document), chatItems: sr ? wide(sr) : 0 };
}"""


@pytest.fixture(scope="session", autouse=True)
def server_is_up():
    try:
        httpx.get(f"{BASE}/api/health", timeout=10).raise_for_status()
    except httpx.HTTPError:
        pytest.exit(f"No app at {BASE}. Start the local server (see this file's docstring) "
                    "or set BASE_URL.", returncode=1)


def open_chat(page: Page) -> None:
    page.goto(BASE)
    page.get_by_role("button", name="Ask Cadre's AI").click()
    expect(page.locator(INPUT)).to_be_visible()


def ask(page: Page, text: str) -> None:
    page.locator(INPUT).click()
    page.keyboard.type(text)
    page.keyboard.press("Enter")


# ---------------- Desktop (Chromium) ----------------
def test_opens_with_ai_disclosure_and_starters(page: Page):
    open_chat(page)
    expect(page.locator(".ph small")).to_contain_text("Cadre's AI assistant")
    expect(page.locator("deep-chat .cad-chip", has_text="What does Cadre do?")).to_be_visible()


@pytest.mark.model
def test_starter_streams_a_complete_grounded_answer(page: Page):
    open_chat(page)
    page.locator("deep-chat .cad-chip", has_text="What is the AI Maturity Index?").click()
    expect(page.locator(LAST_ANSWER)).to_contain_text("pillar", timeout=ANSWER)
    expect(page.locator("deep-chat .cad-starters.cad-gone")).to_have_count(1)   # starters tucked away
    expect(page.locator("deep-chat")).not_to_contain_text("[HANDOFF")
    expect(page.locator(LAST_ANSWER)).not_to_contain_text("More:")          # source shown as a link chip
    expect(page.locator("deep-chat .cad-src").last).to_have_attribute("href", re.compile(r"^https://(portal\.go)?cadre\.ai"))
    page.get_by_role("button", name="More options").click()
    page.get_by_role("menuitem", name="Show behind the scenes").click()
    expect(page.locator("#status")).to_contain_text("maturity_index", timeout=ANSWER)


@pytest.mark.model
def test_pricing_offers_strategist_then_form_validates_and_confirms_once(page: Page):
    open_chat(page)
    ask(page, "How much does the 45-day intensive cost?")
    page.locator("deep-chat .cad-offer-btn").last.click(timeout=ANSWER)
    form = page.locator("deep-chat .cad-form").last
    expect(form.locator("input[name=subject]")).to_have_value("Pricing question")
    expect(form.locator("textarea[name=message]")).to_have_value(re.compile("45-day intensive"))
    form.locator(".cad-form-send").click()                                    # empty → error
    expect(form.locator(".cad-form-err")).to_contain_text("Enter your name first")
    form.locator("input[name=name]").fill("Browser Test")
    form.locator("input[name=email]").fill("browser-test@example.com")
    form.locator(".cad-form-send").dblclick()                                 # double submit
    expect(page.locator("deep-chat .cad-form-done")).to_have_count(1, timeout=10_000)
    expect(page.locator("deep-chat .cad-form-done")).to_contain_text("nothing was sent to Cadre")


@pytest.mark.model
def test_keyboard_only_open_ask_close(page: Page):
    page.goto(BASE)
    page.get_by_role("button", name="Ask Cadre's AI").focus()
    page.keyboard.press("Enter")
    expect(page.locator(INPUT)).to_be_visible()
    ask(page, "Where do I find the client portal?")
    expect(page.locator(LAST_ANSWER)).to_contain_text("portal.gocadre.ai", timeout=ANSWER)
    page.keyboard.press("Escape")
    expect(page.locator("#panel")).to_be_hidden()
    expect(page.locator("#launcher")).to_be_focused()


@pytest.mark.model
def test_start_over_clears_the_conversation(page: Page):
    open_chat(page)
    ask(page, "Do you work with hotels?")
    expect(page.locator(LAST_ANSWER)).to_contain_text("hospitality", timeout=ANSWER)
    page.get_by_role("button", name="Start a new chat").click()
    expect(page.locator("deep-chat .cad-msg")).to_have_count(1)            # just the greeting
    expect(page.locator("deep-chat .cad-starters:not(.cad-gone)")).to_have_count(1)


def test_firewall_rate_limit_says_slow_down_not_sorry(page: Page):
    # Vercel's firewall answers 429 before the app runs; simulate it (no need to flood the site)
    page.route("**/api/chat", lambda r: r.fulfill(status=429, body="Too Many Requests"))
    open_chat(page)
    ask(page, "What does Cadre do?")
    expect(page.locator(LAST_ANSWER)).to_contain_text("sending messages quickly")
    expect(page.locator(INPUT)).to_be_editable()                              # input released


def _fake_stream(page: Page, body: str) -> None:
    page.route("**/api/chat", lambda r: r.fulfill(status=200, body=body,
                                                  headers={"Content-Type": "text/event-stream"}))


def test_a_hiccup_after_the_answer_never_replaces_it(page: Page):
    # Audit 09-25: an error after "done" (here, a garbled trailing event) replaced a finished
    # answer with "Sorry, I couldn't answer that just now."
    _fake_stream(page, 'event: token\ndata: {"text": "Cadre works in construction."}\n\n'
                       'event: done\ndata: {"handoff": false, "model": "m"}\n\n'
                       'event: token\ndata: {garbled\n\n')
    open_chat(page)
    ask(page, "Do you work with construction companies?")
    expect(page.locator(LAST_ANSWER)).to_contain_text("Cadre works in construction.")
    expect(page.locator(LAST_ANSWER)).not_to_contain_text("couldn't answer")
    expect(page.locator(INPUT)).to_be_editable()


def test_a_cut_off_answer_keeps_what_arrived_and_says_so(page: Page):
    # Audit 09-25: a stream that ended mid-answer showed the half answer with no hint
    _fake_stream(page, 'event: token\ndata: {"text": "Cadre has four services:"}\n\n')
    open_chat(page)
    ask(page, "What does Cadre do?")
    expect(page.locator(LAST_ANSWER)).to_contain_text("Cadre has four services:")
    expect(page.locator(LAST_ANSWER)).to_contain_text("couldn't answer that just now")


def test_privacy_page_matches_storage(page: Page):
    # No longer linked from the widget (Brian, 09-24); the page stays accurate at /privacy.html
    page.goto(BASE + "/privacy.html")
    expect(page.locator("body")).to_contain_text("redacted, for 30 days")


# ---------------- iPhone profile (WebKit = Safari's engine) ----------------
@pytest.fixture
def iphone(playwright):
    browser = playwright.webkit.launch()
    ctx = browser.new_context(**playwright.devices["iPhone 14"])
    yield ctx.new_page()
    ctx.close()
    browser.close()


@pytest.mark.model
def test_iphone_nothing_wider_than_the_screen_through_a_full_conversation(iphone: Page):
    def check(step):
        o = iphone.evaluate(NO_OVERFLOW)
        assert o == {"page": True, "pageItems": 0, "chatItems": 0}, f"overflow at {step}: {o}"
    iphone.goto(BASE)
    check("landing")
    iphone.get_by_role("button", name="Ask Cadre's AI").tap()
    expect(iphone.locator(INPUT)).to_be_visible()
    check("open")
    iphone.locator("deep-chat .cad-chip", has_text="How do I book a call?").tap()
    expect(iphone.locator("deep-chat .cad-form")).to_have_count(1, timeout=ANSWER)  # asked for a call → form now
    check("answer + form")


def test_iphone_keyboard_never_covers_the_form_and_nothing_auto_focuses(iphone: Page):
    # Simulate the iOS keyboard: visualViewport reports a shorter visible area, like Safari does
    iphone.add_init_script("""(() => { const vv = window.visualViewport; let kb = 0;
      Object.defineProperty(vv, 'height', { get: () => window.innerHeight - kb });
      Object.defineProperty(vv, 'offsetTop', { get: () => 0 });
      window.__keyboard = (h) => { kb = h; vv.dispatchEvent(new Event('resize')); }; })();""")
    iphone.goto(BASE)
    iphone.get_by_role("button", name="Ask Cadre's AI").tap()
    expect(iphone.locator(INPUT)).to_be_visible()
    assert iphone.evaluate("document.activeElement.tagName") == "BODY", "opening must not pop the keyboard"
    iphone.get_by_role("button", name="Talk to a strategist").tap()
    name = iphone.locator("deep-chat .cad-form input[name=name]").last
    expect(name).to_be_visible()
    assert iphone.evaluate("!document.getElementById('chat').shadowRoot.activeElement"), "form must not grab focus"
    name.tap()
    iphone.evaluate("window.__keyboard(336)")                    # iPhone 14 keyboard height
    iphone.wait_for_timeout(900)
    visible = iphone.evaluate("innerHeight") - 336
    box = name.bounding_box()
    assert box["y"] >= 0 and box["y"] + box["height"] <= visible, f"field hidden by keyboard: {box}, visible={visible}"


def test_iphone_open_chat_locks_the_page_behind_it(iphone: Page):
    # On Brian's iPhone (09-26), swipes in the open chat scrolled the page behind it, so the page
    # moved and the chat didn't. Open: the page is locked and the chat list keeps its swipes.
    # Close: the page is back where the visitor left it. No model call: the forms come from the
    # header button.
    iphone.goto(BASE)
    iphone.evaluate("document.querySelector('main').style.minHeight = '3000px'; scrollTo(0, 500)")
    iphone.get_by_role("button", name="Ask Cadre's AI").tap()
    expect(iphone.locator(INPUT)).to_be_visible()
    for _ in range(3):                                            # enough content for the chat to scroll
        iphone.get_by_role("button", name="Talk to a strategist").tap()
    state = iphone.evaluate("""() => { scrollTo(0, 900);
      const m = document.getElementById('chat').shadowRoot.querySelector('#messages');
      return { pageY: scrollY, bodyTop: document.body.style.top, contain: getComputedStyle(m).overscrollBehaviorY,
               chatScrolls: m.scrollHeight > m.clientHeight }; }""")
    assert state == {"pageY": 0, "bodyTop": "-500px", "contain": "contain", "chatScrolls": True}, state
    iphone.locator("#close").tap()
    iphone.wait_for_timeout(400)
    assert iphone.evaluate("scrollY") == 500, "closing must put the page back where it was"


def test_iphone_inputs_are_16px_so_safari_does_not_zoom(iphone: Page):
    iphone.goto(BASE)
    iphone.get_by_role("button", name="Ask Cadre's AI").tap()
    size = iphone.locator(INPUT).evaluate("e => getComputedStyle(e).fontSize")
    assert size == "16px", f"Safari zooms the page for inputs under 16px; got {size}"
