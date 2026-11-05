"""Headless checks for streamlit_app.py - no browser, no network, no API key, no spend.

Exercises the two states that are easy to ship broken: the empty landing page, and the full
results view (metric cards, both charts, the filters, the per-page rows, the downloads).
Run from the repo root:  python tests_app.py
"""
import sys

from streamlit.testing.v1 import AppTest

PASS, FAIL = [], []


def check(name, fn):
    try:
        fn()
        PASS.append(name)
    except Exception as e:
        FAIL.append((name, "%s: %s" % (type(e).__name__, e)))


def fake_results():
    """Shaped exactly like what the classify step writes into session_state."""
    base = dict(is_pdf=False, lang="en", failed=False)
    return [
        dict(url="https://example.com/", page_type="Homepage / Hub", audience="General Public",
             confidence=3, evidence="masthead and top-level nav", title="Example", **base),
        dict(url="https://example.com/privacy", page_type="Privacy & Legal", audience="General Public",
             confidence=2, evidence="headed 'Privacy Statement'", title="Privacy", **base),
        dict(url="https://example.com/datasheet.pdf", page_type="Product Information",
             audience="Healthcare Professional", confidence=1, evidence="dosage table",
             title="Datasheet", **dict(base, is_pdf=True)),
        dict(url="https://example.com/broken", page_type=None, audience=None, confidence=0,
             evidence="APIError: overloaded", title="", **dict(base, failed=True)),
    ]


def run(**state):
    at = AppTest.from_file("streamlit_app.py", default_timeout=60)
    for k, v in state.items():
        at.session_state[k] = v
    at.run()
    if at.exception:
        raise AssertionError("app raised: %s" % "; ".join(str(e.value) for e in at.exception))
    return at


def t_landing():
    at = run()
    body = " ".join(m.value for m in at.markdown)
    assert "Web Page Categorisation" in body
    assert "1 &middot; Crawl" in body or "1 · Crawl" in body, "the three explainer cards should show"
    assert at.button, "the crawl button should exist"


def t_results_render():
    at = run(results=fake_results(), elapsed=3.2, cost=0.00211,
             crawled_url="https://example.com", records=[{}])
    body = " ".join(m.value for m in at.markdown)
    for want in ("Results", "Pages classified", "Actual cost", "Homepage / Hub",
                 "Privacy &amp; Legal", "ships unreviewed", "needs a person"):
        assert want in body, "missing from the results view: %r" % want


def t_failed_row_is_shown_not_hidden():
    at = run(results=fake_results(), elapsed=1.0, cost=0.001,
             crawled_url="https://example.com", records=[{}])
    body = " ".join(m.value for m in at.markdown)
    assert "not classified" in body, "a failed page must still appear, not vanish"
    assert "nan" not in body.lower().split("human")[0], "NaN must never reach the page"
    assert "1 failed" in body, "the failure count belongs on the metric card"


def t_counts_exclude_failures():
    at = run(results=fake_results(), elapsed=1.0, cost=0.001,
             crawled_url="https://example.com", records=[{}])
    body = " ".join(m.value for m in at.markdown)
    assert ">3<" in body.replace(" ", ""), "3 of 4 pages classified; the failure should not count"


def t_sample_banner_only_for_the_sample():
    # A real, paid run must never be labelled a saved sample. The flag is sticky in
    # session_state, so a crawl after viewing the sample has to clear it.
    def banners(at):
        return " ".join(el.value for el in at.info)

    real = run(results=fake_results(), elapsed=1.0, cost=0.001,
               crawled_url="https://example.com", records=[{}], is_sample=False)
    assert "saved sample" not in banners(real), "a real, paid run was labelled a sample"

    sample = run(results=fake_results(), elapsed=1.0, cost=0.001,
                 crawled_url="x (sample)", records=[{}], is_sample=True)
    assert "saved sample" in banners(sample), "the sample must say so"


def t_crawling_after_the_sample_clears_the_sample_flag():
    """The real interaction that shipped the bug: view the sample, then crawl.

    Driven through the actual buttons rather than by poking session_state, because the bug
    was that the crawl handler forgot one key. The URL is a .invalid domain, so the crawl
    resolves nothing and returns immediately - no network, no spend.
    """
    at = AppTest.from_file("streamlit_app.py", default_timeout=90)
    at.run()
    sample_btn = [b for b in at.button if "sample" in b.label.lower()]
    assert sample_btn, "no sample button on the landing page"
    sample_btn[0].click().run()
    assert at.session_state["is_sample"] is True, "the sample button should set is_sample"
    assert any("saved sample" in el.value for el in at.info), "the sample must be labelled"

    at.text_input[0].set_value("https://not-a-real-domain-for-tests.invalid").run()
    crawl_btn = [b for b in at.button if "crawl" in b.label.lower()]
    assert crawl_btn, "no crawl button"
    crawl_btn[0].click().run()
    assert at.session_state.get("is_sample") is False, \
        "crawling must clear is_sample, or a real paid run is labelled a saved sample"


def t_downloads_present():
    at = run(results=fake_results(), elapsed=1.0, cost=0.001,
             crawled_url="https://example.com", records=[{}])
    labels = [d.label for d in at.download_button]
    assert "Download CSV" in labels and "Download JSONL" in labels, labels


def t_charts_render():
    at = run(results=fake_results(), elapsed=1.0, cost=0.001,
             crawled_url="https://example.com", records=[{}])
    # AppTest has no accessor for st.bar_chart - it surfaces as UnknownElement, one per chart
    n = sum(type(el).__name__ == "UnknownElement" for el in at._tree)
    assert n >= 2, "expected both bar charts to render, got %d" % n


if __name__ == "__main__":
    for name, fn in [
        ("landing page renders with the three explainer cards", t_landing),
        ("results view renders every section", t_results_render),
        ("a failed page is shown, not silently dropped", t_failed_row_is_shown_not_hidden),
        ("metric counts exclude failed pages", t_counts_exclude_failures),
        ("the sample banner shows only for the sample", t_sample_banner_only_for_the_sample),
        ("crawling after the sample clears the sample flag",
         t_crawling_after_the_sample_clears_the_sample_flag),
        ("CSV and JSONL download buttons exist", t_downloads_present),
        ("both bar charts render", t_charts_render),
    ]:
        check(name, fn)
    for n in PASS:
        print("PASS  %s" % n)
    for n, e in FAIL:
        print("FAIL  %s\n      %s" % (n, e))
    print("\n%d passed, %d failed" % (len(PASS), len(FAIL)))
    sys.exit(1 if FAIL else 0)
