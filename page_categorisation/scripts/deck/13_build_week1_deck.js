// Week-1 prototype review deck. Design mirrors Web_Page_Categorisation.pptx (13.33x7.5, Cambria/Calibri,
// navy 11203A dark slides, F7F6F2 light slides, white rounded cards, amber E08E1D for risks).
// Every number comes from results/*.json (benchmark, cascade_summary, scale_cost, llm_haiku_summary).
const pptxgen = require("pptxgenjs");
const SK = process.env.SKILL_DIR;
const { applyTheme } = require(SK + "/scripts/apply_theme.js");

const OUT = process.argv[2] || "Week1_Prototype_Review.pptx";
const TOTAL = 16;
const FOOT = "Web Page Categorisation — Week 1 Prototype";

const THEME = {
  name: "Web Page Categorisation",
  headFontFace: "Cambria",
  bodyFontFace: "Calibri",
  colors: {
    dk1: "1B2435", lt1: "FFFFFF", dk2: "11203A", lt2: "ECEAE2",
    accent1: "2F6FED", accent2: "E08E1D", accent3: "5B6472", accent4: "0F766E",
    accent5: "A33D1C", accent6: "8FB1F2", hlink: "2F6FED", folHlink: "5B6472",
  },
};

const NAVY = "11203A", INK = "1B2435", GREY = "5B6472", BLUE = "2F6FED", AMBER = "E08E1D", TEAL = "0F766E";
const LBLUE = "8FB1F2", RULE = "E2DFD4", CHIP = "ECEAE2", LIGHTBG = "F7F6F2";
const DCARD = "192C4D", DCARD2 = "152747", WARN = "2A2013", DTEXT = "C3CDE0", WTEXT = "D9C2A0", DTITLE = "F1F3F7";
const AMBERBG = "FCEFDC";

const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE"; // 13.33 x 7.5
pres.title = "Web Page Categorisation: Week 1 prototype review";
pres.author = "Project team";
pres.theme = { headFontFace: "Cambria", bodyFontFace: "Calibri" };

pres.defineSlideMaster({ title: "LIGHT", background: { color: LIGHTBG } });
pres.defineSlideMaster({ title: "DARK", background: { color: NAVY } });

// ---------- helpers ----------
const warns = [];
const CW = { Calibri: 0.5, Cambria: 0.57, "Courier New": 0.6 };
function est(text, w, pt, face, bold) {
  const f = (CW[face] || 0.5) * (bold ? 1.06 : 1);
  const perLine = Math.max(1, Math.floor(w / ((f * pt) / 72)));
  const paras = String(text).split("\n");
  const lines = paras.reduce((n, p) => n + Math.max(1, Math.ceil(p.length / perLine)), 0);
  return (lines * pt * 1.22) / 72;
}
function T(s, text, x, y, w, h, o = {}) {
  const face = o.fontFace || "Calibri";
  const pt = o.fontSize || 13;
  const plain = Array.isArray(text) ? text.map((r) => r.text).join("") : text;
  const need = est(plain, w, pt, face, o.bold);
  if (need > h + 0.02) warns.push(`overflow? "${plain.slice(0, 40)}" needs ${need.toFixed(2)}in, box ${h}in`);
  s.addText(text, Object.assign({ x, y, w, h, margin: 0, valign: "top", isTextBox: true, fontFace: face, fontSize: pt, color: INK }, o));
}
const shadow = () => ({ type: "outer", color: NAVY, opacity: 0.18, blur: 6, offset: 2, angle: 90 });
function card(s, x, y, w, h, kind, name) {
  const o = { x, y, w, h, rectRadius: 0.1, objectName: name || "card" };
  if (kind === "light") Object.assign(o, { fill: { color: "FFFFFF" }, line: { color: RULE, width: 1 }, shadow: shadow() });
  else Object.assign(o, { fill: { color: kind }, line: { color: kind, width: 0.5 } });
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, o);
}
function bar(s, x, y, w, h, fill, name) { s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w, h, rectRadius: 0.08, fill: { color: fill }, line: { color: fill, width: 0 }, objectName: name || "bar" }); }
function arrowR(s, x, y, color) { s.addShape(pres.shapes.RIGHT_ARROW, { x, y, w: 0.24, h: 0.16, fill: { color }, line: { color, width: 0.25 }, objectName: "arrow" }); }
function arrowD(s, x, y, color) { s.addShape(pres.shapes.DOWN_ARROW, { x, y, w: 0.25, h: 0.28, fill: { color }, line: { color, width: 0.25 }, objectName: "arrow" }); }
function rule(s, x, y, w) { s.addShape(pres.shapes.LINE, { x, y, w, h: 0, line: { color: RULE, width: 1 }, objectName: "rule" }); }

function frame(dark, kicker, title, n, titleSize = 28) {
  const s = pres.addSlide({ masterName: dark ? "DARK" : "LIGHT" });
  T(s, kicker, 0.7, 0.5, 10, 0.3, { fontSize: 12, bold: true, color: dark ? LBLUE : BLUE, objectName: "kicker" });
  T(s, title, 0.7, 0.82, 11.9, 1.0, { fontSize: titleSize, bold: true, fontFace: "Cambria", color: dark ? DTITLE : NAVY, objectName: "title" });
  T(s, FOOT, 0.7, 6.95, 7, 0.3, { fontSize: 10, color: dark ? "7E8AA3" : "9AA0AC", objectName: "footer" });
  T(s, String(n).padStart(2, "0") + " / " + TOTAL, 11.93, 6.95, 0.7, 0.3, { fontSize: 10, color: dark ? "7E8AA3" : "9AA0AC", align: "right", objectName: "page" });
  return s;
}
const tableCell = (text, o = {}) => ({ text, options: Object.assign({ fontFace: "Calibri", fontSize: 12, color: INK, valign: "middle" }, o) });
const TBORDER = { type: "solid", pt: 0.5, color: RULE };

// ================= 1. Title =================
{
  const s = pres.addSlide({ masterName: "DARK" });
  s.addShape(pres.shapes.OVAL, { x: 10.3, y: -1.6, w: 4.4, h: 4.4, fill: { color: BLUE, transparency: 86 }, line: { color: BLUE, transparency: 100, width: 0 }, objectName: "decor" });
  T(s, "WEEK 1 PROTOTYPE REVIEW", 0.9, 2.15, 10, 0.35, { fontSize: 14, bold: true, color: LBLUE, objectName: "kicker" });
  T(s, "Web Page Categorisation: what we built in week one", 0.9, 2.6, 10.8, 1.7, { fontSize: 44, bold: true, fontFace: "Cambria", color: DTITLE, objectName: "title" });
  T(s, "Classifying page type and audience from URL and page text: the approach, a working prototype, how well it does on sites it has never seen, and the issues we hit.", 0.9, 4.5, 9.6, 1.0, { fontSize: 16, color: DTEXT, objectName: "subtitle" });
  T(s, "DCR Project #1 · Week 1 review", 0.9, 6.75, 5, 0.3, { fontSize: 12, color: "AEB8CC" });
  T(s, "27 October 2026", 7.43, 6.75, 5, 0.3, { fontSize: 12, color: "AEB8CC", align: "right" });
  s.addNotes("Week-1 review of the DCR web page categorisation project. In this session: what we built, how well it works on sites it has never seen, what went wrong along the way, and what we recommend next. Every number in this deck was measured on the ten site scans we were given; where a number is a calculation rather than a measurement, the slide says so.");
}

// ================= 2. Agenda =================
{
  const s = frame(false, "AGENDA", "Where we're going", 2, 34);
  const items = [
    ["What we built", "The data, the approach, the taxonomy and the working prototype"],
    ["How well it works", "Accuracy on sites it has never seen: the cheap tiers, then the LLM"],
    ["Cost, scale and what changed", "Speed, measured LLM cost, and assumptions we had to revisit"],
    ["Issues and next steps", "What we fixed, what is still open, and what we recommend"],
  ];
  items.forEach((it, i) => {
    const y = 2.0 + i * 1.1;
    s.addShape(pres.shapes.OVAL, { x: 0.7, y, w: 0.55, h: 0.55, fill: { color: BLUE }, line: { color: BLUE, width: 0 }, objectName: "num" });
    T(s, String(i + 1), 0.7, y, 0.55, 0.55, { fontSize: 18, bold: true, fontFace: "Cambria", color: "FFFFFF", align: "center", valign: "middle" });
    T(s, it[0], 1.5, y - 0.06, 10.8, 0.35, { fontSize: 18, bold: true, fontFace: "Cambria" });
    T(s, it[1], 1.5, y + 0.28, 10.8, 0.35, { fontSize: 13, color: GREY });
    rule(s, 0.7, y + 0.85, 11.93);
  });
  s.addNotes("Four parts: what we built, how well it works (first the cheap tiers, then the LLM), what it costs and which of our assumptions changed, and finally the issues and next steps.");
}

// ================= 3. Data =================
{
  const s = frame(false, "THE DATA", "Ten site scans, 34,319 records, 10,625 real pages", 3);
  const stats = [
    ["34,319", "records across 10 site scans, between 2.2k and 6.1k each", false],
    ["10,625", "real pages or PDFs (7,195 HTML and 3,430 PDF). The rest are images, errors and viewer shells.", false],
    ["31%", "of pages sit on other organisations' sites (PubMed, NICE, EMA and similar)", false],
    ["0", "records have the language or translated-text fields filled in", true],
  ];
  stats.forEach((st, i) => {
    const x = 0.7 + i * 3.04;
    card(s, x, 1.95, 2.85, 2.1, st[2] ? AMBERBG : "light");
    T(s, st[0], x + 0.25, 2.12, 2.4, 0.7, { fontSize: 36, bold: true, fontFace: "Cambria", color: st[2] ? "946200" : BLUE });
    T(s, st[1], x + 0.25, 2.88, 2.4, 1.1, { fontSize: 13, color: st[2] ? INK : GREY });
  });
  const chips = [
    "No ground-truth labels were supplied, so we built our own",
    "12+ languages found: English is 58% of pages, Spanish and Japanese about 13% each",
    "Templates dominate: about 3,100 URL templates across the 10,625 pages",
    "Near-duplicates collapse 10,625 pages to 8,622 units",
  ];
  chips.forEach((c, i) => {
    const x = 0.7 + i * 3.04;
    bar(s, x, 4.35, 2.85, 1.1, CHIP, "chip");
    T(s, c, x + 0.15, 4.35, 2.55, 1.1, { fontSize: 13, bold: true, color: NAVY, valign: "middle" });
  });
  T(s, "Most of a page's text is menus, cookie banners and footers, so cleaning the text was the first job.", 0.7, 5.8, 11.93, 0.5, { fontSize: 14, color: GREY });
  s.addNotes("Ten scans, about 34 thousand records, of which about 10.6 thousand are real pages or PDFs. Nearly a third of the pages are on other organisations' sites because the crawls followed outbound links. The scan's language and translation fields are empty in every record, so we detect language ourselves. No labels came with the data.");
}

// ================= 4. Approach (dark) =================
{
  const s = frame(true, "APPROACH", "The approach: a cascade from cheap rules to an LLM", 4);
  const boxes = [
    ["Page in", "URL and text from the site scan (HTML and PDF)", false],
    ["Clean text", "Strip menus and banners per site, split the URL into words, detect language", false],
    ["Tier 1 · Rules", "Multilingual keyword, URL and page-structure evidence", false],
    ["Tier 2 · Model", "Embedding model trained on the labelled pages", false],
    ["Confidence gate", "Publish, sample for a check, or send to review", false],
    ["Tier 3 · LLM", "Haiku 5.5, measured on the labelled pages (slides 9 and 10)", true],
  ];
  boxes.forEach((b, i) => {
    const x = 0.68 + i * 2.04;
    card(s, x, 2.1, 1.78, 2.25, b[2] ? WARN : DCARD);
    T(s, b[0], x + 0.18, 2.3, 1.45, 0.62, { fontSize: 14.5, bold: true, fontFace: "Cambria", color: DTITLE });
    T(s, b[1], x + 0.18, 3.0, 1.45, 1.25, { fontSize: 11.5, color: b[2] ? WTEXT : DTEXT });
    if (i < 5) arrowR(s, x + 1.8, 3.1, i === 4 ? AMBER : LBLUE);
  });
  bar(s, 0.68, 4.62, 11.98, 0.55, BLUE, "output");
  T(s, "Output per page: type + audience + declared audience + confidence + evidence + review status", 0.9, 4.62, 11.5, 0.55, { fontSize: 15, bold: true, color: "FFFFFF", valign: "middle" });
  T(s, "Type and audience are scored separately. The audience a page declares (“for HCPs only”) is kept apart from the audience its content suggests, so mismatches can be flagged.", 0.7, 5.5, 5.8, 1.1, { fontSize: 13, color: DTEXT });
  T(s, "If most pages on a site carry a declaration, the site's other pages inherit it. This needs no labels, so it works on any new scan.", 6.83, 5.5, 5.8, 1.1, { fontSize: 13, color: DTEXT });
  s.addNotes("This follows the architecture in the proposal. Cheap rules first, then a small embedding model, then a confidence gate that decides whether to publish, spot-check or send for review, then an LLM. We measured all of it on the same 800 labelled pages: the cheap tiers on slides 7 and 8, the LLM tier on slides 9 and 10. Type and audience are separate axes, and we keep the audience a page declares apart from the audience its content suggests, because the difference between the two is a compliance signal.");
}

// ================= 5. Taxonomy =================
{
  const s = frame(false, "APPROACH · TAXONOMY", "A taxonomy built from the data: 23 page types, 8 audiences", 5);
  card(s, 0.7, 1.95, 8.0, 3.85, "light");
  T(s, "23 page types", 1.0, 2.12, 7.4, 0.4, { fontSize: 17, bold: true, fontFace: "Cambria", color: NAVY });
  const types = ["Homepage / Hub", "Gateway / Selector", "Login / Registration", "Contact / Locations", "Legal & Compliance", "Form / Request", "Safety Reporting", "About the Company",
    "Investor Relations", "Careers", "News & Media", "Article / Story", "Sustainability", "Product Information", "Prescribing Information", "Disease & Therapy Area",
    "Clinical Evidence", "Medical Education & Events", "Patient Support", "R&D & Science", "Listing / Library", "Utility / Error", "Other"];
  [types.slice(0, 8), types.slice(8, 16), types.slice(16)].forEach((col, ci) => {
    s.addText(col.map((a, i) => ({ text: a, options: { bullet: true, breakLine: i < col.length - 1 } })), { x: 1.0 + ci * 2.55, y: 2.65, w: 2.45, h: 2.95, margin: 0, valign: "top", isTextBox: true, fontFace: "Calibri", fontSize: 13, color: INK, paraSpaceAfter: 5, objectName: "types" });
  });
  card(s, 8.9, 1.95, 3.73, 3.85, "light");
  T(s, "8 audiences", 9.2, 2.12, 3.3, 0.4, { fontSize: 17, bold: true, fontFace: "Cambria", color: NAVY });
  const aud = ["Healthcare Professional", "Patient / Caregiver", "General Public", "Investor", "Media", "Job Seeker", "Business Partner", "Unclear"];
  s.addText(aud.map((a, i) => ({ text: a, options: { bullet: true, breakLine: i < aud.length - 1 } })), { x: 9.2, y: 2.65, w: 3.2, h: 2.4, margin: 0, valign: "top", isTextBox: true, fontFace: "Calibri", fontSize: 13, color: INK, paraSpaceAfter: 4, objectName: "audiences" });
  T(s, "No Job Seeker page was drawn into the labelled sample, so that audience is untested.", 9.2, 5.1, 3.2, 0.6, { fontSize: 12, color: GREY });
  T(s, "Clustering grouped pages by site and clinical topic, not by function, so it checked and extended a hand-built list rather than replacing it. The sample has no employee content, so “Job Seeker” replaces “Employee”.", 0.7, 6.0, 11.93, 0.7, { fontSize: 13, color: GREY });
  s.addNotes("The proposal said to discover the taxonomy from the data. We tried clustering first. The clusters followed the site and the clinical topic rather than what a page is for, so we used them to check and extend a hand-built list. Two types, Form / Request and Legal & Compliance, were added after reviewing clusters. There is no employee content in the sample, so Job Seeker replaces Employee. The list on the slide is exactly the taxonomy file, in file order.");
}

// ================= 6. How we measured =================
{
  const s = frame(false, "QUALITY", "How we measured it: a labelled set and a new-site test", 6);
  const cards = [
    ["A labelled set", "800 pages, 80 per site, balanced across URL templates, with weights that restore the real page mix."],
    ["Two annotators", "A third pass settled their disagreements. They agreed on 91% of page types and 97% of audiences (Cohen's kappa 0.905 and 0.952)."],
    ["Leave-one-site-out", "Train on nine sites, score the tenth cold, and rotate through all ten."],
  ];
  cards.forEach((c, i) => {
    const x = 0.7 + i * 4.06;
    card(s, x, 1.95, 3.81, 1.95, "light");
    T(s, c[0], x + 0.25, 2.12, 3.31, 0.4, { fontSize: 16, bold: true, fontFace: "Cambria", color: NAVY });
    T(s, c[1], x + 0.25, 2.62, 3.31, 1.2, { fontSize: 13, color: GREY });
  });
  card(s, 0.7, 4.1, 11.93, 1.55, "light");
  T(s, "One rotation of the test", 1.0, 4.25, 6, 0.3, { fontSize: 13, bold: true, color: BLUE });
  for (let i = 0; i < 10; i++) {
    const x = 1.0 + i * 1.13, held = i === 9;
    bar(s, x, 4.65, 1.05, 0.5, held ? AMBER : CHIP, "site");
    T(s, held ? "held out" : "train", x, 4.65, 1.05, 0.5, { fontSize: 11, bold: true, color: held ? NAVY : GREY, align: "center", valign: "middle" });
  }
  T(s, "Ten rotations give an honest score for a new site. The LLM needs no training, so it is scored on the same 800 pages.", 1.0, 5.28, 11.2, 0.3, { fontSize: 12, color: GREY });
  bar(s, 0.7, 5.9, 11.93, 0.7, AMBERBG, "caveat");
  T(s, "Caveat: the labels come from LLM annotators, not domain experts. Treat them as provisional until DCR checks a sample by hand.", 0.95, 5.9, 11.45, 0.7, { fontSize: 13, bold: true, color: NAVY, valign: "middle" });
  s.addNotes("There were no labels, so we built an 800-page set: 80 per site, balanced across URL templates, with weights so we can estimate accuracy for the real page mix. Two independent annotators labelled every page from a written guide and a third pass settled the disagreements. The test that matters for the trained tiers is leave-one-site-out. The honest caveat: the annotators are LLMs, so this is a provisional standard until DCR checks a sample.");
}

// ================= 7. Results (cheap cascade) =================
{
  const s = frame(false, "QUALITY · CHEAP TIERS", "On a site it has never seen, the cheap tiers get 44% of types, 68% of audiences", 7);
  card(s, 0.7, 1.95, 7.95, 4.5, "light");
  const labels = ["Majority", "Zero-shot", "TF-IDF", "Embedding", "Rules*", "Fusion", "Cascade*"];
  s.addChart(pres.charts.BAR, [
    { name: "Page type", labels, values: [16, 17, 35, 38, 44, 44, 44] },
    { name: "Audience", labels, values: [53, 50, 65, 65, 54, 63, 68] },
  ], {
    x: 0.85, y: 2.05, w: 7.65, h: 4.3, barDir: "col", barGrouping: "clustered", barGapWidthPct: 55,
    chartColors: [BLUE, TEAL],
    showLegend: true, legendPos: "b", legendFontSize: 11, legendColor: GREY, legendFontFace: "Calibri",
    showValue: true, dataLabelFormatCode: '0"%"', dataLabelFontSize: 10, dataLabelColor: INK, dataLabelFontFace: "Calibri", dataLabelPosition: "outEnd",
    valAxisMinVal: 0, valAxisMaxVal: 100, valAxisMajorUnit: 25, valAxisLabelFormatCode: '0"%"', valAxisLabelColor: GREY, valAxisLabelFontSize: 10, valAxisLabelFontFace: "Calibri",
    catAxisLabelColor: INK, catAxisLabelFontSize: 11, catAxisLabelFontFace: "Calibri",
    valGridLine: { color: RULE, size: 0.75 }, catGridLine: { style: "none" },
  });
  card(s, 8.9, 1.95, 3.73, 1.4, "light");
  T(s, "44%", 9.15, 2.05, 1.6, 0.7, { fontSize: 38, bold: true, fontFace: "Cambria", color: BLUE });
  T(s, "of page types right on an unseen site", 9.15, 2.78, 3.3, 0.5, { fontSize: 13, color: GREY });
  card(s, 8.9, 3.5, 3.73, 1.4, "light");
  T(s, "68%", 9.15, 3.6, 1.6, 0.7, { fontSize: 38, bold: true, fontFace: "Cambria", color: TEAL });
  T(s, "of audiences right on an unseen site", 9.15, 4.33, 3.3, 0.5, { fontSize: 13, color: GREY });
  bar(s, 8.9, 5.05, 3.73, 1.4, CHIP, "chip");
  T(s, "Always guessing the majority (most common) label scores 16% on type and 53% on audience, so type is a real gain and audience adds little.", 9.1, 5.05, 3.35, 1.4, { fontSize: 13, bold: true, color: NAVY, valign: "middle" });
  T(s, "* Rules and cascade settings were revised after error analysis on the labelled pages, so these bars are optimistic. 800 pages, leave-one-site-out.", 0.7, 6.55, 11.93, 0.3, { fontSize: 11, color: GREY });
  s.addNotes("First result: the cheap tiers. On a site held out of training, the cascade gets 44% of page types and 68% of audiences right. A model that always guesses the most common label gets 16% and 53%, so there is real signal in type but audience is only slightly better than guessing. The rules and cascade bars are optimistic because we tuned the rules after looking at errors on the same labelled pages. Weighted to the real page mix, the cascade scores 53% on type and 70% on audience.");
}

// ================= 8. Gating (dark) =================
{
  const s = frame(true, "QUALITY · THE HARD PART", "The cheap tiers can't vouch for themselves, but more sites help", 8);
  card(s, 0.7, 1.95, 6.4, 3.6, DCARD);
  T(s, "Accuracy on a held-out site vs number of training sites", 0.95, 2.1, 5.9, 0.3, { fontSize: 13, bold: true, color: LBLUE });
  s.addChart(pres.charts.LINE, [
    { name: "Page type", labels: ["1", "2", "4", "6", "9"], values: [29, 30, 38, 42, 44] },
    { name: "Audience", labels: ["1", "2", "4", "6", "9"], values: [48, 52, 62, 58, 63] },
  ], {
    x: 0.85, y: 2.45, w: 6.1, h: 2.55, chartColors: [LBLUE, AMBER], lineSize: 3, lineDataSymbol: "circle", lineDataSymbolSize: 8,
    showLegend: true, legendPos: "b", legendFontSize: 11, legendColor: DTEXT, legendFontFace: "Calibri",
    showValue: true, dataLabelFormatCode: '0"%"', dataLabelFontSize: 10, dataLabelColor: DTITLE, dataLabelFontFace: "Calibri", dataLabelPosition: "t",
    valAxisMinVal: 20, valAxisMaxVal: 70, valAxisMajorUnit: 10, valAxisLabelFormatCode: '0"%"', valAxisLabelColor: DTEXT, valAxisLabelFontSize: 10, valAxisLabelFontFace: "Calibri",
    catAxisLabelColor: DTEXT, catAxisLabelFontSize: 10, catAxisLabelFontFace: "Calibri",
    valGridLine: { color: "2A3B5E", size: 0.75 }, catGridLine: { style: "none" },
  });
  T(s, "Same-site split: 56% type, 74% audience. Moving to a new site costs about 12 points.", 0.95, 5.05, 5.9, 0.4, { fontSize: 12, color: DTEXT });
  card(s, 7.3, 1.95, 5.33, 0.6, DCARD);
  T(s, "100% of pages pass through the confidence gate", 7.5, 1.95, 4.9, 0.6, { fontSize: 13, color: DTITLE, valign: "middle" });
  arrowD(s, 9.84, 2.6, LBLUE);
  card(s, 7.3, 3.0, 2.55, 2.55, DCARD);
  T(s, "2.8%", 7.5, 3.15, 2.15, 0.6, { fontSize: 30, bold: true, fontFace: "Cambria", color: DTITLE });
  T(s, "confident enough to sample", 7.5, 3.8, 2.15, 0.6, { fontSize: 13, color: DTEXT });
  T(s, "Type 82% and audience 95% correct", 7.5, 4.55, 2.15, 0.8, { fontSize: 12, color: DTEXT });
  card(s, 10.08, 3.0, 2.55, 2.55, WARN);
  T(s, "97.2%", 10.28, 3.15, 2.15, 0.6, { fontSize: 30, bold: true, fontFace: "Cambria", color: DTITLE });
  T(s, "sent to LLM review", 10.28, 3.8, 2.15, 0.6, { fontSize: 13, color: "F2E2C6" });
  T(s, "Type 43% and audience 67% correct", 10.28, 4.55, 2.15, 0.8, { fontSize: 12, color: WTEXT });
  bar(s, 0.7, 5.8, 11.93, 0.85, AMBER, "callout");
  T(s, "The proposal assumed 15–25% of pages would escalate. At today's accuracy it is about 97%, and no confidence threshold reaches 90% accuracy at useful coverage.", 0.95, 5.8, 11.45, 0.85, { fontSize: 14, bold: true, color: NAVY, valign: "middle" });
  s.addNotes("This is the finding that changes the plan for the cheap tiers. We calibrated the confidence scores, and they are honest, but honest confidence says 'not sure' for almost everything: 97% of pages go to review. The learning curve shows accuracy was still rising as we added training sites, so more labelled sites would help, but we cannot count on the cheap tiers to handle most pages today. Moving to a site the model has not seen costs about 12 points.");
}

// ================= 9. Haiku result =================
{
  const s = frame(false, "QUALITY · THE LLM TIER", "Haiku 5.5 on the same 800 pages: 81% page type, 90% audience", 9);
  card(s, 0.7, 1.95, 6.6, 3.85, "light");
  s.addChart(pres.charts.BAR, [
    { name: "Cheap cascade (unseen site)", labels: ["Page type", "Audience"], values: [44.1, 67.8] },
    { name: "Haiku 5.5", labels: ["Page type", "Audience"], values: [80.9, 90.4] },
  ], {
    x: 0.85, y: 2.05, w: 6.3, h: 3.65, barDir: "col", barGrouping: "clustered", barGapWidthPct: 70,
    chartColors: ["8A93A3", BLUE],
    showLegend: true, legendPos: "b", legendFontSize: 11, legendColor: GREY, legendFontFace: "Calibri",
    showValue: true, dataLabelFormatCode: '0.0"%"', dataLabelFontSize: 12, dataLabelColor: INK, dataLabelFontFace: "Calibri", dataLabelPosition: "outEnd",
    valAxisMinVal: 0, valAxisMaxVal: 100, valAxisMajorUnit: 25, valAxisLabelFormatCode: '0"%"', valAxisLabelColor: GREY, valAxisLabelFontSize: 10, valAxisLabelFontFace: "Calibri",
    catAxisLabelColor: INK, catAxisLabelFontSize: 12, catAxisLabelFontFace: "Calibri",
    valGridLine: { color: RULE, size: 0.75 }, catGridLine: { style: "none" },
  });
  card(s, 7.55, 1.95, 5.08, 1.2, "light");
  T(s, "80.9%", 7.8, 1.95, 1.75, 1.2, { fontSize: 36, bold: true, fontFace: "Cambria", color: BLUE, valign: "middle" });
  T(s, "of page types right (95% range 78–83%)", 9.6, 1.95, 2.9, 1.2, { fontSize: 13, color: GREY, valign: "middle" });
  card(s, 7.55, 3.3, 5.08, 1.2, "light");
  T(s, "90.4%", 7.8, 3.3, 1.75, 1.2, { fontSize: 36, bold: true, fontFace: "Cambria", color: TEAL, valign: "middle" });
  T(s, "of audiences right (95% range 88–92%)", 9.6, 3.3, 2.9, 1.2, { fontSize: 13, color: GREY, valign: "middle" });
  bar(s, 7.55, 4.65, 5.08, 1.15, CHIP, "chip");
  T(s, "Weighted to the real page mix: 88.8% type, 92.1% audience. On 329 pages only Haiku gets the type right; on 35 only the cascade does.", 7.75, 4.65, 4.7, 1.15, { fontSize: 12.5, bold: true, color: NAVY, valign: "middle" });
  bar(s, 0.7, 5.98, 11.93, 0.8, AMBERBG, "caveat");
  T(s, "Caveat: the labels come from LLM annotators using the same guide Haiku is given. Haiku agrees with each annotator on about 80% of types, while the two annotators agree with each other on 91%.", 0.95, 5.98, 11.45, 0.8, { fontSize: 13, bold: true, color: NAVY, valign: "middle" });
  s.addNotes("Second result: the LLM tier, measured. We ran Haiku 5.5 on all 800 labelled pages with the annotation guide as its instructions. It gets 81% of page types and 90% of audiences right, against 44% and 68% for the cheap cascade on the same pages. The 95% ranges come from resampling the 800 pages. The caveat matters: the labels were made by LLM annotators working from the same written guide, so this measures agreement with them, not proven truth. Haiku agrees with each annotator on about 80% of types, while the two annotators agree with each other on 91%, so Haiku is clearly below the labelling process itself.");
}

// ================= 10. Trust (dark) =================
{
  const s = frame(true, "QUALITY · CAN WE TRUST IT?", "When Haiku says “certain”, it is right 93% on type and 97% on audience", 10);
  const conf = [
    ["CERTAIN", "38.8% of pages", "Type 92.6% · Audience 97.4%", "310 pages. Type 95% range 89–95%.", DCARD, DTEXT],
    ["PROBABLE", "55.6% of pages", "Type 76.0% · Audience 87.6%", "445 pages.", DCARD, DTEXT],
    ["A GUESS", "5.6% of pages", "Type 48.9% · Audience 68.9%", "45 pages.", WARN, WTEXT],
  ];
  conf.forEach((c, i) => {
    const x = 0.7 + i * 4.06;
    card(s, x, 1.95, 3.81, 2.05, c[4]);
    T(s, c[0], x + 0.22, 2.1, 3.37, 0.3, { fontSize: 11, bold: true, color: i === 2 ? AMBER : LBLUE });
    T(s, c[1], x + 0.22, 2.42, 3.37, 0.5, { fontSize: 22, bold: true, fontFace: "Cambria", color: DTITLE });
    T(s, c[2], x + 0.22, 3.05, 3.37, 0.35, { fontSize: 14, bold: true, color: i === 2 ? "F2E2C6" : DTITLE });
    T(s, c[3], x + 0.22, 3.45, 3.37, 0.4, { fontSize: 12, color: c[5] });
  });
  const notes = [
    ["Errors are near neighbours", "Product Information read as Prescribing Information (12 pages). Disease & Therapy Area read as Homepage / Hub (9)."],
    ["Audience slips to “Unclear”", "General Public to Unclear on 15 pages, Healthcare Professional to Unclear on 13. Weakest type: R&D & Science, 36% of 14 pages."],
    ["Spread across sites", "Type 68–91% and audience 85–99% by site, against 28–55% and 25–84% for the cheap cascade."],
  ];
  notes.forEach((c, i) => {
    const x = 0.7 + i * 4.06;
    card(s, x, 4.15, 3.81, 1.65, DCARD2);
    T(s, c[0], x + 0.22, 4.27, 3.37, 0.3, { fontSize: 14, bold: true, fontFace: "Cambria", color: DTITLE });
    T(s, c[1], x + 0.22, 4.65, 3.37, 1.1, { fontSize: 12, color: DTEXT });
  });
  bar(s, 0.7, 5.95, 11.93, 0.8, AMBER, "rule check");
  T(s, "Rule we set before the run: Haiku should reach 90% on type and 95% on audience for pages it calls certain. Result: 92.6% and 97.4%. The rule is met, though the type result's 95% range starts at 89%.", 0.95, 5.95, 11.45, 0.8, { fontSize: 13, bold: true, color: NAVY, valign: "middle" });
  s.addNotes("How far to trust Haiku. Its own confidence ranks its errors well: pages it calls certain are 39% of the total and are right 93% of the time on type and 97% on audience; the 6% it calls a guess are right under half the time on type. Most mistakes are between neighbouring types, and the audience errors are mostly pages it calls Unclear. Accuracy by site ranges from 68 to 91% on type, against 28 to 55% for the cheap tiers. The 90% and 95% thresholds were our own choice, written down before we ran the pilot; the type result just clears it, with a 95% range that starts at 89%.");
}

// ================= 11. Finding =================
{
  const s = frame(false, "FINDING", "Audience is mostly a property of the site, and mismatches can be found", 11);
  card(s, 0.7, 1.95, 6.2, 4.55, "light");
  T(s, "Share of pages declaring “HCP only”, by site", 1.0, 2.12, 5.6, 0.35, { fontSize: 15, bold: true, fontFace: "Cambria", color: NAVY });
  s.addChart(pres.charts.BAR, [
    { name: "Pages declaring HCP only", labels: ["Corporate sites (highest of 5)", "medicalinformation.pt", "myastrazeneca.be", "myastrazeneca.co.uk", "azone.es", "medicalinformation (US)"], values: [1, 23, 54, 78, 93, 99] },
  ], {
    x: 0.9, y: 2.6, w: 5.8, h: 3.75, barDir: "bar", barGapWidthPct: 50, chartColors: [BLUE], showLegend: false,
    showValue: true, dataLabelFormatCode: '0"%"', dataLabelFontSize: 11, dataLabelColor: INK, dataLabelFontFace: "Calibri", dataLabelPosition: "outEnd",
    valAxisMinVal: 0, valAxisMaxVal: 100, valAxisMajorUnit: 25, valAxisLabelFormatCode: '0"%"', valAxisLabelColor: GREY, valAxisLabelFontSize: 10, valAxisLabelFontFace: "Calibri",
    catAxisLabelColor: INK, catAxisLabelFontSize: 11, catAxisLabelFontFace: "Calibri",
    valGridLine: { color: RULE, size: 0.75 }, catGridLine: { style: "none" },
  });
  const r = [
    ["45%", "of true HCP pages state “HCP only” on the page itself (52% counting their site's declaration)", BLUE],
    ["12 of 235", "pages counted as “HCP only” are patient-facing documents on sites that mostly declare it", "A33D1C"],
    ["0 labels", "needed for the site-level signal, so it works on any new scan", TEAL],
  ];
  r.forEach((c, i) => {
    const y = 1.95 + i * 1.6;
    card(s, 7.15, y, 5.48, 1.35, "light");
    T(s, c[0], 7.4, y, 2.1, 1.35, { fontSize: 28, bold: true, fontFace: "Cambria", color: c[2], valign: "middle" });
    T(s, c[1], 9.55, y, 2.9, 1.35, { fontSize: 13, color: GREY, valign: "middle" });
  });
  s.addNotes("Two things. First, audience is mostly a property of the site: on the HCP portals nearly every page carries an 'HCP only' statement, on the five corporate sites at most 1% do, and fewer than half of true HCP pages state it themselves (45%; 52% counting the site's declaration). Second, comparing the audience a page is declared to have with the audience its content suggests finds real candidates: of 235 labelled pages counted as HCP only, 12 are patient-facing documents, such as a medication guide and patient information on Lynparza and Tagrisso, sitting on sites that mostly declare HCP only. All 12 inherit the declaration from their site rather than stating it themselves. That is the mis-filed document case from the proposal. This was measured on the 800 labelled pages with the rule-based detector, not the LLM.");
}

// ================= 12. Prototype =================
{
  const s = frame(false, "PROTOTYPE · REAL OUTPUT", "The prototype: scan in, one classification per page out", 12);
  T(s, "Run on one full scan (1,342 pages, about 59 seconds of model time). These are the first rows of its output, from the cheap tiers.", 0.7, 1.55, 11.93, 0.35, { fontSize: 13, color: GREY });
  bar(s, 0.7, 2.05, 11.93, 0.55, NAVY, "command");
  T(s, "python scripts/classify_scan.py content/<site>/<id>/filetext.json -o out.jsonl", 0.95, 2.05, 11.4, 0.55, { fontSize: 13, fontFace: "Courier New", color: DTITLE, valign: "middle" });
  const hdr = ["Page", "Type", "Audience", "Confidence (type / audience)", "Status"].map((t) => tableCell(t, { bold: true, color: GREY, fontSize: 11, fill: { color: CHIP } }));
  const rows = [
    ["az-oncology.jp/", "Homepage / Hub", "Patient / Caregiver", "0.64 / 0.68", "llm_review"],
    ["az-oncology.jp/glossary/", "Patient Support", "Patient / Caregiver", "0.42 / 0.66", "llm_review"],
    ["az-oncology.jp/cancer_treatment/", "Patient Support", "Patient / Caregiver", "0.41 / 0.66", "llm_review"],
    ["searchmytrial.com/smt-sites/astrazeneca/", "R&D & Science", "Patient / Caregiver", "0.47 / 0.57", "llm_review"],
  ].map((r) => r.map((t) => tableCell(t, { fill: { color: "FFFFFF" }, fontSize: 12 })));
  s.addTable([hdr, ...rows], { x: 0.7, y: 2.85, w: 11.93, colW: [4.2, 2.0, 2.1, 2.25, 1.38], rowH: [0.4, 0.5, 0.5, 0.5, 0.5], border: TBORDER, margin: [5, 8, 5, 8], objectName: "output table" });
  const chips = [
    ["1,342 pages classified: 783 Patient Support, 350 Utility / Error, 76 Disease & Therapy Area", CHIP],
    ["Every row also carries the evidence behind it, such as the words that triggered a rule", CHIP],
    ["1,291 of 1,342 were routed to review: the gate says “not sure” and means it", AMBERBG],
  ];
  chips.forEach((c, i) => {
    const x = 0.7 + i * 4.06;
    bar(s, x, 5.65, 3.81, 1.0, c[1], "chip");
    T(s, c[0], x + 0.18, 5.65, 3.45, 1.0, { fontSize: 12, bold: true, color: NAVY, valign: "middle" });
  });
  s.addNotes("The prototype takes a raw scan file and returns one line per page with the page type, the audience, a confidence for each, the audience the page declares, the evidence, and a status that says whether to publish, sample or review. We ran it on two full scans, the larger one being 1,342 pages in about a minute of model time. Notice that all four of these rows are sent to review: with this much uncertainty the cheap tiers' gate is working as designed, which is why the LLM tier matters. The LLM tier is in the same package (llm_tier.py).");
}

// ================= 13. Speed and cost (dark) =================
{
  const s = frame(true, "SCALE & COST", "Speed and cost: measured for the CPU tiers and for Haiku 5.5", 13);
  card(s, 0.7, 1.95, 11.93, 0.65, DCARD);
  T(s, "100% of pages are cleaned and scored by the rules: about 186 pages per second per CPU core", 0.95, 1.95, 11.4, 0.65, { fontSize: 13, color: DTITLE, valign: "middle" });
  arrowD(s, 6.37, 2.66, LBLUE);
  card(s, 1.7, 3.0, 9.93, 0.65, DCARD);
  T(s, "Embedding model: about 30 pages per second on the whole 32-core VM, or about 9.4 hours per million pages", 1.9, 3.0, 9.55, 0.65, { fontSize: 13, color: DTITLE, valign: "middle", align: "center" });
  arrowD(s, 6.37, 3.7, AMBER);
  card(s, 0.7, 4.05, 11.93, 0.75, WARN);
  T(s, "Haiku 5.5, measured on 800 pages: $0.137 in total, or $0.17 per 1,000 pages (about $171 per million), at 4.3 pages per second with 8 parallel requests", 0.95, 4.05, 11.4, 0.75, { fontSize: 13, bold: true, color: "F2E2C6", valign: "middle" });
  const n = [
    "Prompt caching matters: the same run without it would have cost about $0.43 per 1,000 pages. Our pre-run estimate was $0.28.",
    "Classifying every page in the ten scans (10,625) would cost about $1.82, or $1.47 for the 8,622 de-duplicated units.",
    "At 8 parallel requests a million pages would take about 64 hours (extrapolated). The Batch API, not tested here, lists at half price.",
  ];
  n.forEach((t, i) => {
    const x = 0.7 + i * 4.06;
    card(s, x, 5.1, 3.81, 1.5, DCARD2);
    T(s, t, x + 0.2, 5.1, 3.41, 1.5, { fontSize: 12.5, color: DTEXT, valign: "middle" });
  });
  s.addNotes("The CPU tiers are fast: the rules run at about 186 pages a second per core and the embedding model at about 30 pages a second on the whole machine, which is about nine and a half hours for a million pages. The LLM cost is now measured, not estimated: 800 pages cost 14 cents, which is 17 cents per thousand pages. That depends on prompt caching, because the 2,900-token instruction block is the same for every page; without caching it would be 43 cents per thousand. Our earlier estimate of 28 cents was wrong in both directions. Speed was 4.3 pages a second with 8 parallel requests; the 64 hours per million is a straight extrapolation from that, and more concurrency or the batch API would change it. The batch discount is a list-price fact, not something we tested.");
}

// ================= 14. Assumptions =================
{
  const s = frame(false, "WHAT CHANGED", "Four assumptions in the proposal needed revisiting", 14);
  const h = ["The proposal assumed", "What we measured", "What we do instead"].map((t) => tableCell(t, { bold: true, color: GREY, fontSize: 11, fill: { color: CHIP } }));
  const data = [
    ["The scan's detected-language and translated-text fields can be used", "Both are empty in all 34,319 records", "We detect language from the text"],
    ["About 15–25% of pages escalate to an LLM", "Cheap tiers alone: about 97%. Haiku marks 39% of pages “certain”, at 93% type and 97% audience accuracy", "Haiku becomes the main classifier; humans review the uncertain part"],
    ["Clustering discovers the taxonomy", "Clusters follow site and clinical topic, not page function", "Clusters check and extend a hand-built list"],
    ["“HCP only” banners identify HCP pages", "Only 45% of HCP pages state one themselves, and navigation links look similar", "Use the site-level share and cue-word patterns"],
  ];
  const rows = data.map((r) => [tableCell(r[0], { fill: { color: "FFFFFF" }, fontSize: 13 }), tableCell(r[1], { fill: { color: "FFFFFF" }, fontSize: 13, bold: true }), tableCell(r[2], { fill: { color: "FFFFFF" }, fontSize: 13 })]);
  s.addTable([h, ...rows], { x: 0.7, y: 1.95, w: 11.93, colW: [4.0, 4.4, 3.53], rowH: [0.4, 0.95, 0.95, 0.95, 0.95], border: TBORDER, margin: [6, 9, 6, 9], objectName: "assumptions table" });
  T(s, "These come from our measurements on the ten site scans. The proposal itself flagged the 15–25% figure as illustrative.", 0.7, 6.3, 11.93, 0.4, { fontSize: 13, color: GREY });
  s.addNotes("Four things in the proposal did not survive contact with the data. The language fields are empty. The 15 to 25 percent escalation figure, which the proposal marked as illustrative, is about 97 percent for the cheap tiers; with Haiku, 39 percent of pages come back marked certain at 93 and 97 percent accuracy, and the rest need a human or a second opinion. Clustering did not produce a function-based taxonomy by itself. And the 'for HCPs only' banner is on fewer than half of HCP pages, and a menu link can look like one.");
}

// ================= 15. Issues (dark) =================
{
  const s = frame(true, "ISSUES", "Issues we hit this week, and where each one stands", 15);
  bar(s, 0.7, 1.85, 1.2, 0.32, TEAL, "tag");
  T(s, "FIXED", 0.7, 1.85, 1.2, 0.32, { fontSize: 12, bold: true, color: "FFFFFF", align: "center", valign: "middle" });
  bar(s, 6.78, 1.85, 1.6, 0.32, AMBER, "tag");
  T(s, "STILL OPEN", 6.78, 1.85, 1.6, 0.32, { fontSize: 12, bold: true, color: NAVY, align: "center", valign: "middle" });
  const fixed = [
    ["Page text was mostly menus and banners", "Removed per site by how often each line repeats. The raw header is kept because banners live there."],
    ["Site-specific words had leaked into the rules", "Found in error analysis, removed, and every result re-run."],
    ["Navigation links read as audience banners", "A menu link “Profesionales Sanitarios” was flagged as a declaration. Cue-word patterns fixed it."],
    ["LLM answers were being cut off", "The first Haiku run capped replies at 300 tokens and 152 of 800 failed. The cap is now 1,500 and all 800 reran cleanly."],
  ];
  const open = [
    ["Labels come from LLMs, not experts", "Haiku agrees with each annotator on about 80% of types; the two annotators agree with each other on 91%."],
    ["Rules were tuned on the labelled pages", "Rule and cascade scores are optimistic. A brand-new site is the real test."],
    ["Haiku has weak spots", "R&D & Science (36% of 14 pages), Product vs Prescribing Information (12 mix-ups) and the “Unclear” audience."],
    ["Rare page types are too thin to score", "Investor (7 labelled pages), Safety (6), Contact (9) and Media (13) need more examples."],
  ];
  const col = (items, x, fill, tcol) => items.forEach((it, i) => {
    const y = 2.35 + i * 1.12;
    card(s, x, y, 5.85, 1.0, fill);
    T(s, it[0], x + 0.22, y + 0.1, 5.4, 0.3, { fontSize: 14, bold: true, fontFace: "Cambria", color: DTITLE });
    T(s, it[1], x + 0.22, y + 0.45, 5.4, 0.5, { fontSize: 12, color: tcol });
  });
  col(fixed, 0.7, DCARD, DTEXT);
  col(open, 6.78, WARN, WTEXT);
  s.addNotes("Fixed: the page text was mostly boilerplate, so we strip it per site while keeping the header where banners live. Some site-specific words had leaked into the rules and inflated scores, so we removed them and re-ran every result. A navigation link was being read as an audience banner. And our first LLM run failed on 19 percent of pages because I had capped the reply length too low: the model writes a short reasoning step before its answer and ran out of room. We raised the cap and reran all 800 pages. Still open: the labels are LLM-made, the rules were tuned on the same labelled pages, Haiku has some weak spots, and some page types have too few examples to score.");
}

// ================= 16. Recommendation (dark) =================
{
  const s = frame(true, "RECOMMENDATION", "Recommendation: make Haiku 5.5 the main classifier, with a human check on uncertain pages", 16, 26);
  const ph = [
    ["NEXT", "Check the labels", "DCR labels 200 pages by hand. That pins accuracy to about ±5.5 points; 80 pages would give only ±8.8. Then freeze taxonomy v1.2.", false],
    ["THEN", "Test on a new site", "Run Haiku end to end on a site outside the ten, and report accuracy and the share of “certain” pages.", false],
    ["THEN", "Fix the weak spots", "Sharpen the guide where Haiku slips (Product vs Prescribing Information, R&D & Science, “Unclear” audience) and re-measure.", false],
    ["ONGOING", "Route and monitor", "Accept “certain” answers (39% of pages), review the rest. Track the certain-share and accuracy per site.", true],
  ];
  ph.forEach((p, i) => {
    const x = 0.7 + i * 3.04;
    card(s, x, 2.1, 2.84, 3.0, p[3] ? WARN : DCARD);
    T(s, p[0], x + 0.2, 2.3, 2.44, 0.3, { fontSize: 11, bold: true, color: p[3] ? AMBER : LBLUE });
    T(s, p[1], x + 0.2, 2.65, 2.44, 0.4, { fontSize: 15, bold: true, fontFace: "Cambria", color: DTITLE });
    T(s, p[2], x + 0.2, 3.15, 2.44, 1.85, { fontSize: 12, color: p[3] ? WTEXT : DTEXT });
    if (i < 3) s.addShape(pres.shapes.RECTANGLE, { x: x + 2.86, y: 3.6, w: 0.16, h: 0.16, fill: { color: LBLUE }, line: { color: LBLUE, width: 0 }, objectName: "step" });
  });
  bar(s, 0.7, 5.4, 11.93, 0.85, AMBER, "ask");
  T(s, "Proposed: Haiku 5.5 as the main classifier, humans on the uncertain pages. Measured cost: about $171 per million pages.", 0.95, 5.4, 11.45, 0.85, { fontSize: 14, bold: true, color: NAVY, valign: "middle" });
  s.addNotes("The data now supports a clear direction. The cheap tiers alone get 44 and 68 percent on a new site; Haiku 5.5 gets 81 and 90 percent on the same pages for about 17 cents per thousand pages, and its 'certain' answers, 39 percent of pages, are right 93 and 97 percent of the time. So we recommend Haiku as the main classifier with humans on the uncertain pages. That is a recommendation from one pilot on LLM-made labels, so the first step is a hand check of 200 pages, which pins the accuracy to about plus or minus 5.5 points (80 pages would only give 8.8, both at 80 percent accuracy). Then a brand-new site, then fixing the weak spots, then routing by confidence and monitoring per site. The 90 and 95 percent thresholds we set before the run are on slide 10.");
}

(async () => {
  await pres.writeFile({ fileName: OUT });
  await applyTheme(OUT, THEME);
  console.log("wrote", OUT);
  console.log(warns.length ? "FIT WARNINGS:\n" + warns.join("\n") : "no fit warnings");
})();
