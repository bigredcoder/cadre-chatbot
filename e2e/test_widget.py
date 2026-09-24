"""Browser tests: drive the real widget like a visitor, on desktop Chromium AND an iPhone
profile in WebKit (Safari's engine). Phone tests fail if anything is wider than the screen.

Runs against the LIVE site by default (real Jev, real model: a few cents per run):
  .venv/bin/python -m pytest e2e -q
Against local:  BASE_URL=http://localhost:8000 .venv/bin/python -m pytest e2e -q
  (start the local server with RATE_LIMIT_PER_MINUTE=1000: repeated runs from one machine
   otherwise hit the per-visitor limit, 12 messages/minute, and answers time out)
Not part of the default `pytest` run (unit tests live in tests/).
The chat window is Deep Chat (a web component); Playwright's CSS locators see inside it.
"""
import os
import re

import pytest
from playwright.sync_api import Page, expect

BASE = os.environ.get("BASE_URL", "https://cadre-chatbot-xi.vercel.app")
ANSWER = 30_000
INPUT = "deep-chat #text-input"
LAST_ANSWER = "deep-chat .cad-msg >> nth=-1"
NO_OVERFLOW = """() => {
  const W = innerWidth, sr = document.getElementById('chat').shadowRoot;
  const wide = (root) => [...root.querySelectorAll('*')].filter(e => {
    const r = e.getBoundingClientRect(); return r.width > 0 && r.right > W + 1; }).length;
  return { page: document.documentElement.scrollWidth <= W, pageItems: wide(document), chatItems: sr ? wide(sr) : 0 };
}"""


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
    expect(page.locator("#notice")).to_contain_text("saved for 30 days")
    expect(page.locator("deep-chat .cad-chip", has_text="What does Cadre do?")).to_be_visible()


def test_starter_streams_a_complete_grounded_answer(page: Page):
    open_chat(page)
    page.locator("deep-chat .cad-chip", has_text="What is the AI Maturity Index?").click()
    expect(page.locator(LAST_ANSWER)).to_contain_text("pillar", timeout=ANSWER)
    expect(page.locator("deep-chat .cad-starters.cad-gone")).to_have_count(1)   # starters tucked away
    expect(page.locator("deep-chat")).not_to_contain_text("[HANDOFF")
    page.get_by_role("button", name="More options").click()
    page.get_by_role("menuitem", name="Show behind the scenes").click()
    expect(page.locator("#status")).to_contain_text("maturity_index", timeout=ANSWER)


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


def test_start_over_clears_the_conversation(page: Page):
    open_chat(page)
    ask(page, "Do you work with hotels?")
    expect(page.locator(LAST_ANSWER)).to_contain_text("hospitality", timeout=ANSWER)
    page.get_by_role("button", name="More options").click()
    page.get_by_role("menuitem", name="Start a new chat").click()
    expect(page.locator("deep-chat .cad-msg")).to_have_count(1)            # just the greeting
    expect(page.locator("deep-chat .cad-starters:not(.cad-gone)")).to_have_count(1)


def test_privacy_page_matches_storage(page: Page):
    open_chat(page)
    with page.expect_popup() as popup:
        page.locator("#notice").get_by_role("link", name="Details").click()
    expect(popup.value.locator("body")).to_contain_text("redacted, for 30 days")


# ---------------- iPhone profile (WebKit = Safari's engine) ----------------
@pytest.fixture
def iphone(playwright):
    browser = playwright.webkit.launch()
    ctx = browser.new_context(**playwright.devices["iPhone 14"])
    yield ctx.new_page()
    ctx.close()
    browser.close()


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


def test_iphone_inputs_are_16px_so_safari_does_not_zoom(iphone: Page):
    iphone.goto(BASE)
    iphone.get_by_role("button", name="Ask Cadre's AI").tap()
    size = iphone.locator(INPUT).evaluate("e => getComputedStyle(e).fontSize")
    assert size == "16px", f"Safari zooms the page for inputs under 16px; got {size}"
