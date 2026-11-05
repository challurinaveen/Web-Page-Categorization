"""Tier 3 - LLM classification of the pages the cheap tiers cannot settle, or of every page.

STATUS: measured on the 800-page gold set with Haiku 5.5 by scripts/11_llm_pilot.py, and wired into
the prototype CLI (scripts/classify_scan.py --llm). See the README, "The LLM tier, measured".
Written against the Messages API (output_config.format JSON schema, cached system prompt, effort "low").
Note: the model emits a thinking block before the answer, so max_tokens must leave room for both - an initial
budget of 300 truncated ~19% of answers.

The system prompt is the annotation guide itself (taxonomy + decision rules), so the same text that made
the gold labels drives the model; it is identical for every request and therefore prompt-cacheable.
"""
import json
import os
from concurrent.futures import ThreadPoolExecutor, as_completed

from .taxonomy import AUD, TYPES, VERSION

MODEL = os.environ.get("PAGECAT_LLM_MODEL", "claude-haiku-5-5")      # $0.10 / $0.50 per MTok (<=100K prompt)
GUIDE_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "gold", "ANNOTATION_GUIDE.md")

PRICE = {"claude-haiku-5-5": (0.10, 0.50), "claude-sonnet-5-5": (2.0, 10.0)}   # $/MTok in, out

# Per-page usage measured on the 800-page pilot (results/llm_haiku.jsonl): the guide rides in a cached
# system block (2923 tokens, read at 0.1x), so only the page view plus request framing pay full input price.
CACHE_TOKENS, FRAMING_TOKENS, OUT_TOKENS = 2923, 183, 180

# P(correct) per self-reported confidence, measured on the gold set (results/llm_haiku_summary.json,
# the README, "The LLM tier, measured") as (type, audience). Lets type_conf/audience_conf keep one meaning - calibrated
# P(correct) - whichever tier produced the label. 0 = request failed.
CONF_ACC = {3: (0.926, 0.974), 2: (0.760, 0.876), 1: (0.489, 0.689), 0: (0.0, 0.0)}

SCHEMA = {
    "type": "object",
    "properties": {
        "type": {"type": "string", "enum": TYPES},
        "audience": {"type": "string", "enum": AUD},
        "confidence": {"type": "integer", "enum": [1, 2, 3]},
        "evidence": {"type": "string"},
    },
    "required": ["type", "audience", "confidence", "evidence"],
    "additionalProperties": False,
}


def page_view(row, body_chars=550, head_chars=350) -> str:
    """The same compact view the human/LLM annotators saw: URL + text only."""
    kind = ("PDF, %d pages" % row.pdf_pages if row.is_pdf else "HTML") + (", external domain" if row.third_party else "")
    return json.dumps(dict(url=row.url, title=row.title[:160], lang=row.lang, kind=kind,
                           header_text=row.head[:head_chars], body_text=" ".join(row.body[:body_chars].split())),
                      ensure_ascii=False)


def classify(client, row, model=None):
    """One page -> dict(type, audience, confidence 1-3, evidence). `client` = anthropic.Anthropic()."""
    system = [{"type": "text", "text": open(GUIDE_PATH).read() +
               "\nReply with the JSON object only: type, audience, confidence (3 certain, 2 probable, 1 guess) "
               "and a <=15-word evidence quote/reason.", "cache_control": {"type": "ephemeral"}}]
    r = client.messages.create(model=model or MODEL, max_tokens=1500, system=system,
                               output_config={"effort": "low", "format": {"type": "json_schema", "schema": SCHEMA}},
                               messages=[{"role": "user", "content": page_view(row)}])
    if r.stop_reason == "refusal":                    # safety classifiers: route to a human, never guess
        return dict(type="Other", audience="Unclear", confidence=1, evidence="model refused", usage=r.usage)
    text = next((b.text for b in r.content if b.type == "text"), None)
    if text is None or r.stop_reason == "max_tokens":
        raise RuntimeError("no complete answer (stop_reason=%s)" % r.stop_reason)
    out = json.loads(text)
    out["usage"] = r.usage
    out["taxonomy"] = VERSION
    return out


def estimate_usd(rows, model=None):
    """Pre-flight cost of classifying `rows`, in USD. Never touches the API.

    Token counts are the measured per-page ones above plus the real length of each page view
    (chars/3.2, the same rule as scripts/09_scale_cost.py), so this is an estimate, not a quote.
    """
    n = len(rows)
    if not n:
        return 0.0
    pi, po = PRICE.get(model or MODEL, (0.0, 0.0))
    inp = sum(len(page_view(r)) for r in rows) / 3.2 + FRAMING_TOKENS * n
    return (inp * pi + CACHE_TOKENS * n * pi * 0.1          # guide read from cache on every request
            + CACHE_TOKENS * pi * 1.25                      # ...written once, by the first one
            + OUT_TOKENS * n * po) / 1e6


def usd(usages, model=None):
    """What a finished run actually cost, from the API's own usage numbers."""
    pi, po = PRICE.get(model or MODEL, (0.0, 0.0))
    return sum(u["inp"] * pi + u["cread"] * pi * 0.1 + u["cwrite"] * pi * 1.25 + u["out"] * po
               for u in usages) / 1e6


def run(client, rows, model=None, concurrency=8, on_progress=None):
    """Classify `rows` (feature rows from scan.featurise) in parallel; one dict per row, input order.

    A failed request yields type=None plus `error` instead of raising, so one bad page cannot lose a
    whole scan - the caller keeps the cheap tier's label for those rows and reports the count.

    on_progress(done, total) is called once per finished page, and only ever from the thread that
    called run() - never from a worker. That matters because the obvious thing to drive with it is
    a UI progress bar, and some are not thread-safe: Streamlit raises NoSessionContext if one of
    its widgets is touched from a pool thread.
    """
    rows = list(rows)
    total = len(rows)
    if not total:
        return []
    model = model or MODEL

    def one(r):
        try:
            o = classify(client, r, model=model)
            u = o.pop("usage")
            o["usage"] = dict(inp=u.input_tokens, out=u.output_tokens,
                              cread=getattr(u, "cache_read_input_tokens", 0) or 0,
                              cwrite=getattr(u, "cache_creation_input_tokens", 0) or 0)
        except Exception as e:                            # keep going; classify_scan reports the tally
            o = dict(type=None, audience=None, confidence=0, evidence="",
                     error="%s: %s" % (type(e).__name__, str(e)[:200]))
        return o

    out = [None] * total
    out[0] = one(rows[0])                                 # serial first: writes the cache the rest read
    if on_progress:
        on_progress(1, total)
    if total > 1:
        with ThreadPoolExecutor(concurrency) as ex:
            futures = {ex.submit(one, r): i for i, r in enumerate(rows[1:], start=1)}
            for done, fut in enumerate(as_completed(futures), start=2):
                out[futures[fut]] = fut.result()          # index keeps the caller's order
                if on_progress:
                    on_progress(done, total)
    return out
