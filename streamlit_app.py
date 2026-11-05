"""Web Page Categorisation - live demo.

Give it a URL. It crawls the site politely, then asks Claude Haiku 5.5 what each page is and
who it is for, and shows the answer with the evidence behind it.

Only tier 3 (the LLM) runs here. Tiers 1-2 need PyTorch and a 471 MB sentence encoder, which is
more than a small cloud dyno wants to carry. The README section "The LLM tier, measured" is why that
costs almost nothing: on a site the model has never seen, the cheap tiers get 44% of page types right
and Haiku gets 81%.

Run locally:   streamlit run streamlit_app.py
Deploy:        Streamlit Cloud, main file streamlit_app.py, with ANTHROPIC_API_KEY in Secrets.
"""
import html
import math
import os
import re
import sys
import time

import pandas as pd
import streamlit as st

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "page_categorisation", "src"))

from pagecat import llm_tier                      # noqa: E402
from pagecat.fetch import crawl                   # noqa: E402
from pagecat.scan import featurise                # noqa: E402
from pagecat.taxonomy import VERSION              # noqa: E402

# --------------------------------------------------------------------------- page config

st.set_page_config(page_title="Web Page Categorisation", page_icon="◧",
                   layout="wide", initial_sidebar_state="expanded")

NAVY, AMBER, TEAL, RUST, INK, GREY = "#11203A", "#E08E1D", "#0F766E", "#A33D1C", "#1B2435", "#5B6472"


def _s(v, fallback=""):
    """Display string for raw HTML: NaN/None become `fallback`, and everything is escaped.

    Both halves matter. pandas turns a failed page's None into NaN, and NaN is truthy, so
    `value or fallback` would print "nan"; and page titles and URLs come from a crawled site,
    so they are untrusted and must never reach innerHTML unescaped.
    """
    if v is None or (isinstance(v, float) and math.isnan(v)):
        v = fallback
    return html.escape(str(v))

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,400;9..144,600&family=Inter:wght@400;500;600&display=swap');

html, body, [class*="css"], .stMarkdown, .stText { font-family: 'Inter', system-ui, sans-serif; }
.stApp { background: #F7F6F2; }
#MainMenu, footer, header { visibility: hidden; }
.block-container { padding-top: 2.2rem; padding-bottom: 3rem; max-width: 1280px; }

h1, h2, h3 { font-family: 'Fraunces', Georgia, serif !important; color: #1B2435; letter-spacing: -0.01em; }

/* hero */
.hero { background: #11203A; border-radius: 14px; padding: 2.1rem 2.3rem 1.8rem;
        margin-bottom: 1.6rem; }
.hero .rule { width: 56px; height: 4px; background: #E08E1D; border-radius: 2px; margin-bottom: 1.1rem; }
.hero h1 { color: #F1F3F7 !important; font-size: 2.1rem; margin: 0 0 .5rem; }
.hero p { color: #C3CDE0; font-size: 1.02rem; margin: 0; max-width: 62rem; line-height: 1.55; }
.hero .meta { color: #7E8CA8; font-size: .82rem; margin-top: 1rem; }

/* cards */
.card { background: #fff; border: 1px solid #E4E1D8; border-radius: 12px;
        padding: 1.1rem 1.3rem; box-shadow: 0 2px 8px rgba(138,133,120,.09); height: 100%; }
.card .lbl { color: #5B6472; font-size: .76rem; text-transform: uppercase;
             letter-spacing: .07em; font-weight: 600; }
.card .val { font-family: 'Fraunces', Georgia, serif; font-size: 2.05rem;
             line-height: 1.15; margin-top: .3rem; color: #11203A; }
.card .sub { color: #5B6472; font-size: .82rem; margin-top: .28rem; }

/* result rows */
.page { background: #fff; border: 1px solid #E4E1D8; border-radius: 10px;
        padding: .85rem 1.05rem; margin-bottom: .55rem; }
.page .u { font-family: ui-monospace, 'SF Mono', Menlo, monospace; font-size: .78rem;
           color: #5B6472; word-break: break-all; }
.page .t { font-size: 1.02rem; font-weight: 600; color: #1B2435; margin: .25rem 0 .1rem; }
.page .e { font-size: .86rem; color: #5B6472; font-style: italic; margin-top: .35rem; }

.badge { display: inline-block; padding: .17rem .6rem; border-radius: 999px;
         font-size: .72rem; font-weight: 600; letter-spacing: .02em; }
.b-auto   { background: #D7EFE9; color: #0F766E; }
.b-samp   { background: #FCEFDC; color: #96601A; }
.b-human  { background: #F6DFD8; color: #A33D1C; }
.b-aud    { background: #ECEAE2; color: #1B2435; }

.stButton > button { background: #11203A; color: #fff; border: 0; border-radius: 8px;
                     padding: .55rem 1.3rem; font-weight: 600; }
.stButton > button:hover { background: #1B3055; color: #fff; }
.stDownloadButton > button { border-radius: 8px; border: 1px solid #C9C4B6;
                             background: #fff; color: #1B2435; font-weight: 500; }
/* The sidebar is the control panel and should stay open.
   Two rules learned the hard way:
   1. Never hide the control that REOPENS a collapsed sidebar. Streamlit decides the initial
      state itself and it varies by version and viewport; hiding the reopen arrow turns a
      collapsed sidebar into one the user cannot recover. Only the collapse arrow is hidden.
   2. Do not try to force a collapsed sidebar open with CSS. Streamlit translates it off
      screen with an emotion class that survives even an inline !important override, so the
      rule silently loses and the panel is simply gone. initial_sidebar_state does the job. */
section[data-testid="stSidebar"], div[data-testid="stSidebar"] {
  background: #fff; border-right: 1px solid #E4E1D8;
}
div[data-testid="stSidebarCollapseButton"],
button[data-testid="stSidebarCollapseButton"] { display: none !important; }
/* Section label inside the sidebar, in place of an expander. */
.sidelabel { font-size: .72rem; font-weight: 600; letter-spacing: .07em;
             text-transform: uppercase; color: #8A8578; margin: .2rem 0 -.2rem; }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="hero">
  <div class="rule"></div>
  <h1>Web Page Categorisation</h1>
  <p>Give it any website. It crawls the pages, reads each one, and says <b>what kind of page it is</b>
     and <b>who it is written for</b> &mdash; with the evidence it used and how sure it is.</p>
  <div class="meta">Taxonomy %s &nbsp;·&nbsp; benchmarked with Claude Haiku 5.5 on 800 labelled pages:
     80.9%% on page type, 90.4%% on audience</div>
</div>
""" % VERSION, unsafe_allow_html=True)

# --------------------------------------------------------------------------- key + settings


ENV_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "page_categorisation", ".env")


def _key_from_env_file():
    """The same local .env the CLI reads (scripts/classify_scan.py). Never exists on the cloud."""
    try:
        m = re.search(r"sk-ant-[A-Za-z0-9_\-]+", open(ENV_FILE, encoding="utf-8").read())
        return m.group(0) if m else None
    except Exception:
        return None


def api_key():
    """Secrets (Streamlit Cloud) -> environment -> the project's local .env -> typed in the sidebar.

    The value is only ever passed to the Anthropic client; nothing here prints or logs it.
    """
    try:
        if "ANTHROPIC_API_KEY" in st.secrets:
            return st.secrets["ANTHROPIC_API_KEY"], "app secrets"
    except Exception:
        pass
    if os.environ.get("ANTHROPIC_API_KEY"):
        return os.environ["ANTHROPIC_API_KEY"], "environment"
    if st.session_state.get("typed_key"):
        return st.session_state["typed_key"], "this session"
    from_file = _key_from_env_file()
    if from_file:
        return from_file, "page_categorisation/.env"
    return None, None


with st.sidebar:
    st.markdown("### Settings")
    key, key_src = api_key()
    if key:
        st.success("API key loaded from %s" % key_src)
    else:
        st.text_input("Anthropic API key", type="password", key="typed_key",
                      placeholder="sk-ant-...",
                      help="Not stored. On Streamlit Cloud, set ANTHROPIC_API_KEY in Secrets instead.")
        key, key_src = api_key()

    st.markdown("---")
    # The three choices that change what a run costs stay in front; the rest is tuning.
    max_pages = st.slider("Pages to crawl", 5, 60, 15,
                          help="Each page is one API call. The crawl waits a second between "
                               "requests, so 15 pages takes about half a minute.")

    MODELS = {"claude-haiku-5-5": ("Haiku 5.5", 0.171, "measured: 80.9% type, 90.4% audience"),
              "claude-sonnet-5-5": ("Sonnet 5.5", 5.51, "20x the price, never benchmarked")}
    model = st.selectbox("Model", list(MODELS), index=0,
                         format_func=lambda m: MODELS[m][0],
                         help="Haiku is the one every number in this app was measured with.")
    _label, _rate, _note = MODELS[model]
    st.caption("$%.2f per 1,000 pages · %s" % (_rate, _note))

    st.markdown("---")
    st.markdown('<div class="sidelabel">Crawl</div>', unsafe_allow_html=True)
    include_pdf = st.checkbox("Include PDFs", value=True,
                              help="PDFs score as well as HTML (80.7% vs 80.9% on page type).")
    same_host = st.checkbox("Stay on this exact host", value=False,
                            help="Off: also follow links to subdomains of the same registered "
                                 "domain, e.g. from example.com to news.example.com.")
    delay = st.select_slider("Delay between requests", [1.0, 2.0, 3.0], value=1.0,
                             format_func=lambda v: "%.0f s" % v,
                             help="How long to wait between page fetches. Raise it for a "
                                  "site that rate-limits; there is no reason to go faster.")
    concurrency = st.slider("Parallel requests", 1, 12, 8,
                            help="How many pages are classified at once. 8 is what the "
                                 "4.3 pages/s figure was measured at.")

    st.markdown("---")
    st.caption("The crawler always honours robots.txt, fetches one page at a time and identifies "
               "itself. Only crawl sites you are allowed to crawl.")

SAMPLE = [
    ("https://www.astrazeneca.com/", "Homepage / Hub", "General Public", 3,
     "corporate masthead linking to news, investors, careers and therapy areas"),
    ("https://www.astrazeneca.com/privacy-notice.html", "Privacy & Legal", "General Public", 3,
     "headed 'Privacy Notice'; sets out data collection and rights"),
    ("https://www.astrazeneca.com/our-science/clinical-trials.html", "Clinical Evidence",
     "Healthcare Professional", 2, "trial design and endpoint tables; clinical register links"),
    ("https://www.astrazeneca.com/careers/apply.html", "Careers", "Job Seeker", 3,
     "'search and apply for roles'; vacancy list with locations"),
    ("https://www.astrazeneca.com/investor-relations/results.pdf", "Investor Relations", "Investor", 3,
     "quarterly results PDF with revenue tables and EPS guidance"),
    ("https://www.astrazeneca.com/contact-us.html", "Contact / Locations", "General Public", 2,
     "office addresses and a general enquiry form"),
    ("https://www.astrazeneca.com/hcp/prescribing.html", "Prescribing Information",
     "Healthcare Professional", 3, "header states 'intended for healthcare professionals only'"),
    ("https://www.astrazeneca.com/patient-support/access.html", "Patient Support",
     "Patient / Caregiver", 2, "describes an affordability programme for people taking the medicine"),
    ("https://www.astrazeneca.com/legacy/redirect", "Utility / Error", "Unclear", 1,
     "near-empty shell; body is a redirect notice"),
    ("https://www.astrazeneca.com/our-science/oncology.html", "Disease & Therapy Area",
     "Healthcare Professional", 2, "disease background and mechanism of action for a tumour type"),
    ("https://www.astrazeneca.com/our-science/respiratory.html", "Disease & Therapy Area",
     "General Public", 2, "plain-language explanation of asthma and COPD"),
    ("https://www.astrazeneca.com/media-centre/press-releases/q3.html", "News & Media",
     "Media", 3, "dated press release with a media contact block"),
    ("https://www.astrazeneca.com/media-centre/articles/trial-readout.html", "News & Media",
     "General Public", 2, "news article summarising a trial result for a lay reader"),
    ("https://www.astrazeneca.com/hcp/dosing.pdf", "Prescribing Information",
     "Healthcare Professional", 3, "posology and method of administration; HCP-only banner"),
    ("https://www.astrazeneca.com/our-science/publications.html", "Clinical Evidence",
     "Healthcare Professional", 2, "list of peer-reviewed publications with DOIs"),
    ("https://www.astrazeneca.com/sustainability/report-2026.pdf", "Sustainability",
     "Investor", 3, "emissions targets and progress tables"),
    ("https://www.astrazeneca.com/search?q=", "Utility / Error", "Unclear", 1,
     "empty search results shell; no content"),
]


def load_sample():
    st.session_state.results = [
        dict(url=u, page_type=t, audience=a, confidence=c, evidence=e,
             is_pdf=u.endswith(".pdf"), lang="en", title="", failed=False)
        for u, t, a, c, e in SAMPLE]
    n = len(SAMPLE)
    st.session_state.update(elapsed=n / 4.3, cost=n * 0.171 / 1000,
                            crawled_url="www.astrazeneca.com (sample)",
                            records=[{}] * n, is_sample=True)


# --------------------------------------------------------------------------- input

c1, c2 = st.columns([4, 1.25])
with c1:
    url = st.text_input("Website", placeholder="https://example.com",
                        label_visibility="collapsed")
with c2:
    go = st.button("Crawl site", use_container_width=True)

for k in ("records", "results", "elapsed", "cost", "crawled_url"):
    st.session_state.setdefault(k, None)

# --------------------------------------------------------------------------- crawl

if go:
    if not url.strip():
        st.warning("Enter a URL first.")
    else:
        # is_sample must go too, or a real paid run inherits the "this is a saved sample" banner
        st.session_state.update(records=None, results=None, is_sample=False)
        target = url.strip()
        if not target.startswith(("http://", "https://")):
            target = "https://" + target
        bar, note = st.progress(0.0, text="Reading robots.txt…"), st.empty()
        recs, blocked, errors = [], 0, 0
        t0 = time.time()
        try:
            for rec in crawl(target, max_pages=max_pages, delay=delay, same_host=same_host,
                             include_pdf=include_pdf):
                recs.append(rec)
                bar.progress(min(len(recs) / max_pages, 1.0),
                             text="Fetched %d of %d — %s" % (len(recs), max_pages, rec["File URL"][:80]))
            bar.empty(); note.empty()
        except Exception as e:
            bar.empty(); note.empty()
            st.error("Could not crawl that site: %s: %s" % (type(e).__name__, e))
        if recs:
            st.session_state.records = recs
            st.session_state.crawled_url = target
            st.session_state.crawl_secs = time.time() - t0

# --------------------------------------------------------------------------- estimate + classify

def _rate_note(est, n, model):
    """Per-1,000 rate, flagged when a tiny run makes the one-off cache write dominate."""
    per_k = est / max(n, 1) * 1000
    tail = " (small run: the one-off prompt cache write dominates)" if n < 20 else ""
    return "%s · $%.3f per 1,000 pages%s" % (model.replace("claude-", ""), per_k, tail)


records = st.session_state.records
if records and st.session_state.results is None:
    feats = featurise(records)
    if not len(feats):
        st.error("Crawled %d pages but none were classifiable — they were images, errors or empty shells."
                 % len(records))
    else:
        rows = list(feats.itertuples())
        est = llm_tier.estimate_usd(rows, model)
        a, b, c = st.columns(3)
        for col, lbl, val, sub in [
            (a, "Crawled", "%d" % len(records), "%d classifiable, %d skipped"
             % (len(feats), len(records) - len(feats))),
            (b, "Estimated cost", "$%.4f" % est, _rate_note(est, len(rows), model)),
            (c, "Crawl took", "%.0fs" % st.session_state.get("crawl_secs", 0), "one request at a time"),
        ]:
            col.markdown('<div class="card"><div class="lbl">%s</div><div class="val">%s</div>'
                         '<div class="sub">%s</div></div>' % (lbl, val, sub), unsafe_allow_html=True)

        st.write("")
        if not key:
            st.info("Add an Anthropic API key in the sidebar to classify these pages.", icon="🔑")
        elif st.button("Classify %d pages — about $%.4f" % (len(rows), est), type="primary"):
            import anthropic
            client = anthropic.Anthropic(api_key=key, max_retries=4)
            bar = st.progress(0.0, text="Classifying page 1 of %d…" % len(rows))
            t0 = time.time()
            # llm_tier.run calls this from this thread, never from a pool thread - st.progress
            # raises NoSessionContext if it is touched from one.
            answers = llm_tier.run(
                client, rows, model=model, concurrency=concurrency,
                on_progress=lambda d, t: bar.progress(d / t, text="Classified %d of %d" % (d, t)))
            bar.empty()

            st.session_state.results = [
                dict(url=r.url, page_type=a.get("type"), audience=a.get("audience"),
                     confidence=a.get("confidence", 0), evidence=a.get("evidence") or a.get("error", ""),
                     is_pdf=bool(r.is_pdf), lang=r.lang, title=r.title, failed=a.get("type") is None)
                for r, a in zip(rows, answers)]
            st.session_state.elapsed = time.time() - t0
            st.session_state.cost = llm_tier.usd([a["usage"] for a in answers if "usage" in a], model)
            st.rerun()

# --------------------------------------------------------------------------- results

results = st.session_state.results
if results:
    df = pd.DataFrame(results)
    ok = df[~df.failed]
    STATUS = {3: ("auto", "b-auto", "ships unreviewed"),
              2: ("sampled", "b-samp", "ships, spot-checked"),
              1: ("human review", "b-human", "needs a person"),
              0: ("failed", "b-human", "request failed")}

    st.markdown("### Results")
    st.caption("%d pages from %s" % (len(df), st.session_state.crawled_url))
    if st.session_state.get("is_sample"):
        st.info("This is a saved sample, not a live run. Enter a URL above to classify a real site.",
                icon="ℹ")

    n3, n2, n1 = [(ok.confidence == c).sum() for c in (3, 2, 1)]
    cols = st.columns(4)
    for col, lbl, val, sub in [
        (cols[0], "Pages classified", "%d" % len(ok),
         "%d failed" % int(df.failed.sum()) if df.failed.any() else "none failed"),
        (cols[1], "Actual cost", "$%.4f" % (st.session_state.cost or 0),
         "$%.3f per 1,000 pages" % ((st.session_state.cost or 0) / max(len(df), 1) * 1000)),
        (cols[2], "Took", "%.0fs" % (st.session_state.elapsed or 0),
         "%.1f pages/s" % (len(df) / max(st.session_state.elapsed or 1, .001))),
        (cols[3], "Ship without review", "%d" % n3,
         "%d spot-check · %d to a person" % (n2, n1)),
    ]:
        col.markdown('<div class="card"><div class="lbl">%s</div><div class="val">%s</div>'
                     '<div class="sub">%s</div></div>' % (lbl, val, sub), unsafe_allow_html=True)

    st.write("")
    left, right = st.columns(2)
    with left:
        st.markdown("##### Page types found")
        st.bar_chart(ok.page_type.value_counts(), horizontal=True, color=NAVY, height=max(180, 32 * ok.page_type.nunique()))
    with right:
        st.markdown("##### Who they are written for")
        st.bar_chart(ok.audience.value_counts(), horizontal=True, color=TEAL, height=max(180, 32 * ok.audience.nunique()))

    st.markdown("##### Every page")
    f1, f2 = st.columns([2, 3])
    pick = f1.multiselect("Filter by confidence", ["auto", "sampled", "human review", "failed"],
                          default=[], placeholder="All pages")
    q = f2.text_input("Search URL or type", placeholder="e.g. privacy, /about, Patient",
                      label_visibility="visible")

    view = df
    if pick:
        want = {k for k, (nm, _, _) in STATUS.items() if nm in pick}
        view = view[view.confidence.isin(want)]
    if q:
        m = q.lower()
        view = view[view.apply(
            lambda r: any(m in str(v).lower() for v in (r.url, r.page_type, r.audience)
                          if v is not None and not (isinstance(v, float) and math.isnan(v))), axis=1)]

    st.caption("%d of %d pages" % (len(view), len(df)))
    for r in view.itertuples():
        name, cls, meaning = STATUS.get(r.confidence, STATUS[0])
        st.markdown(
            '<div class="page">'
            '<div class="u">%s%s</div>'
            '<div class="t">%s</div>'
            '<span class="badge %s">%s &nbsp;·&nbsp; %s</span> '
            '<span class="badge b-aud">%s</span>'
            '<div class="e">%s</div>'
            '</div>' % (
                _s(r.url), "  (PDF)" if r.is_pdf else "",
                _s(r.page_type, "— not classified —"), cls, name, meaning,
                _s(r.audience, "—"), _s(r.evidence)),
            unsafe_allow_html=True)

    st.write("")
    d1, d2, _ = st.columns([1, 1, 3])
    d1.download_button("Download CSV", df.to_csv(index=False).encode("utf-8"),
                       "page_categories.csv", "text/csv", use_container_width=True)
    d2.download_button("Download JSONL", df.to_json(orient="records", lines=True).encode("utf-8"),
                       "page_categories.jsonl", "application/x-ndjson", use_container_width=True)

    with st.expander("How to read these numbers"):
        st.markdown("""
The model reports its own confidence on every page, and that confidence was measured against an
800-page benchmark, so it means something concrete:

| It says | Share of pages | Page type correct | Audience correct |
|---|---|---|---|
| **auto** (certain) | 39% | 92.6% | 97.4% |
| **sampled** (probable) | 56% | 76.0% | 87.6% |
| **human review** (guess) | 6% | 48.9% | 68.9% |

Overall: **80.9%** of page types and **90.4%** of audiences, at about **$0.17 per 1,000 pages**.

Two honest caveats. The benchmark was labelled by two LLM annotators reading the same guide this
model is given, so these are agreement figures, not human-verified truth. And the taxonomy was
derived from ten pharmaceutical websites — on a site from another industry the model will pick the
closest category it has rather than the right one, because the right one may not exist in the list.
""")
elif not records:
    st.markdown("")
    s1, s2 = st.columns([1.4, 4])
    if s1.button("See a sample", use_container_width=True):
        load_sample()
        st.rerun()
    s2.markdown('<div style="padding-top:.45rem;color:#5B6472;font-size:.9rem">'
                "No API key needed &mdash; a saved run on a site from the benchmark, "
                "so you can see the output before spending anything.</div>",
                unsafe_allow_html=True)
    st.write("")
    e1, e2, e3 = st.columns(3)
    for col, h, d in [
        (e1, "1 · Crawl", "Enter a URL. The crawler follows links from that page, obeying robots.txt "
                          "and pausing between requests."),
        (e2, "2 · Read", "Each page — HTML or PDF — is stripped of navigation and cookie banners, then "
                         "sent to Claude with the annotation guide as its instructions."),
        (e3, "3 · Judge", "Every answer comes back with a short evidence quote and a confidence, so you "
                          "can see why it decided what it did."),
    ]:
        col.markdown('<div class="card"><div class="lbl">%s</div><div class="sub" '
                     'style="margin-top:.55rem;font-size:.9rem;line-height:1.5">%s</div></div>'
                     % (h, d), unsafe_allow_html=True)
