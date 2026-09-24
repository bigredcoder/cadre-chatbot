// Unit tests for public/render.js (the widget's safe rendering). Run: node --test tests/js
// pytest runs these too (tests/test_render_js.py), so `pytest -q` covers Python and JS.
import { test } from "node:test";
import assert from "node:assert/strict";
import "../../public/render.js";

const { render, sourceLabel } = globalThis.CadenceRender;

test("escapes model output: no HTML gets through", () => {
  const html = render('Hi <img src=x onerror=alert(1)> and <script>x</script>');
  assert.ok(!html.includes("<img") && !html.includes("<script"));
  assert.ok(html.includes("&lt;img"));
});

test("links only Cadre's own sites", () => {
  const html = render("See cadre.ai/strategy, portal.gocadre.ai, example.com and evilcadre.ai/x");
  assert.ok(html.includes('href="https://cadre.ai/strategy"'));
  assert.ok(html.includes('href="https://portal.gocadre.ai/"'));
  assert.ok(!html.includes("example.com</a>"));
  assert.ok(!html.includes("evilcadre.ai/x</a>") && !html.includes('href="https://cadre.ai/x"'));
});

test("a 'More:' ending becomes one labeled source link", () => {
  const html = render("It is 45 days. More: cadre.ai/strategy.");
  assert.ok(!html.includes("More:"));
  assert.match(html, /class="cad-src" href="https:\/\/cadre\.ai\/strategy"[^>]*>AI Strategy ↗/);
});

test("mid-stream, a half-typed source line is hidden", () => {
  assert.ok(!render("It is 45 days. More: cadre.ai/str", false).includes("cad-src"));
});

test("odd source paths never throw (09-24: 'foo-' froze the chat)", () => {
  for (const u of ["cadre.ai/foo-", "cadre.ai/a--b", "cadre.ai/-", "cadre.ai/", "portal.gocadre.ai"]) {
    assert.doesNotThrow(() => render(`Answer. More: ${u}`));
    assert.ok(sourceLabel(u).length > 0, u);
  }
  assert.equal(sourceLabel("cadre.ai/industries/private-equity"), "Private Equity");
});

test("a crafted source line can't inject markup", () => {
  const html = render('More: cadre.ai/"><img src=x onerror=alert(1)>');
  assert.ok(!html.includes("<img"));
});

test("bullets become a list; bold survives escaping", () => {
  const html = render("Services:\n* **AI Strategy**\n* AI Agents");
  assert.match(html, /<ul><li><b>AI Strategy<\/b><\/li><li>AI Agents<\/li><\/ul>/);
});
