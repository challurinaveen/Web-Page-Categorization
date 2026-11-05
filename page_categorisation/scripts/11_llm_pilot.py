"""Pilot of the LLM tier (src/pagecat/llm_tier.py) on the gold set.

usage: 11_llm_pilot.py MODEL N OUT.jsonl      (N = number of gold pages, 0 = all)

The API key is read from ./.env (any NAME= sk-ant-... line); it is never printed.
Reports accuracy vs the gold labels (population-weighted too), agreement by confidence, and real token usage / cost.
"""
import json
import os
import re
import sys
from concurrent.futures import ThreadPoolExecutor

import numpy as np
import pandas as pd

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, os.path.join(ROOT, "src"))

PRICE = {"claude-haiku-5-5": (0.10, 0.50), "claude-sonnet-5-5": (2.0, 10.0)}   # $/MTok in, out (cache read 0.1x, write 1.25x)


def load_key():
    if os.environ.get("ANTHROPIC_API_KEY"):
        return
    m = re.search(r"sk-ant-[A-Za-z0-9_\-]+", open(os.path.join(ROOT, ".env")).read())
    if not m:
        sys.exit("no sk-ant key found in .env")
    os.environ["ANTHROPIC_API_KEY"] = m.group()


def main():
    model, n, out = sys.argv[1], int(sys.argv[2]), sys.argv[3]
    os.environ["PAGECAT_LLM_MODEL"] = model
    load_key()
    import anthropic
    from pagecat import llm_tier
    client = anthropic.Anthropic(max_retries=4)

    g = pd.read_parquet(os.path.join(ROOT, "gold/gold_final.parquet"))
    if n:
        g = g.sample(n, random_state=0)
    rows = list(g.itertuples())

    def run(r):
        try:
            o = llm_tier.classify(client, r)
            u = o.pop("usage")
            o["usage"] = dict(inp=u.input_tokens, out=u.output_tokens,
                              cread=getattr(u, "cache_read_input_tokens", 0) or 0,
                              cwrite=getattr(u, "cache_creation_input_tokens", 0) or 0)
        except Exception as e:                                   # keep going; report at the end
            o = dict(type=None, audience=None, confidence=0, evidence="ERROR %s: %s" % (type(e).__name__, str(e)[:200]))
        o["gid"] = r.gid
        return o

    res = [run(rows[0])]                                         # warm the prompt cache before going parallel
    with ThreadPoolExecutor(8) as ex:
        res += list(ex.map(run, rows[1:]))
    with open(out, "w") as f:
        for o in res:
            f.write(json.dumps(o, ensure_ascii=False) + "\n")

    p = pd.DataFrame(res).merge(g[["gid", "type", "audience", "weight"]], on="gid", suffixes=("_llm", "_gold"))
    err = p.type_llm.isna()
    print("pages %d, errors %d" % (len(p), err.sum()))
    if err.any():
        print(p[err].evidence.value_counts().head(3).to_string())
    q = p[~err]
    if q.empty:
        sys.exit("every request failed - nothing to score")
    w = q.weight
    for ax in ("type", "audience"):
        ok = (q[ax + "_llm"] == q[ax + "_gold"])
        print("%-8s acc %.1f%%  (population-weighted %.1f%%)" % (ax, 100 * ok.mean(), 100 * np.average(ok, weights=w)))
    both = (q.type_llm == q.type_gold)
    for c in (1, 2, 3):
        m = q.confidence == c
        if m.any():
            print("  confidence %d: %4d pages, type acc %.1f%%, audience acc %.1f%%" % (
                c, m.sum(), 100 * both[m].mean(), 100 * (q.audience_llm == q.audience_gold)[m].mean()))
    u = pd.DataFrame([o["usage"] for o in res if "usage" in o])
    pi, po = PRICE.get(model, (np.nan, np.nan))
    cost = (u.inp.sum() * pi + u.cread.sum() * pi * 0.1 + u.cwrite.sum() * pi * 1.25 + u.out.sum() * po) / 1e6
    print("tokens: in %d, cache-read %d, cache-write %d, out %d  ->  $%.4f total, $%.3f per 1000 pages (no batch discount)" % (
        u.inp.sum(), u.cread.sum(), u.cwrite.sum(), u.out.sum(), cost, 1000 * cost / len(u)))


if __name__ == "__main__":
    main()
