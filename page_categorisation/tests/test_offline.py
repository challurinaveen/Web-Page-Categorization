#!/usr/bin/env python
"""Offline checks - no API key, no model download, no network. Run from anywhere:

    python tests/test_offline.py

Covers the parts that are easy to break and expensive to notice: the tier-3 cost model, the tier-3
wiring (against a stub client, including a failed request), the URL-rule boundary guards from
the README, "URL-rule boundary guards", the scan reader's record filtering, and taxonomy/guide agreement.
"""
import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_HERE, "..", "src"))
os.chdir(os.path.join(_HERE, ".."))

from pagecat import cascade as C          # noqa: E402
from pagecat import llm_tier as L         # noqa: E402
from pagecat import preprocess, rules, scan  # noqa: E402
from pagecat.taxonomy import AUD, TYPES   # noqa: E402

PASS, FAIL = [], []


def check(name):
    def deco(fn):
        try:
            fn()
            PASS.append(name)
        except Exception as e:
            FAIL.append((name, "%s: %s" % (type(e).__name__, e)))
    return deco


def record(url, text, mime="text/html", status="200", pages=0):
    """One record in the 14-field DCR scan format."""
    return {"Report ID": "1", "Report URL": "https://www.astrazeneca.com/", "File ref": url,
            "File storagekey": "k", "File URL": url, "File Mimetype": mime, "File Status": status,
            "PDF Pages": pages, "File URL Shortestpath": "https://www.astrazeneca.com/\n" + url,
            "File text": text, "File text lines": text.split("\n"), "File text sep": "\n",
            "File text language": "", "File text translated": ""}


BODY = "\n".join(["Prescribing information for healthcare professionals."] * 4 +
                 ["This medicine is indicated for the treatment of adult patients."] * 4)
ROWS = scan.featurise([record("https://www.astrazeneca.com/p%d" % i, BODY) for i in range(5)])


# --------------------------------------------------------------------- cost model

@check("estimate_usd: zero pages costs nothing, cost grows with page count")
def _():
    assert L.estimate_usd([]) == 0.0
    one = L.estimate_usd(list(ROWS.iloc[:1].itertuples()))
    five = L.estimate_usd(list(ROWS.itertuples()))
    assert 0 < one < five, (one, five)


@check("estimate_usd: Haiku is the cheapest option and Sonnet is 20x its token price")
def _():
    rows = list(ROWS.itertuples())
    h, s = L.estimate_usd(rows, "claude-haiku-5-5"), L.estimate_usd(rows, "claude-sonnet-5-5")
    assert L.PRICE["claude-sonnet-5-5"][0] / L.PRICE["claude-haiku-5-5"][0] == 20
    assert L.PRICE["claude-sonnet-5-5"][1] / L.PRICE["claude-haiku-5-5"][1] == 20
    assert abs(s / h - 20) < 1e-6, "cost should scale exactly with price, got %.4fx" % (s / h)
    assert h == min(L.estimate_usd(rows, m) for m in L.PRICE)


@check("estimate_usd: per-1,000 estimate lands near the $0.171 measured in REPORT 4b")
def _():
    per_1k = L.estimate_usd(list(ROWS.itertuples())) / len(ROWS) * 1000
    assert 0.10 < per_1k < 0.40, "%.4f per 1,000 is outside the measured range" % per_1k


@check("usd: cached input bills at 0.1x, cache writes at 1.25x, output at the output price")
def _():
    pi, po = L.PRICE["claude-haiku-5-5"]
    M = 1_000_000

    def one(**kw):
        return L.usd([dict(dict(inp=0, out=0, cread=0, cwrite=0), **kw)], "claude-haiku-5-5")
    assert abs(one(inp=M) - pi) < 1e-9
    assert abs(one(cread=M) - pi * 0.1) < 1e-9
    assert abs(one(cwrite=M) - pi * 1.25) < 1e-9
    assert abs(one(out=M) - po) < 1e-9
    assert L.usd([]) == 0.0


# ------------------------------------------------------------- tier-3 wiring (stub client)

class StubUsage:
    input_tokens, output_tokens = 515, 180
    cache_read_input_tokens, cache_creation_input_tokens = 2923, 0


class StubBlock:
    type = "text"

    def __init__(self, text):
        self.text = text


class StubResponse:
    def __init__(self, payload, stop_reason="end_turn"):
        self.content = [StubBlock(json.dumps(payload))]
        self.usage = StubUsage()
        self.stop_reason = stop_reason


class StubMessages:
    def __init__(self, parent):
        self.parent = parent

    def create(self, **kw):
        p = self.parent
        p.calls += 1
        p.seen.append(kw)
        if p.fail_on == p.calls:
            raise RuntimeError("stub failure")
        return StubResponse(p.payload, p.stop_reason)


class StubClient:
    """Answers every request from a fixed payload. `fail_on` makes that call number raise instead."""

    def __init__(self, payload, fail_on=None, stop_reason="end_turn"):
        self.payload, self.fail_on, self.stop_reason = payload, fail_on, stop_reason
        self.calls, self.seen = 0, []
        self.messages = StubMessages(self)


ANSWER = dict(type="Prescribing Information", audience="Healthcare Professional",
              confidence=3, evidence="header states for HCPs only")


@check("classify: sends a cached system prompt and a JSON schema bound to the taxonomy")
def _():
    c = StubClient(ANSWER)
    out = L.classify(c, next(ROWS.itertuples()))
    kw = c.seen[0]
    assert kw["system"][0]["cache_control"] == {"type": "ephemeral"}, "guide must be cacheable"
    assert kw["output_config"]["format"]["type"] == "json_schema"
    assert kw["max_tokens"] >= 1500, "300 output tokens truncated 19% of answers (REPORT 4b)"
    assert L.SCHEMA["properties"]["type"]["enum"] == TYPES
    assert L.SCHEMA["properties"]["audience"]["enum"] == AUD
    assert out["type"] == ANSWER["type"] and out["taxonomy"]


@check("classify: a refusal is routed to a human, never guessed")
def _():
    c = StubClient(ANSWER, stop_reason="refusal")
    out = L.classify(c, next(ROWS.itertuples()))
    assert (out["type"], out["audience"], out["confidence"]) == ("Other", "Unclear", 1)


@check("classify: a truncated answer raises rather than returning a half-parsed label")
def _():
    c = StubClient(ANSWER, stop_reason="max_tokens")
    try:
        L.classify(c, next(ROWS.itertuples()))
    except RuntimeError:
        return
    raise AssertionError("stop_reason=max_tokens should raise")


@check("run: returns one answer per row, in input order, with usage attached")
def _():
    rows = list(ROWS.itertuples())
    c = StubClient(ANSWER)
    out = L.run(c, rows, concurrency=4)
    assert len(out) == len(rows) and c.calls == len(rows)
    assert all(o["type"] == ANSWER["type"] for o in out)
    assert all(set(o["usage"]) == {"inp", "out", "cread", "cwrite"} for o in out)
    assert L.run(c, []) == []


@check("run: on_progress fires once per page, from the calling thread only")
def _():
    # A Streamlit progress bar raises NoSessionContext if touched from a pool thread, so this
    # callback must never be handed to a worker. The app depends on it.
    import threading
    rows = list(ROWS.itertuples())
    main, seen, threads = threading.get_ident(), [], set()

    def note(done, total):
        seen.append((done, total))
        threads.add(threading.get_ident())

    out = L.run(StubClient(ANSWER), rows, concurrency=4, on_progress=note)
    assert len(out) == len(rows)
    assert threads == {main}, "on_progress was called from %d other thread(s)" % (len(threads) - 1)
    assert [d for d, _ in seen] == list(range(1, len(rows) + 1)), seen
    assert all(t == len(rows) for _, t in seen)


@check("run: answers keep the caller's order even though they finish out of order")
def _():
    import time as _t
    rows = list(ROWS.itertuples())

    class Staggered(StubClient):
        """Later pages come back first, so a naive as_completed would scramble the order."""
        def __init__(self, payload):
            super().__init__(payload)
            self._n = 0

        @property
        def messages(self):
            parent = self

            class M:
                def create(inner, **kw):
                    parent._n += 1
                    i = parent._n
                    _t.sleep(0.02 * max(0, 4 - i))
                    parent.calls += 1
                    parent.seen.append(kw)
                    return StubResponse(dict(parent.payload, evidence="page-%d" % i))
            return M()

        @messages.setter
        def messages(self, v):
            pass

    out = L.run(Staggered(ANSWER), rows, concurrency=4)
    assert len(out) == len(rows)
    assert all(o["type"] == ANSWER["type"] for o in out), "every row must get an answer"
    assert all(o is not None for o in out), "no gaps in the output list"


@check("run: one failed page does not lose the scan")
def _():
    rows = list(ROWS.itertuples())
    out = L.run(StubClient(ANSWER, fail_on=2), rows, concurrency=1)
    bad = [o for o in out if o["type"] is None]
    assert len(bad) == 1 and "stub failure" in bad[0]["error"]
    assert len(out) == len(rows)


@check("apply_llm: LLM label wins, cheap label is kept, status follows the LLM's own confidence")
def _():
    def pred():
        return C.Prediction(url="u", page_type="Product Information", type_conf=0.3,
                            audience="General Public", audience_conf=0.4, declared_audience="",
                            tier="rules", status="llm_review")
    for conf, status in [(3, "auto"), (2, "sampled"), (1, "human_review")]:
        p = pred()
        C.apply_llm([p], [0], [dict(ANSWER, confidence=conf)])
        assert (p.page_type, p.audience) == (ANSWER["type"], ANSWER["audience"])
        assert (p.cascade_type, p.cascade_audience) == ("Product Information", "General Public")
        assert (p.tier, p.status, p.llm_conf) == ("llm", status, conf)
        assert (p.type_conf, p.audience_conf) == L.CONF_ACC[conf]
        assert p.agree_type is False and p.agree_audience is False
    p = pred()                                        # failed request keeps the cheap answer
    C.apply_llm([p], [0], [dict(type=None, audience=None, confidence=0, error="boom")])
    assert (p.page_type, p.tier, p.status) == ("Product Information", "rules", "llm_error")
    assert json.loads(p.to_json())["cascade_type"] == "Product Information"


# ------------------------------------------------- URL-rule boundary guards (REPORT 4c)

def url_hits(url):
    """Type labels whose URL rules fire on `url`, matched against the same string the classifier uses."""
    f = preprocess.build(dict(url=url, mime="text/html", is_pdf=False, pdf_pages=0,
                              depth=url.count("/"), lines=[], body_lines=[]))
    field = rules._fields(f)["u"]
    return {label for label, rs in rules.TYPE_RULES.items()
            for axis, pat, w in rs if axis == "u" and pat.search(field)}


@check("rules: 'form' does not fire inside medicalinformation / prescribing-information / ?format=")
def _():
    for u in ["https://medicalinformation.astrazeneca-us.com/home.html",
              "https://www.astrazeneca.com/prescribing-information/tagrisso.pdf",
              "https://www.astrazeneca.com/content?format=pdf"]:
        assert "Form / Request" not in url_hits(u), u


@check("rules: 'form' still fires on a real form path")
def _():
    assert "Form / Request" in url_hits("https://www.astrazeneca.com/contact/form")
    assert "Form / Request" in url_hits("https://www.azone.es/formulario-de-contacto")


@check("rules: 'data' does not fire on /datasets/ but does on a clinical-data path")
def _():
    assert "Clinical Evidence" not in url_hits("https://huggingface.co/datasets/squad")
    assert "Clinical Evidence" in url_hits("https://www.astrazeneca.com/clinical-data/trials")


@check("rules: the deliberate stems from REPORT 4c still match the longer word")
def _():
    assert "Sustainability" in url_hits("https://www.astrazeneca.com/sustainability/report-2025")
    assert url_hits("https://www.astrazeneca.com/oncology/lung-cancer"), "oncolog stem should still fire"


# --------------------------------------------------------------------- scan reader

@check("featurise: keeps HTTP 200 HTML and PDF, drops errors, images and empty shells")
def _():
    recs = [record("https://www.astrazeneca.com/ok", BODY),
            record("https://www.astrazeneca.com/doc.pdf", BODY, "application/pdf", pages=3),
            record("https://www.astrazeneca.com/404", BODY, status="404"),
            record("https://www.astrazeneca.com/logo.png", BODY, "image/png"),
            record("https://www.astrazeneca.com/empty", "hi")]
    kept = scan.featurise(recs).set_index("url")
    assert set(kept.index) == {"https://www.astrazeneca.com/ok",
                               "https://www.astrazeneca.com/doc.pdf"}, list(kept.index)
    assert kept.loc["https://www.astrazeneca.com/doc.pdf", "is_pdf"]


@check("featurise: marks third-party domains and strips per-host boilerplate")
def _():
    nav = "Home | Products | Contact"
    recs = [record("https://www.astrazeneca.com/p%d" % i, nav + "\n" + BODY) for i in range(25)]
    recs.append(record("https://pubmed.ncbi.nlm.nih.gov/123/", BODY))
    out = scan.featurise(recs).set_index("url")
    assert out.loc["https://pubmed.ncbi.nlm.nih.gov/123/", "third_party"]
    assert not out.loc["https://www.astrazeneca.com/p0", "third_party"]
    assert nav not in out.loc["https://www.astrazeneca.com/p0", "body"], "nav line should be boilerplate"


# ----------------------------------------------------------------------- taxonomy

@check("taxonomy: every label in the code appears in the annotation guide the LLM is given")
def _():
    guide = open("gold/ANNOTATION_GUIDE.md", encoding="utf-8").read()
    missing = [t for t in TYPES + AUD if t not in guide]
    assert not missing, "labels absent from the guide: %s" % missing


if __name__ == "__main__":
    for n in PASS:
        print("PASS  %s" % n)
    for n, e in FAIL:
        print("FAIL  %s\n      %s" % (n, e))
    print("\n%d passed, %d failed" % (len(PASS), len(FAIL)))
    sys.exit(1 if FAIL else 0)
