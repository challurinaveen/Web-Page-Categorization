// Week-1 prototype review deck.
//
//   node scripts/deck/build_week1_deck.js ../Week1_Prototype_Review.pptx
//
// Design mirrors the client brief (Web_Page_Categorisation.pptx): 13.33x7.5, Cambria/Calibri,
// navy 11203A dark slides, F7F6F2 light slides, white rounded cards, amber E08E1D for risks.
// Every figure on every slide comes from results/*.json or the README - nothing is illustrative.
const path = require("path");
const pptxgen = require("pptxgenjs");
const SK = process.env.SKILL_DIR;
const { applyTheme } = require(path.join(SK, "scripts", "apply_theme.js"));

const OUT = process.argv[2] || "Week1_Prototype_Review.pptx";
const FOOT = "Web Page Categorisation — Week 1";

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

const NAVY = "11203A", INK = "1B2435", GREY = "5B6472", BLUE = "2F6FED", AMBER = "E08E1D";
const TEAL = "0F766E", RUST = "A33D1C", LBLUE = "8FB1F2", LIGHTBG = "F7F6F2", CHIP = "ECEAE2";
const DCARD = "192C4D", DTEXT = "C3CDE0", DTITLE = "F1F3F7", AMBERBG = "FCEFDC";

const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE";
pres.title = "Web Page Categorisation: week 1 prototype review";
pres.author = "Project team";
pres.theme = { headFontFace: "Cambria", bodyFontFace: "Calibri" };

const shadow = () => ({ type: "outer", color: "8A8578", blur: 9, offset: 2, angle: 90, opacity: 0.22 });

// ---------------------------------------------------------------- layouts

pres.defineSlideMaster({
  title: "COVER",
  background: { color: NAVY },
  objects: [
    { text: { text: "", options: { name: "title", placeholder: "title", x: 0.9, y: 2.25, w: 11.5, h: 1.5, fontSize: 44, bold: true, color: DTITLE, fontFace: "Cambria" } } },
    { text: { text: "", options: { name: "body", placeholder: "body", x: 0.9, y: 3.8, w: 10.6, h: 1.2, fontSize: 18, color: DTEXT, valign: "top" } } },
  ],
});

pres.defineSlideMaster({
  title: "LIGHT",
  background: { color: LIGHTBG },
  slideNumber: { x: 12.55, y: 7.02, w: 0.5, h: 0.3, fontSize: 10, color: GREY, align: "right" },
  objects: [
    { text: { text: "", options: { name: "title", placeholder: "title", x: 0.62, y: 0.42, w: 12.1, h: 0.75, fontSize: 32, bold: true, color: INK, fontFace: "Cambria", valign: "middle" } } },
    { text: { text: FOOT, options: { x: 0.62, y: 7.02, w: 6, h: 0.3, fontSize: 10, color: GREY, isTextBox: true } } },
  ],
});

pres.defineSlideMaster({
  title: "DARK",
  background: { color: NAVY },
  slideNumber: { x: 12.55, y: 7.02, w: 0.5, h: 0.3, fontSize: 10, color: "6B7A99", align: "right" },
  objects: [
    { text: { text: "", options: { name: "title", placeholder: "title", x: 0.62, y: 0.42, w: 12.1, h: 0.75, fontSize: 32, bold: true, color: DTITLE, fontFace: "Cambria", valign: "middle" } } },
    { text: { text: FOOT, options: { x: 0.62, y: 7.02, w: 6, h: 0.3, fontSize: 10, color: "6B7A99", isTextBox: true } } },
  ],
});

// ---------------------------------------------------------------- helpers

/** White rounded card. */
function card(s, x, y, w, h, name, fill) {
  s.addShape(pres.ShapeType.roundRect, {
    x, y, w, h, rectRadius: 0.07, fill: { color: fill || "FFFFFF" },
    line: { color: fill ? fill : "E4E1D8", width: 1 }, shadow: shadow(), objectName: name,
  });
}

/** Filled circle with a short label in it (number or 2-3 letters). */
function badge(s, x, y, d, label, fill, textColor) {
  s.addShape(pres.ShapeType.ellipse, { x, y, w: d, h: d, fill: { color: fill }, line: { color: fill, width: 1 }, objectName: "badge-" + label });
  s.addText(label, { x, y, w: d, h: d, align: "center", valign: "middle", fontSize: label.length > 2 ? 11 : 14, bold: true, color: textColor || "FFFFFF", margin: 0, isTextBox: true });
}

/** Big number + caption, for stat rows. */
function stat(s, x, y, w, value, label, color) {
  s.addText(value, { x, y, w, h: 0.78, fontSize: 40, bold: true, color, fontFace: "Cambria", align: "left", margin: 0, isTextBox: true });
  s.addText(label, { x, y: y + 0.78, w, h: 0.62, fontSize: 12, color: GREY, align: "left", margin: 0, isTextBox: true, valign: "top" });
}

// ---- code panels -------------------------------------------------------
const CODE_BG = "0D1830", CODE_TX = "D6DEEC", CODE_CM = "7E8CA8", CODE_ST = "E0B673";
const CODE_KW = "8FB1F2", CODE_FN = "7FD3C3";

/** Dark panel of monospaced code. `lines` items are a string, or [[text, colour], ...]. */
function codePanel(s, x, y, w, h, caption, lines, name, size) {
  s.addShape(pres.ShapeType.roundRect, {
    x, y, w, h, rectRadius: 0.05, fill: { color: CODE_BG },
    line: { color: "22365C", width: 1 }, objectName: name,
  });
  let top = y + 0.16;
  if (caption) {
    s.addText(caption, { x: x + 0.2, y: top, w: w - 0.4, h: 0.24, fontSize: 9.5, bold: true,
      color: CODE_CM, fontFace: "Courier New", charSpacing: 0.6, margin: 0, isTextBox: true });
    top += 0.3;
  }
  const runs = [];
  lines.forEach((ln, i) => {
    const parts = typeof ln === "string" ? [[ln, CODE_TX]] : ln;
    parts.forEach(([t, c], j) => runs.push({
      text: t, options: { color: c, breakLine: j === parts.length - 1 && i < lines.length - 1 },
    }));
  });
  s.addText(runs, { x: x + 0.2, y: top, w: w - 0.4, h: y + h - top - 0.14,
    fontSize: size || 9.5, fontFace: "Courier New", margin: 0, isTextBox: true,
    valign: "top", lineSpacingMultiple: 1.12 });
}

const CHART_BASE = {
  catAxisLabelColor: GREY, valAxisLabelColor: GREY,
  catAxisLabelFontFace: "+mn-lt", valAxisLabelFontFace: "+mn-lt",
  catAxisLabelFontSize: 11, valAxisLabelFontSize: 11,
  dataLabelColor: INK, dataLabelFontFace: "+mn-lt", dataLabelFontSize: 10,
  catGridLine: { style: "none" }, valGridLine: { color: "E4E1D8", size: 1 },
  catAxisLineShow: false, valAxisLineShow: false,
  showTitle: false, chartColors: [BLUE, TEAL],
};

const TITLE = { placeholder: "title", fontSize: 32, bold: true, fontFace: "Cambria", color: INK, valign: "middle" };
const TITLE_DK = Object.assign({}, TITLE, { color: DTITLE });

// ================================================================ 1. cover

pres.addSection({ title: "Opening" });
{
  const s = pres.addSlide({ masterName: "COVER", sectionTitle: "Opening" });
  s.addShape(pres.ShapeType.rect, { x: 0.9, y: 1.55, w: 1.1, h: 0.06, fill: { color: AMBER }, line: { color: AMBER, width: 0 }, objectName: "cover-mark" });
  s.addText("Web Page Categorisation", Object.assign({}, TITLE_DK, { fontSize: 44 }));
  s.addText("Week 1: a working prototype, a benchmark to judge it by, and the one result that changed the plan",
    { placeholder: "body", fontSize: 18, color: DTEXT, fontFace: "Calibri", valign: "top" });
  s.addText("Classifying page type and intended audience from URL and page text · 10 site scans, 34,319 records",
    { x: 0.9, y: 5.4, w: 11.5, h: 0.4, fontSize: 13, color: "7E8CA8", isTextBox: true });
  s.addNotes("Week 1 covered the whole loop: taxonomy, prototype, benchmark, and three measured approaches. "
    + "The headline is that the cheap approach the brief assumed does not clear the bar, and the LLM approach does, "
    + "for about $1.82 across all ten supplied scans.");
}

// ================================================================ 2. the brief

{
  const s = pres.addSlide({ masterName: "LIGHT", sectionTitle: "Opening" });
  s.addText("What the brief asks for", Object.assign({}, TITLE));

  const asks = [
    ["1", "Two labels per page", "Page type and intended audience, from the URL and page text only."],
    ["2", "A taxonomy we derive", "Not a predefined list — the categories have to come out of the data."],
    ["3", "Measured, not asserted", "Benchmark the accuracy and flag what is wrong or uncertain."],
    ["4", "Has to survive site #11", "Built on these sites, it still has to work on a site it has never seen."],
  ];
  asks.forEach(([n, h, d], i) => {
    const y = 1.42 + i * 1.28;
    card(s, 0.62, y, 7.25, 1.12, "ask-" + n);
    badge(s, 0.88, y + 0.32, 0.48, n, NAVY);
    s.addText(h, { x: 1.52, y: y + 0.17, w: 6.1, h: 0.33, fontSize: 15, bold: true, color: INK, margin: 0, isTextBox: true });
    s.addText(d, { x: 1.52, y: y + 0.53, w: 6.15, h: 0.44, fontSize: 12.5, color: GREY, margin: 0, isTextBox: true, valign: "top" });
  });

  card(s, 8.2, 1.42, 4.5, 4.96, "quote", NAVY);
  s.addText("The key question", { x: 8.55, y: 1.75, w: 3.8, h: 0.3, fontSize: 11, bold: true, color: AMBER, charSpacing: 1.2, margin: 0, isTextBox: true });
  s.addText("How can we accurately determine the type and intended audience of a web page at scale, while keeping the solution fast, repeatable and cost-effective?",
    { x: 8.55, y: 2.2, w: 3.82, h: 1.9, fontSize: 16, color: DTITLE, fontFace: "Cambria", italic: true, margin: 0, isTextBox: true, valign: "top", lineSpacingMultiple: 1.15 });
  s.addText("Week 1 answers it with measured numbers rather than an architecture.",
    { x: 8.55, y: 5.42, w: 3.82, h: 0.76, fontSize: 12, color: DTEXT, margin: 0, isTextBox: true, valign: "top" });
  s.addNotes("The fourth requirement is the hard one and it is the one that decided the week: anything tuned on these "
    + "ten sites has to be scored on a site held out of training, or the number is meaningless.");
}

// ================================================================ 3. what we built

pres.addSection({ title: "What we built" });
{
  const s = pres.addSlide({ masterName: "LIGHT", sectionTitle: "What we built" });
  s.addText("What we built this week", Object.assign({}, TITLE));

  const items = [
    ["TAX", "Taxonomy v1.1, derived from the data", "23 page types and 8 audiences, drafted from the corpus and then checked by embedding clustering. Type and audience are kept as two independent axes.", TEAL],
    ["CLI", "A working prototype", "One command: scan file in, one classification per page out, with the evidence for each. Runs all three tiers; tested on two full site scans.", BLUE],
    ["BM", "An 800-page benchmark", "80 pages per site, labelled twice independently and adjudicated, with sampling weights so population accuracy can be estimated.", NAVY],
    ["3T", "Three approaches, all measured", "Keyword rules, embeddings + logistic regression, and an LLM pass — each scored on sites held out of training.", RUST],
    ["WEB", "A crawler for unseen sites", "Turns any live website into the same scan format, so the prototype can be pointed at a site nobody supplied a scan for.", GREY],
  ];
  items.forEach(([tag, h, d, col], i) => {
    const y = 1.38 + i * 1.0;
    card(s, 0.62, y, 12.1, 0.88, "built-" + i);
    badge(s, 0.86, y + 0.2, 0.48, tag, col);
    s.addText(h, { x: 1.52, y: y + 0.11, w: 4.9, h: 0.33, fontSize: 14.5, bold: true, color: INK, margin: 0, isTextBox: true });
    s.addText(d, { x: 6.5, y: y + 0.11, w: 6.0, h: 0.66, fontSize: 12, color: GREY, margin: 0, isTextBox: true, valign: "top" });
  });

  s.addText("All of it reproducible from the repository: 17 offline checks pass with no API key and no model download.",
    { x: 0.62, y: 6.44, w: 11.4, h: 0.32, fontSize: 11.5, italic: true, color: TEAL, margin: 0, isTextBox: true });
  s.addNotes("The crawler matters more than it looks: it is how we can test the 'site #11' question at all without "
    + "waiting for another DCR scan.");
}

// ================================================================ 4. the data

{
  const s = pres.addSlide({ masterName: "LIGHT", sectionTitle: "What we built" });
  s.addText("The data we ran it on", Object.assign({}, TITLE));

  card(s, 0.62, 1.38, 12.1, 1.72, "stats");
  const stats = [
    ["10", "AstraZeneca-family\nsite scans", NAVY],
    ["34,319", "records in total\n(1.1 GB of JSON)", NAVY],
    ["10,625", "are classifiable pages\n7,195 HTML + 3,430 PDF", BLUE],
    ["31%", "point at external domains\nPubMed, NICE, EMA, CMS", AMBER],
    ["12+", "languages detected\nen 58%, es 13%, ja 13%", TEAL],
  ];
  stats.forEach(([v, l, c], i) => {
    stat(s, 0.95 + i * 2.4, 1.6, 2.25, v, l, c);
  });

  card(s, 0.62, 3.28, 5.95, 1.5, "dedupe");
  s.addText("Templates dominate a crawl", { x: 0.92, y: 3.46, w: 5.3, h: 0.32, fontSize: 14.5, bold: true, color: INK, margin: 0, isTextBox: true });
  s.addText("10,625 pages collapse to 8,622 distinct units across 3,082 URL templates — 513 congress-PDF viewers on one site alone. Naive sampling flatters any model, so the benchmark reports template-balanced and population-weighted accuracy side by side.",
    { x: 0.92, y: 3.82, w: 5.35, h: 0.92, fontSize: 11.5, color: GREY, margin: 0, isTextBox: true, valign: "top" });

  card(s, 6.77, 3.28, 5.95, 1.5, "lang", AMBERBG);
  s.addText("One assumption in the brief did not hold", { x: 7.07, y: 3.46, w: 5.3, h: 0.32, fontSize: 14.5, bold: true, color: RUST, margin: 0, isTextBox: true });
  s.addText("The brief’s approach reads the scan’s detected-language and auto-translated-text fields. Both are empty in all 34,319 records. The prototype therefore detects language itself, from the text.",
    { x: 7.07, y: 3.82, w: 5.35, h: 0.92, fontSize: 11.5, color: "6B4A20", margin: 0, isTextBox: true, valign: "top" });

  card(s, 0.62, 4.96, 12.1, 1.34, "boiler");
  s.addText("Boilerplate is the real text-quality problem", { x: 0.92, y: 5.14, w: 7, h: 0.32, fontSize: 14.5, bold: true, color: INK, margin: 0, isTextBox: true });
  s.addText("On template-driven sites most of a page’s text is navigation, cookie banner and footer. We strip it per host by line frequency — a line appearing on 30% or more of a host’s pages is boilerplate — but keep the raw page header as a separate signal, because the header is where the audience is declared.",
    { x: 0.92, y: 5.5, w: 11.5, h: 0.66, fontSize: 11.5, color: GREY, margin: 0, isTextBox: true, valign: "top" });
  s.addNotes("No ground-truth labels were supplied with the data, which is why building a benchmark was week-1 work "
    + "rather than week-3 work.");
}

// ================================================================ 5. the approach

{
  const s = pres.addSlide({ masterName: "LIGHT", sectionTitle: "What we built" });
  s.addText("The approach: three tiers, cheapest first", Object.assign({}, TITLE));

  const tiers = [
    ["Tier 1", "Keyword and URL rules", "190 pages/s/core", "free", "Multilingual keyword, URL and structure patterns. No model to load. Attaches the matched evidence to every label.", TEAL],
    ["Tier 2", "Embeddings + logistic regression", "30 pages/s", "free", "e5-small embeddings of content and header, fused with the rule evidence and host context. Outputs a calibrated confidence.", BLUE],
    ["Tier 3", "Claude Haiku 5.5 reads the page", "4.3 pages/s", "$0.17 / 1,000", "The annotation guide is the system prompt, cached. Returns a label, a 1–3 confidence and a short evidence quote.", NAVY],
  ];
  tiers.forEach(([t, h, speed, cost, d, col], i) => {
    const x = 0.62 + i * 4.09;
    card(s, x, 1.4, 3.84, 3.5, "tier-" + i);
    s.addShape(pres.ShapeType.rect, { x: x + 0.3, y: 1.68, w: 0.42, h: 0.05, fill: { color: col }, line: { color: col, width: 0 }, objectName: "tiermark-" + i });
    s.addText(t, { x: x + 0.3, y: 1.84, w: 3.2, h: 0.3, fontSize: 11, bold: true, color: col, charSpacing: 1.2, margin: 0, isTextBox: true });
    s.addText(h, { x: x + 0.3, y: 2.16, w: 3.26, h: 0.78, fontSize: 17, bold: true, color: INK, fontFace: "Cambria", margin: 0, isTextBox: true, valign: "top" });
    s.addText(d, { x: x + 0.3, y: 3.0, w: 3.26, h: 1.1, fontSize: 11.5, color: GREY, margin: 0, isTextBox: true, valign: "top" });
    s.addShape(pres.ShapeType.roundRect, { x: x + 0.3, y: 4.18, w: 1.5, h: 0.42, rectRadius: 0.06, fill: { color: CHIP }, line: { color: CHIP, width: 0 }, objectName: "speed-" + i });
    s.addText(speed, { x: x + 0.3, y: 4.18, w: 1.5, h: 0.42, align: "center", valign: "middle", fontSize: 10.5, color: INK, margin: 0, isTextBox: true });
    s.addShape(pres.ShapeType.roundRect, { x: x + 1.92, y: 4.18, w: 1.64, h: 0.42, rectRadius: 0.06, fill: { color: i === 2 ? NAVY : CHIP }, line: { color: i === 2 ? NAVY : CHIP, width: 0 }, objectName: "cost-" + i });
    s.addText(cost, { x: x + 1.92, y: 4.18, w: 1.64, h: 0.42, align: "center", valign: "middle", fontSize: 10.5, bold: i === 2, color: i === 2 ? "FFFFFF" : INK, margin: 0, isTextBox: true });
    if (i < 2) {
      s.addText("›", { x: x + 3.86, y: 2.75, w: 0.3, h: 0.5, align: "center", valign: "middle", fontSize: 26, color: "B8B3A5", margin: 0, isTextBox: true });
    }
  });

  card(s, 0.62, 5.08, 12.1, 1.3, "gate");
  s.addText("Between the tiers sits a confidence gate", { x: 0.92, y: 5.26, w: 7, h: 0.32, fontSize: 14.5, bold: true, color: INK, margin: 0, isTextBox: true });
  s.addText("Each page falls through until something is confident enough. Every answer carries a calibrated probability that it is correct, and a status: auto ships, sampled ships but is audited, llm_review escalates, human_review goes to a person. Tier 3 is the only part that costs money, so it is off unless asked for and sends nothing without an explicit --yes.",
    { x: 0.92, y: 5.62, w: 11.5, h: 0.64, fontSize: 11.5, color: GREY, margin: 0, isTextBox: true, valign: "top" });
  s.addNotes("Type and audience are scored as two separate axes. Audience is split further into declared "
    + "(the page says 'for HCPs only') and content-based, so the two can be compared — that comparison is finding 4.");
}

// ================================================================ 6. the code

{
  const s = pres.addSlide({ masterName: "LIGHT", sectionTitle: "What we built" });
  s.addText("The code that does it", Object.assign({}, TITLE));
  s.addText("Two extracts from the library, unedited. The whole prototype is about 1,100 lines of Python across eight modules.",
    { x: 0.62, y: 1.2, w: 12.1, h: 0.32, fontSize: 12.5, color: GREY, margin: 0, isTextBox: true });

  codePanel(s, 0.62, 1.62, 6.26, 4.5, "src/pagecat/llm_tier.py  —  tier 3", [
    [["SCHEMA", CODE_KW], [" = {", CODE_TX], ['"type"', CODE_ST], [": ", CODE_TX], ['"object"', CODE_ST], [", ", CODE_TX], ['"properties"', CODE_ST], [": {", CODE_TX]],
    [['    "type"', CODE_ST], [":       {", CODE_TX], ['"enum"', CODE_ST], [": TYPES},   ", CODE_TX], ["# 23 types", CODE_CM]],
    [['    "audience"', CODE_ST], [":   {", CODE_TX], ['"enum"', CODE_ST], [": AUD},     ", CODE_TX], ["# 8 audiences", CODE_CM]],
    [['    "confidence"', CODE_ST], [": {", CODE_TX], ['"enum"', CODE_ST], [": [1, 2, 3]},", CODE_TX]],
    [['    "evidence"', CODE_ST], [":   {", CODE_TX], ['"type"', CODE_ST], [": ", CODE_TX], ['"string"', CODE_ST], ["}}}", CODE_TX]],
    "",
    [["def ", CODE_KW], ["classify", CODE_FN], ["(client, row, model=", CODE_TX], ["None", CODE_KW], ["):", CODE_TX]],
    [["    system = [{", CODE_TX], ['"text"', CODE_ST], [": open(GUIDE_PATH).read(),", CODE_TX]],
    [["               ", CODE_TX], ['"cache_control"', CODE_ST], [": {", CODE_TX], ['"type"', CODE_ST], [": ", CODE_TX], ['"ephemeral"', CODE_ST], ["}}]", CODE_TX]],
    [["    ", CODE_TX], ["# the guide is identical every call, so it caches:", CODE_CM]],
    [["    ", CODE_TX], ["# $0.43 -> $0.17 per 1,000 pages", CODE_CM]],
    [["    r = client.messages.", CODE_TX], ["create", CODE_FN], ["(", CODE_TX]],
    [["        model=model ", CODE_TX], ["or", CODE_KW], [" MODEL, max_tokens=", CODE_TX], ["1500", CODE_FN], [",", CODE_TX]],
    [["        system=system, output_config={", CODE_TX]],
    [['            "format"', CODE_ST], [": {", CODE_TX], ['"type"', CODE_ST], [": ", CODE_TX], ['"json_schema"', CODE_ST], [",", CODE_TX]],
    [['                       "schema"', CODE_ST], [": SCHEMA}},", CODE_TX]],
    [["        messages=[{", CODE_TX], ['"role"', CODE_ST], [": ", CODE_TX], ['"user"', CODE_ST], [", ", CODE_TX], ['"content"', CODE_ST], [": page_view(row)}])", CODE_TX]],
    "",
    [["    ", CODE_TX], ["if", CODE_KW], [" r.stop_reason == ", CODE_TX], ['"refusal"', CODE_ST], [":  ", CODE_TX], ["# never guess", CODE_CM]],
    [["        ", CODE_TX], ["return", CODE_KW], [" dict(type=", CODE_TX], ['"Other"', CODE_ST], [", confidence=", CODE_TX], ["1", CODE_FN], [")", CODE_TX]],
    [["    ", CODE_TX], ["return", CODE_KW], [" json.loads(text)", CODE_TX]],
  ], "code-llm");

  codePanel(s, 7.08, 1.62, 5.64, 4.5, "src/pagecat/cascade.py  —  the gate", [
    [["LLM_STATUS = {", CODE_TX], ["3", CODE_FN], [": ", CODE_TX], ['"auto"', CODE_ST], [", ", CODE_TX], ["2", CODE_FN], [": ", CODE_TX], ['"sampled"', CODE_ST], [",", CODE_TX]],
    [["              ", CODE_TX], ["1", CODE_FN], [": ", CODE_TX], ['"human_review"', CODE_ST], [", ", CODE_TX], ["0", CODE_FN], [": ", CODE_TX], ['"llm_error"', CODE_ST], ["}", CODE_TX]],
    "",
    [["def ", CODE_KW], ["apply_llm", CODE_FN], ["(preds, idx, answers):", CODE_TX]],
    [["  ", CODE_TX], ["for", CODE_KW], [" i, a ", CODE_TX], ["in", CODE_KW], [" zip(idx, answers):", CODE_TX]],
    [["    p = preds[i]", CODE_TX]],
    [["    p.cascade_type = p.page_type   ", CODE_TX], ["# keep", CODE_CM]],
    [["    p.page_type  = a[", CODE_TX], ['"type"', CODE_ST], ["]", CODE_TX]],
    [["    p.audience   = a[", CODE_TX], ['"audience"', CODE_ST], ["]", CODE_TX]],
    [["    p.type_conf  = CONF_ACC[a[", CODE_TX], ['"confidence"', CODE_ST], ["]]", CODE_TX]],
    [["    p.agree_type = p.page_type == p.cascade_type", CODE_TX]],
    [["    p.status = LLM_STATUS[a[", CODE_TX], ['"confidence"', CODE_ST], ["]]", CODE_TX]],
    "",
    [["# src/pagecat/rules.py — URL rules anchor on the", CODE_CM]],
    [["# left, so 'form' cannot fire inside", CODE_CM]],
    [["# 'medicalinformation'. Two guards were added", CODE_CM]],
    [["# after the off-domain test found them misfiring.", CODE_CM]],
    [['("u", R(r"', CODE_TX], ["form(?!at)", CODE_ST], ['|formulario|..."), 3.0),', CODE_TX]],
    [['("u", R(r"estudo|', CODE_TX], ["data(?!set)", CODE_ST], ['"),      1.6),', CODE_TX]],
  ], "code-cascade");

  s.addText("Every label carries the evidence that produced it, and one confidence that means the same thing in all three tiers: the measured probability the answer is correct.",
    { x: 0.62, y: 6.3, w: 12.1, h: 0.34, fontSize: 11.5, italic: true, color: TEAL, margin: 0, isTextBox: true });
  s.addNotes("Two details worth pointing at. The cached system block is the whole cost story — the annotation guide "
    + "is 2,923 tokens and identical on every request, so it is read at a tenth of list price. And the cheap tier's "
    + "answer is never thrown away: the two tiers agreeing is itself worth 88.3% accuracy.");
}

// ================================================================ 7. how we measure

pres.addSection({ title: "Evidence" });
{
  const s = pres.addSlide({ masterName: "LIGHT", sectionTitle: "Evidence" });
  s.addText("How we measure it", Object.assign({}, TITLE));

  card(s, 0.62, 1.4, 5.95, 2.62, "goldset");
  s.addText("The benchmark set", { x: 0.92, y: 1.6, w: 5.3, h: 0.32, fontSize: 14.5, bold: true, color: INK, margin: 0, isTextBox: true });
  const points = [
    "800 pages — 80 from each of the 10 sites",
    "Stratified by site and URL template, with quotas near the population (32% external, 23% PDF)",
    "Inverse-probability weights, so population-level accuracy can be estimated and not just guessed",
    "Labelled twice, independently, from one written guide; a third pass adjudicated the 89 disagreements",
  ];
  s.addText(points.map((t, i) => ({ text: t, options: { bullet: { code: "2022", indent: 12 }, breakLine: i < points.length - 1, paraSpaceAfter: 7 } })),
    { x: 0.94, y: 2.02, w: 5.4, h: 1.9, fontSize: 11.5, color: GREY, margin: 0, isTextBox: true, valign: "top" });

  card(s, 6.77, 1.4, 5.95, 2.62, "kappa");
  s.addText("Do the labellers agree?", { x: 7.07, y: 1.6, w: 5.3, h: 0.32, fontSize: 14.5, bold: true, color: INK, margin: 0, isTextBox: true });
  s.addTable(
    [[{ text: "", options: { fill: { color: "FFFFFF" } } }, { text: "Raw", options: { bold: true, color: GREY, align: "center" } }, { text: "Cohen’s κ", options: { bold: true, color: GREY, align: "center" } }],
     [{ text: "Page type", options: { color: INK } }, { text: "91.3%", options: { align: "center", color: INK } }, { text: "0.905", options: { align: "center", bold: true, color: TEAL } }],
     [{ text: "Audience", options: { color: INK } }, { text: "97.0%", options: { align: "center", color: INK } }, { text: "0.952", options: { align: "center", bold: true, color: TEAL } }]],
    { x: 7.07, y: 2.04, w: 5.35, colW: [2.15, 1.6, 1.6], rowH: 0.36, fontSize: 12, fontFace: "+mn-lt", border: { type: "solid", color: "EDEAE1", pt: 1 }, fill: { color: "FFFFFF" } });
  s.addText("The task is well defined: two labellers working from the same guide land on the same answer almost always, and 99.5% of the time when both call themselves certain. That is the ceiling any classifier is measured against.",
    { x: 7.07, y: 3.2, w: 5.35, h: 0.74, fontSize: 11.5, color: GREY, margin: 0, isTextBox: true, valign: "top" });

  card(s, 0.62, 4.24, 12.1, 2.02, "honest", AMBERBG);
  badge(s, 0.92, 4.5, 0.46, "!", AMBER);
  s.addText("The one caveat that applies to every number in this deck", { x: 1.58, y: 4.5, w: 9, h: 0.34, fontSize: 15, bold: true, color: RUST, margin: 0, isTextBox: true });
  s.addText("Both labellers are LLMs working from the same written guide, and that same guide is the system prompt given to the tier-3 model. So the accuracy figures are agreement with a consistent, documented process — not proven ground truth, and the two labellers' errors are correlated, which makes κ an upper bound for independent humans. The set should be treated as silver until a human spot-check. 200 human-checked pages would pin accuracy to about ±5.5 points; 80 pages only ±8.8.",
    { x: 1.58, y: 4.92, w: 10.8, h: 1.2, fontSize: 12.5, color: "6B4A20", margin: 0, isTextBox: true, valign: "top", lineSpacingMultiple: 1.1 });
  s.addNotes("We say this early and keep saying it. The benchmark is good enough to rank approaches against each "
    + "other, which is what week 1 needed. It is not yet good enough to quote an absolute accuracy to a client.");
}

// ================================================================ 7. generalisation chart

{
  const s = pres.addSlide({ masterName: "LIGHT", sectionTitle: "Evidence" });
  s.addText("Trained on nine sites, scored on the tenth", Object.assign({}, TITLE));

  const labels = ["Majority class", "Zero-shot embedding", "TF-IDF + logistic reg.", "Embeddings + logistic reg.",
    "Rules (tier 1)", "Cascade (tiers 1–2)", "Haiku 5.5 (tier 3)"];
  s.addChart(pres.ChartType.bar, [
    { name: "Page type", labels, values: [15.9, 16.9, 35.4, 37.6, 44.3, 44.1, 80.9] },
    { name: "Audience", labels, values: [52.9, 49.5, 65.1, 65.3, 54.1, 67.6, 90.4] },
  ], Object.assign({}, CHART_BASE, {
    x: 0.5, y: 1.4, w: 8.35, h: 5.3, barDir: "bar", barGapWidthPct: 45,
    showValue: true, dataLabelPosition: "outEnd", dataLabelFormatCode: '0"%"',
    showLegend: true, legendPos: "t", legendColor: GREY, legendFontFace: "+mn-lt", legendFontSize: 11,
    valAxisMaxVal: 100, valAxisMajorUnit: 25, valAxisLabelFormatCode: '0"%"',
  }));

  card(s, 9.0, 1.4, 3.72, 2.3, "readit");
  s.addText("What the chart says", { x: 9.28, y: 1.58, w: 3.2, h: 0.3, fontSize: 13.5, bold: true, color: INK, margin: 0, isTextBox: true });
  s.addText("Every site is held out of training in turn and scored cold, then rotated — so these are the numbers for a site the model has never seen. The cheap tiers cluster around 44% on type. The LLM tier nearly doubles it.",
    { x: 9.28, y: 1.95, w: 3.2, h: 1.6, fontSize: 11.5, color: GREY, margin: 0, isTextBox: true, valign: "top" });

  card(s, 9.0, 3.9, 3.72, 2.8, "why", NAVY);
  s.addText("Why the cheap tiers stall", { x: 9.28, y: 4.08, w: 3.2, h: 0.3, fontSize: 13.5, bold: true, color: AMBER, margin: 0, isTextBox: true });
  s.addText("Not plateaued — label-starved. Accuracy still climbs with every site added (type 29% at one site, 44% at nine). Moving from the same sites to new sites costs about 12 points. More labelled sites is where accuracy would come from.",
    { x: 9.28, y: 4.45, w: 3.2, h: 2.0, fontSize: 11.5, color: DTEXT, margin: 0, isTextBox: true, valign: "top" });
  s.addNotes("Rules and cascade thresholds were revised after error analysis on this same gold set, so those two bars "
    + "are optimistic. Site-specific tokens that had leaked into early rules were found and removed and everything re-run.");
}

// ================================================================ 8. the result that changed the plan

{
  const s = pres.addSlide({ masterName: "DARK", sectionTitle: "Evidence" });
  s.addText("The result that changed the plan", Object.assign({}, TITLE_DK));

  const cols = [
    ["The plan we started with", "Cheap tiers do the work;\nan LLM handles 15–25% of hard cases", [
      ["44%", "page type, unseen site"], ["68%", "audience, unseen site"], ["97%", "of pages still come out “unsure”"]],
      DCARD, LBLUE, "6B7A99"],
    ["What the numbers support", "An LLM does the work;\ncheap tiers filter, prioritise and monitor", [
      ["80.9%", "page type, unseen site"], ["90.4%", "audience, unseen site"], ["$0.17", "per 1,000 pages, measured"]],
      "FFFFFF", NAVY, GREY],
  ];
  cols.forEach(([h, sub, rows, fill, headCol, subCol], i) => {
    const x = 0.62 + i * 6.3;
    s.addShape(pres.ShapeType.roundRect, { x, y: 1.4, w: 5.8, h: 4.3, rectRadius: 0.07, fill: { color: fill }, line: { color: i === 0 ? "2A3C5E" : fill, width: 1 }, objectName: "col-" + i });
    s.addText(h, { x: x + 0.34, y: 1.66, w: 5.1, h: 0.34, fontSize: 11, bold: true, color: i === 0 ? "6B7A99" : AMBER, charSpacing: 1.2, margin: 0, isTextBox: true });
    s.addText(sub, { x: x + 0.34, y: 2.02, w: 5.14, h: 0.9, fontSize: 17, bold: true, color: headCol, fontFace: "Cambria", margin: 0, isTextBox: true, valign: "top" });
    rows.forEach(([v, l], j) => {
      const y = 3.06 + j * 0.85;
      s.addText(v, { x: x + 0.34, y, w: 1.75, h: 0.6, fontSize: 28, bold: true, color: i === 0 ? LBLUE : NAVY, fontFace: "Cambria", margin: 0, isTextBox: true });
      s.addText(l, { x: x + 2.18, y: y + 0.12, w: 3.3, h: 0.5, fontSize: 12, color: subCol, margin: 0, isTextBox: true, valign: "top" });
    });
  });
  s.addText("→", { x: 6.42, y: 3.3, w: 0.5, h: 0.5, align: "center", valign: "middle", fontSize: 24, color: AMBER, margin: 0, isTextBox: true });

  s.addText("On the same 800 pages, 329 are classified correctly only by the LLM tier and 35 only by the cheap tiers. The LLM’s own confidence ranks its errors: the 39% of pages it calls certain are 92.6% and 97.4% correct — which is what makes routing on it defensible.",
    { x: 0.62, y: 5.95, w: 12.1, h: 0.8, fontSize: 12.5, color: DTEXT, margin: 0, isTextBox: true, valign: "top" });
  s.addNotes("This is the slide to linger on. The recommendation in the report flipped on this evidence: the LLM is the "
    + "primary classifier, not the fallback. Sonnet was not run, so there is no measured case for spending 20x more.");
}

// ================================================================ 9. cost and speed

{
  const s = pres.addSlide({ masterName: "LIGHT", sectionTitle: "Evidence" });
  s.addText("What it costs to run", Object.assign({}, TITLE));

  card(s, 0.62, 1.4, 7.6, 3.1, "costtable");
  s.addText("Measured on the 800-page run", { x: 0.92, y: 1.6, w: 7, h: 0.32, fontSize: 14.5, bold: true, color: INK, margin: 0, isTextBox: true });
  const hdr = (t) => ({ text: t, options: { bold: true, color: GREY, fontSize: 11 } });
  s.addTable([
    [hdr("Stage"), hdr("Throughput"), hdr("Cost per 1,000 pages")],
    [{ text: "Featurise (boilerplate, title, language)" }, { text: "170 pages/s/core" }, { text: "free" }],
    [{ text: "Tier 1 — rules" }, { text: "190 pages/s/core" }, { text: "free" }],
    [{ text: "Tier 2 — embeddings (CPU, no GPU)" }, { text: "30 pages/s" }, { text: "free (9.4 VM-hours per million)" }],
    [{ text: "Tier 3 — Haiku 5.5, 8 parallel requests", options: { bold: true } }, { text: "4.3 pages/s", options: { bold: true } }, { text: "$0.171", options: { bold: true, color: TEAL } }],
    [{ text: "Tier 3 without prompt caching", options: { color: GREY } }, { text: "—", options: { color: GREY } }, { text: "$0.43", options: { color: GREY } }],
  ], { x: 0.92, y: 2.04, w: 7.0, colW: [3.1, 1.75, 2.15], rowH: 0.37, fontSize: 11.5, fontFace: "+mn-lt", color: INK, border: { type: "solid", color: "EDEAE1", pt: 1 }, fill: { color: "FFFFFF" }, valign: "middle" });

  card(s, 8.42, 1.4, 4.3, 3.1, "bigcost", NAVY);
  s.addText("$1.82", { x: 8.72, y: 1.78, w: 3.7, h: 1.0, fontSize: 52, bold: true, color: "FFFFFF", fontFace: "Cambria", margin: 0, isTextBox: true });
  s.addText("to classify all 10,625 pages of the ten supplied scans with the LLM tier",
    { x: 8.72, y: 2.82, w: 3.7, h: 0.8, fontSize: 13, color: DTEXT, margin: 0, isTextBox: true, valign: "top" });
  s.addText("Caching the guide — identical on every request — is what takes $0.43 down to $0.17.",
    { x: 8.72, y: 3.64, w: 3.7, h: 0.66, fontSize: 11.5, color: LBLUE, margin: 0, isTextBox: true, valign: "top" });

  card(s, 0.62, 4.72, 12.1, 1.86, "levers");
  s.addText("Three levers that cut the bill further, none of them yet applied", { x: 0.92, y: 4.9, w: 8, h: 0.32, fontSize: 14.5, bold: true, color: INK, margin: 0, isTextBox: true });
  [["Collapse templates", "10,625 pages are 8,622 distinct units here, and more collapses on heavily templated sites. Classify one page per template and propagate with a consistency check."],
   ["Only classify what changed", "On a re-scan, most pages are identical. Ongoing cost is marginal rather than a fresh full run."],
   ["Batch API", "Half list price for work that is not time-critical. A list-price fact, not something we tested."]].forEach(([h, d], i) => {
    const x = 0.92 + i * 3.95;
    s.addText(h, { x, y: 5.3, w: 3.6, h: 0.3, fontSize: 12.5, bold: true, color: TEAL, margin: 0, isTextBox: true });
    s.addText(d, { x, y: 5.62, w: 3.65, h: 0.86, fontSize: 11, color: GREY, margin: 0, isTextBox: true, valign: "top" });
  });
  s.addNotes("The 64-hours-per-million extrapolation and the Batch API discount are not tested. Everything else on "
    + "this slide was measured on the shared 32-vCPU CPU VM, with another process using about nine cores, so it is conservative.");
}

// ================================================================ 10. site-level audience

{
  const s = pres.addSlide({ masterName: "LIGHT", sectionTitle: "Evidence" });
  s.addText("Audience is mostly a property of the site, not the page", Object.assign({}, TITLE));

  const hosts = ["5 corporate sites", "medicalinformation.pt", "myastrazeneca.be", "myastrazeneca.co.uk", "azone.es", "medicalinformation (US)"];
  s.addChart(pres.ChartType.bar, [
    { name: "Pages declaring HCP-only", labels: hosts, values: [1, 23, 54, 78, 93, 99] },
  ], Object.assign({}, CHART_BASE, {
    x: 0.5, y: 1.4, w: 8.35, h: 5.3, barDir: "bar", barGapWidthPct: 40,
    chartColors: [NAVY], showValue: true, dataLabelPosition: "outEnd", dataLabelFormatCode: '0"%"',
    showLegend: false, valAxisMaxVal: 100, valAxisMajorUnit: 25, valAxisLabelFormatCode: '0"%"',
  }));

  card(s, 9.0, 1.4, 3.72, 2.3, "free");
  s.addText("A free, transferable signal", { x: 9.28, y: 1.58, w: 3.2, h: 0.3, fontSize: 13.5, bold: true, color: INK, margin: 0, isTextBox: true });
  s.addText("45% of true-HCP pages state “intended for healthcare professionals only” in their own header; 52% once a page inherits the declaration from its host. It needs no labels, no training and no model — and it carries straight to a new scan.",
    { x: 9.28, y: 1.95, w: 3.2, h: 1.6, fontSize: 11.5, color: GREY, margin: 0, isTextBox: true, valign: "top" });

  card(s, 9.0, 3.9, 3.72, 2.8, "mismatch", AMBERBG);
  s.addText("And it finds mis-filed pages", { x: 9.28, y: 4.08, w: 3.2, h: 0.3, fontSize: 13.5, bold: true, color: RUST, margin: 0, isTextBox: true });
  s.addText("Comparing the declared audience against the content gives 12 pages (5% of 235 HCP-only pages) that are plainly patient-facing — patient information, a US medication guide — on sites that otherwise declare HCP-only. All 12 inherit the declaration rather than stating it.",
    { x: 9.28, y: 4.45, w: 3.2, h: 2.0, fontSize: 11, color: "6B4A20", margin: 0, isTextBox: true, valign: "top" });
  s.addNotes("One trap worth naming: a navigation link reading 'Profesionales Sanitarios' is not a declaration. "
    + "Naive keyword matching confuses the two, and that false positive was found and fixed during the week.");
}

// ======================================================= 11. the off-domain test

{
  const s = pres.addSlide({ masterName: "LIGHT", sectionTitle: "Evidence" });
  s.addText("We pointed it at a site nobody gave us a scan for", Object.assign({}, TITLE));
  s.addText("huggingface.co — a developer platform, deliberately nothing like a pharma site. Crawled with our own crawler, then run through all three tiers unchanged.",
    { x: 0.62, y: 1.2, w: 12.1, h: 0.32, fontSize: 12.5, color: GREY, margin: 0, isTextBox: true });

  card(s, 0.62, 1.62, 12.1, 1.64, "hfstats");
  [["200", "pages crawled\nfrom a standing start", NAVY],
   ["162", "were classifiable\nthe rest: assets, errors", NAVY],
   ["100%", "escalated past tiers 1–2\nnot one page auto-settled", RUST],
   ["$0.02", "total for the LLM tier\n162 pages in 35 seconds", TEAL],
   ["0", "requests failed\nafter the 429 retry fix", TEAL],
  ].forEach(([v, l, c], i) => stat(s, 0.95 + i * 2.4, 1.78, 2.25, v, l, c));

  const compare = [
    ["Tiers 1–2 — the pharma rules", RUST, [
      ["Clinical Evidence", "6"], ["R&D & Science", "8"], ["Form / Request", "1"], ["Patient Support", "1"]],
      "16 of 162 pages given a label that cannot exist on this site. Before the URL-rule fix it was 47."],
    ["Tier 3 — Haiku reading the page", TEAL, [
      ["Listing / Library", "84"], ["Other", "27"], ["Utility / Error", "23"], ["Homepage / Hub", "18"]],
      "Not one pharma label. On audience it answered “Unclear” for 125 of 162 rather than forcing a category."],
  ];
  compare.forEach(([h, col, rows, foot], i) => {
    const x = 0.62 + i * 6.3;
    card(s, x, 3.42, 5.8, 2.26, "cmp-" + i);
    s.addText(h, { x: x + 0.3, y: 3.6, w: 5.2, h: 0.32, fontSize: 13.5, bold: true, color: col, margin: 0, isTextBox: true });
    rows.forEach(([label, n], j) => {
      const y = 4.0 + j * 0.3;
      s.addText(label, { x: x + 0.3, y, w: 4.2, h: 0.28, fontSize: 11.5, color: INK, margin: 0, isTextBox: true });
      s.addText(n, { x: x + 4.5, y, w: 1.0, h: 0.28, fontSize: 11.5, bold: true, color: GREY, align: "right", margin: 0, isTextBox: true });
    });
    s.addText(foot, { x: x + 0.3, y: 5.2, w: 5.22, h: 0.4, fontSize: 11, italic: true, color: GREY, margin: 0, isTextBox: true, valign: "top" });
  });

  card(s, 0.62, 5.84, 12.1, 0.84, "hfverdict", NAVY);
  s.addText([
    { text: "What it proves:  ", options: { bold: true, color: AMBER } },
    { text: "the LLM tier transfers to a new domain and the keyword rules do not. The two tiers agree on only 36% of types here (43% of audiences), against 45% of types on the pharma sites — and where they disagree, it is the cheap tier that is wrong.", options: { color: DTEXT } },
  ], { x: 0.92, y: 6.02, w: 11.5, h: 0.5, fontSize: 12, margin: 0, isTextBox: true, valign: "top" });

  s.addNotes("This is the closest thing week 1 has to the brief’s “site #11” question. It is not a pharma site, so it "
    + "tests transfer harder than a new AstraZeneca site would. Two things to be honest about: agreement is not ground "
    + "truth — nobody labelled these 162 pages — and the taxonomy itself is pharma-specific, so even a perfect "
    + "classifier would be choosing from the wrong list of categories.");
}

// ======================================================= 13. the huggingface output

{
  const s = pres.addSlide({ masterName: "LIGHT", sectionTitle: "Evidence" });
  s.addText("The huggingface.co run, exactly as it came out", Object.assign({}, TITLE));

  codePanel(s, 0.62, 1.3, 12.1, 1.5, null, [
    [["$ ", CODE_FN], ["python scripts/crawl_site.py https://huggingface.co/ -o examples/my_scan.json --max-pages 200", CODE_TX]],
    [["  200 records | robots.txt honoured | 1 req/s, single thread | 36 x HTTP 429 retried", CODE_CM]],
    "",
    [["$ ", CODE_FN], ["python scripts/classify_scan.py examples/my_scan.json --llm escalate --yes -o examples/my_results.jsonl", CODE_TX]],
    [["  tier 3: 162 of 162 pages -> claude-haiku-5-5, estimated $0.03 ($0.171 per 1,000)", CODE_CM]],
    [["  162 pages | tiers ", CODE_TX], ["{'llm': 162}", CODE_ST], [" | status ", CODE_TX], ["{'auto': 26, 'sampled': 121, 'human_review': 15}", CODE_ST]],
    [["  162 pages in 35s (4.6 pages/s), ", CODE_TX], ["0 failed", CODE_FN], [" | cost ", CODE_TX], ["$0.0238", CODE_FN], [" ($0.147 per 1,000)", CODE_TX]],
  ], "hf-console", 9);

  s.addText("Three of the 162 output lines — the whole file is in examples/my_results.jsonl",
    { x: 0.62, y: 3.14, w: 12.1, h: 0.3, fontSize: 12, bold: true, color: INK, margin: 0, isTextBox: true });

  const hdr = (t, al) => ({ text: t, options: { bold: true, color: GREY, fontSize: 10, align: al || "left" } });
  const cell = (t, o) => ({ text: t, options: Object.assign({ fontSize: 10, color: INK }, o || {}) });
  const mono = { fontFace: "Courier New", fontSize: 9, color: GREY };
  s.addTable([
    [hdr("url"), hdr("page_type"), hdr("audience"), hdr("conf", "center"), hdr("status", "center"), hdr("cheap tier said"), hdr("llm_evidence")],
    [cell("/datasets", mono), cell("Listing / Library", { bold: true }), cell("Unclear"), cell("3", { align: "center", bold: true, color: TEAL }),
     cell("auto", { align: "center", color: TEAL, bold: true }), cell("Gateway / Selector", { color: RUST }),
     cell("“Datasets filters with 1,111,090 results; index page linking”", { italic: true, color: GREY, fontSize: 9.5 })],
    [cell("/models", mono), cell("Listing / Library", { bold: true }), cell("Unclear"), cell("2", { align: "center", bold: true, color: AMBER }),
     cell("sampled", { align: "center", color: AMBER, bold: true }), cell("Homepage / Hub", { color: RUST }),
     cell("“Models index with filters and model list; no clear audience signal”", { italic: true, color: GREY, fontSize: 9.5 })],
    [cell("/pricing", mono), cell("Other", { bold: true }), cell("Unclear"), cell("1", { align: "center", bold: true, color: RUST }),
     cell("human_review", { align: "center", color: RUST, bold: true }), cell("Homepage / Hub", { color: RUST }),
     cell("“body is only decorative symbols; no content”", { italic: true, color: GREY, fontSize: 9.5 })],
  ], { x: 0.62, y: 3.5, w: 12.1, colW: [1.1, 1.85, 1.0, 0.55, 1.2, 1.7, 4.7], rowH: 0.42,
       fontFace: "+mn-lt", border: { type: "solid", color: "E4E1D8", pt: 1 }, fill: { color: "FFFFFF" }, valign: "middle" });

  card(s, 0.62, 5.5, 12.1, 1.16, "hfread");
  s.addText("Read the last three columns together", { x: 0.92, y: 5.66, w: 7, h: 0.3, fontSize: 13.5, bold: true, color: INK, margin: 0, isTextBox: true });
  s.addText("The model’s own confidence sorts the work: 26 pages ship unreviewed, 121 ship but get audited, 15 go to a person. The cheap tier got all three of these wrong, and differently each time. And on a site with no patients and no clinicians, answering “Unclear” for the audience is the right answer, not a failure — the taxonomy has no category that fits.",
    { x: 0.92, y: 5.98, w: 11.5, h: 0.6, fontSize: 11.5, color: GREY, margin: 0, isTextBox: true, valign: "top" });

  s.addNotes("These are verbatim rows from examples/my_results.jsonl, not retyped. The evidence string is what makes "
    + "the output auditable — a reviewer can agree or disagree with the model's reason without reopening the page.");
}

// ======================================================= 14. what is not proven

pres.addSection({ title: "What it means" });
{
  const s = pres.addSlide({ masterName: "LIGHT", sectionTitle: "What it means" });
  s.addText("What is not proven yet", Object.assign({}, TITLE));

  const risks = [
    ["No human has checked a single label", "Every accuracy figure is agreement with two LLM labellers reading the same guide the tier-3 model is given. 200 human-checked pages fixes this to ±5.5 points.", "Highest priority"],
    ["There is no auto-publish tier today", "On an unseen site about 97% of pages come out of the cheap tiers as “unsure”. The gate is honest, but it means the cheap tiers are a filter and a cost-saver, not a decision-maker.", "Changes the architecture"],
    ["The taxonomy is pharma-specific", "As the previous slide shows, 23 page types and 8 audiences drawn from ten pharma sites do not describe a developer platform. The LLM tier degrades gracefully; the rules do not. A new client in another industry needs the taxonomy rebuilt, not just retuned.", "Scope question"],
    ["No genuinely new site, and no Sonnet", "All ten sites also shaped the taxonomy and the rules, so even the held-out scores are optimistic. Taxonomy v1.2 is specified but not frozen. Sonnet was never run, so there is no measured case for spending 20x more.", "Not yet tested"],
  ];
  risks.forEach(([h, d, tag], i) => {
    const x = 0.62 + (i % 2) * 6.3;
    const y = 1.42 + Math.floor(i / 2) * 2.56;
    card(s, x, y, 5.8, 2.4, "risk-" + i);
    s.addShape(pres.ShapeType.roundRect, { x: x + 0.3, y: y + 0.22, w: 1.72, h: 0.33, rectRadius: 0.05, fill: { color: AMBERBG }, line: { color: AMBERBG, width: 0 }, objectName: "risktag-" + i });
    s.addText(tag, { x: x + 0.3, y: y + 0.22, w: 1.72, h: 0.33, align: "center", valign: "middle", fontSize: 9.5, bold: true, color: RUST, margin: 0, isTextBox: true });
    s.addText(h, { x: x + 0.3, y: y + 0.62, w: 5.2, h: 0.4, fontSize: 15.5, bold: true, color: INK, fontFace: "Cambria", margin: 0, isTextBox: true, valign: "top" });
    s.addText(d, { x: x + 0.3, y: y + 1.12, w: 5.22, h: 1.12, fontSize: 11.5, color: GREY, margin: 0, isTextBox: true, valign: "top" });
  });
  s.addNotes("Listing these is the point of a week-1 review. None of them invalidates the headline result — the gap "
    + "between 44% and 81% is far larger than any of these caveats could close.");
}

// ======================================================= 13. thank you

pres.addSection({ title: "Close" });
{
  const s = pres.addSlide({ masterName: "COVER", sectionTitle: "Close" });
  s.addShape(pres.ShapeType.rect, { x: 0.9, y: 2.0, w: 1.1, h: 0.06, fill: { color: AMBER }, line: { color: AMBER, width: 0 }, objectName: "thanks-mark" });
  s.addText("Thank you", { x: 0.9, y: 2.55, w: 11.5, h: 1.3, fontSize: 54, bold: true, color: DTITLE, fontFace: "Cambria", isTextBox: true });
  s.addText("Questions welcome — on the numbers, the approach, or what to do next.",
    { x: 0.9, y: 3.95, w: 10.6, h: 0.5, fontSize: 18, color: DTEXT, isTextBox: true });
  s.addText("Findings, numbers and how to run it: README.md   ·   Prototype: scripts/classify_scan.py   ·   Live demo: streamlit_app.py",
    { x: 0.9, y: 5.5, w: 11.5, h: 0.4, fontSize: 13, color: "7E8CA8", isTextBox: true });
  s.addNotes("Everything in this deck is reproducible from the repository. README.md carries the full "
    + "findings, the limitations and the step-by-step run guide; streamlit_app.py is the live demo.");
}

(async () => {
  await pres.writeFile({ fileName: OUT });
  await applyTheme(OUT, THEME);
  console.log("wrote " + OUT);
})();
