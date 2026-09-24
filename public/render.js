// Safe rendering for Cadence's answers. Kept out of index.html so it can be unit-tested
// (tests/js/render.test.mjs, run by pytest). Rules: escape everything; links only to Cadre's
// own sites (research findings #7); "More: <cadre url>" endings become labeled source links.
(() => {
const ALLOWED = ["cadre.ai", "www.cadre.ai", "portal.gocadre.ai"];

// ---- Safe rendering (unchanged rules): escape everything; links only to Cadre's sites ----
const esc = (s) => s.replace(/[&<>"']/g, (c) => ({ "&":"&amp;", "<":"&lt;", ">":"&gt;", '"':"&quot;", "'":"&#39;" }[c]));
function linkify(s) {
  return s.replace(/(?<![\w.@-])(https?:\/\/)?((?:www\.)?cadre\.ai(?:\/[\w\-\/]*)?|portal\.gocadre\.ai(?:\/[\w\-\/]*)?)|hello@gocadre\.ai/g, (m, p, hostpath) => {
    if (m === "hello@gocadre.ai") return `<a href="mailto:hello@gocadre.ai">${m}</a>`;
    const url = new URL("https://" + hostpath.replace(/[.\/]+$/, ""));
    return ALLOWED.includes(url.hostname) ? `<a href="${url.href}" target="_blank" rel="noopener">${esc(m)}</a>` : m;
  });
}
// "More: cadre.ai/strategy." endings become a labeled source link under the answer
// (research findings: show sources; 09-24 polish). Labels come from the page path.
const SOURCE_LABELS = { "": "cadre.ai", "strategy": "AI Strategy", "leadership-facilitation": "AI Leadership & Facilitation",
  "ai-engineering": "AI Engineering", "agents": "AI Agents", "about": "About Cadre", "contact": "Contact Cadre",
  "case-studies": "Case studies", "industries": "Industries", "ai-maturity-index": "AI Maturity Index",
  "retail-e-commerce": "Retail & E-commerce", "manufacturing-logistics": "Manufacturing & Logistics" };
const MORE = /\s*(?:More|Learn more|Source):\s*((?:https?:\/\/)?(?:www\.)?(?:cadre\.ai|portal\.gocadre\.ai)(?:\/[\w\-\/]*)?)\.?/gi;
function sourceLabel(url) {
  const path = url.replace(/^https?:\/\//, "").replace(/^[^/]+\/?/, "").replace(/\/+$/, "");
  const last = path.split("/").pop();
  if (url.includes("portal.gocadre.ai") && !path) return "Cadre client portal";
  // filter(Boolean): "foo-" or "a--b" once threw here and froze the chat (audit 09-24)
  return SOURCE_LABELS[last] ?? (last.split("-").filter(Boolean).map((w) => w[0].toUpperCase() + w.slice(1)).join(" ") || "cadre.ai");
}
function render(text, final = true) {
  const sources = [];
  // Mid-stream, hide a half-typed "More: cadre.ai/str" line; the link appears when the answer is done
  if (!final) text = text.replace(/\s*(?:More|Learn more|Source):[^\n]*$/i, "");
  text = text.replace(MORE, (m, url) => { if (!sources.includes(url)) sources.push(url); return ""; });
  let html = "", list = false;
  for (const raw of esc(text.trim()).split("\n")) {
    const line = raw.replace(/\*\*(.+?)\*\*/g, "<b>$1</b>");
    const item = line.match(/^\s*[*\-•]\s+(.*)/);
    if (item) { if (!list) { html += "<ul>"; list = true; } html += `<li>${linkify(item[1])}</li>`; continue; }
    if (list) { html += "</ul>"; list = false; }
    if (line.trim()) html += `<p>${linkify(line)}</p>`;
  }
  const src = sources.map((u) => `<a class="cad-src" href="https://${u.replace(/^https?:\/\//, "").replace(/[.\/]+$/, "")}" target="_blank" rel="noopener">${esc(sourceLabel(u))} ↗</a>`).join("");
  return `<div class="cad-msg">${list ? html + "</ul>" : html}${src ? `<div class="cad-srcs">${src}</div>` : ""}</div>`;
}

globalThis.CadenceRender = { esc, linkify, render, sourceLabel };
})();
