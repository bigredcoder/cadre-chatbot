"""Browser tests: drive the real widget in Chromium, like a visitor.

Runs against the LIVE site by default (real Jev, real model: a few cents per run):
  .venv/bin/python -m pytest e2e -q
Against local:  BASE_URL=http://localhost:8000 .venv/bin/python -m pytest e2e -q
  (start the local server with RATE_LIMIT_PER_MINUTE=1000: repeated runs from one machine
   otherwise hit the per-visitor limit, 12 messages/minute, and answers time out)
Not part of the default `pytest` run (unit tests live in tests/).
"""
import os
import re

import pytest
from playwright.sync_api import Page, expect

BASE = os.environ.get("BASE_URL", "https://cadre-chatbot-xi.vercel.app")
ANSWER_TIMEOUT = 30_000


@pytest.fixture
def widget(page: Page) -> Page:
    page.goto(BASE)
    page.get_by_role("button", name="Ask Cadre's AI").click()
    return page


def test_launcher_is_labeled_and_opens_with_focus_in_input(widget: Page):
    expect(widget.get_by_role("dialog")).to_be_visible()
    expect(widget.locator("#q")).to_be_focused()
    expect(widget.locator(".ph small")).to_contain_text("Cadre's AI assistant")  # AI disclosure
    expect(widget.get_by_role("button", name="What does Cadre do?")).to_be_visible()


def test_starter_question_streams_a_grounded_answer(widget: Page):
    widget.get_by_role("button", name="What is the AI Maturity Index?").click()
    answer = widget.locator("#log .msg:not(.user)").last
    expect(answer).to_contain_text("pillar", timeout=ANSWER_TIMEOUT)
    expect(widget.locator("#log")).not_to_contain_text("[HANDOFF")
    widget.get_by_label("Behind the scenes").check()
    expect(widget.locator(".bts").last).to_contain_text("maturity_index")


def test_pricing_shows_prefilled_form_and_honest_demo_confirmation(widget: Page):
    widget.locator("#q").fill("How much does the 45-day intensive cost?")
    widget.locator("#q").press("Enter")
    form = widget.locator("form.handoff")
    expect(form).to_be_visible(timeout=ANSWER_TIMEOUT)
    expect(form.get_by_label("Subject")).to_have_value("Pricing question")
    expect(form.get_by_label("Message")).to_have_value(re.compile("45-day intensive"))
    expect(form.get_by_label("Name")).to_be_focused()
    form.get_by_role("button", name="Send to the team").click()                  # empty → error
    expect(form.get_by_role("alert")).to_contain_text("Enter your name first")
    form.get_by_label("Name").fill("Browser Test")
    form.get_by_label("Email").fill("browser-test@example.com")
    form.get_by_role("button", name="Send to the team").dblclick()               # double submit
    confirmation = widget.locator("#log .msg", has_text="nothing was sent to Cadre")
    expect(confirmation).to_have_count(1, timeout=10_000)


def test_keyboard_only_open_ask_close(page: Page):
    page.goto(BASE)
    page.get_by_role("button", name="Ask Cadre's AI").focus()
    page.keyboard.press("Enter")
    expect(page.locator("#q")).to_be_focused()
    page.keyboard.type("Where do I find the client portal?")
    page.keyboard.press("Enter")
    expect(page.locator("#log .msg:not(.user)").last).to_contain_text(
        "portal.gocadre.ai", timeout=ANSWER_TIMEOUT)
    page.keyboard.press("Escape")
    expect(page.get_by_role("dialog")).to_be_hidden()
    expect(page.get_by_role("button", name="Ask Cadre's AI")).to_be_focused()   # focus returns


def test_phone_size_panel_fills_screen_and_input_is_usable(browser):
    ctx = browser.new_context(viewport={"width": 375, "height": 812}, is_mobile=True, has_touch=True)
    page = ctx.new_page()
    page.goto(BASE)
    page.get_by_role("button", name="Ask Cadre's AI").click()
    expect(page.get_by_role("dialog")).to_have_class(re.compile(r"\bopen\b"))
    page.wait_for_function("getComputedStyle(document.getElementById('panel')).transform === 'none'")
    box = page.get_by_role("dialog").bounding_box()  # measured after the open animation
    assert box["width"] >= 370, f"panel should fill a phone screen, got {box['width']}px"
    expect(page.locator("#q")).to_be_in_viewport()
    expect(page.get_by_role("button", name="Talk to a strategist")).to_be_in_viewport()
    ctx.close()


def test_privacy_page_loads_and_matches_storage(page: Page):
    page.goto(BASE)
    page.get_by_role("button", name="Ask Cadre's AI").click()
    with page.expect_popup() as popup:
        page.get_by_role("link", name="How chat data is used").click()
    privacy = popup.value
    expect(privacy.get_by_role("heading", name="How chat data is used")).to_be_visible()
    expect(privacy.locator("body")).to_contain_text("redacted, for 30 days")
