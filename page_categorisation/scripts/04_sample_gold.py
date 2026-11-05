"""Draw the gold-set sample: 80 units per site, stratified by URL template.

Why template strata: a crawl is dominated by a few templates (513 congress-PDF viewers on one
site, 268 login variants on another). Uniform sampling would let those drown everything else
and flatter any classifier. We allocate ~sqrt(stratum size) per template (every template is seen)
and store the inverse-inclusion-probability weight so *population-level* accuracy can still
be estimated from the sample (weight = N_stratum / n_stratum).

Outputs: gold/gold_items.jsonl  (what annotators see)   gold/gold_sample.parquet (full + weights)
"""
import json
import re

import numpy as np
import pandas as pd

PER_SITE = 80
rng = np.random.default_rng(42)
df = pd.read_parquet("data/features.parquet")


def template(url: str) -> str:
    from urllib.parse import urlparse
    u = urlparse(url)
    segs = [re.sub(r"\d+", "#", s) for s in u.path.split("/") if s]
    key = "/".join(segs[:2]) if segs else "/"
    return f"{u.netloc}|{key}|{'pdf' if u.path.lower().endswith('.pdf') else 'x'}"


df["template"] = df.url.map(template)
# drop true near-duplicates inside a template (same title + same first 200 chars of body)
df["_dupkey"] = df.template + "||" + df.title.str[:60] + "||" + df.body.str[:200]
pop = df.drop_duplicates("_dupkey").copy()
print("population after near-dup removal:", len(pop), "of", len(df))

QUOTA = {("own", "html"): 0.50, ("own", "pdf"): 0.17, ("ext", "html"): 0.25, ("ext", "pdf"): 0.08}
pop["pool"] = list(zip(np.where(pop.third_party, "ext", "own"), np.where(pop.is_pdf, "pdf", "html")))


def sqrt_alloc(g, n):
    """Spread n picks over templates ~ sqrt(size); every template gets >=1 while budget allows."""
    st = g.groupby("template").size()
    a = np.sqrt(st)
    a = np.maximum(1, np.round(a / a.sum() * n)).astype(int)
    a = np.minimum(a, st)
    while a.sum() > n:
        a[a.idxmax()] -= 1
    while a.sum() < n and (a < st).any():
        a[(st - a).idxmax()] += 1
    return a


picked = []
for site, g in pop.groupby("site"):
    quota = {k: int(round(v * PER_SITE)) for k, v in QUOTA.items()}
    short = 0
    for k in QUOTA:                              # pools with too little supply hand their quota to own/html
        have = int((g.pool == k).sum())
        if have < quota[k]:
            short += quota[k] - have
            quota[k] = have
    quota[("own", "html")] += short
    quota[("own", "html")] = min(quota[("own", "html")], int((g.pool == ("own", "html")).sum()))
    while sum(quota.values()) < PER_SITE:        # still short (tiny own-html pool): top up elsewhere
        k = max(QUOTA, key=lambda k: (g.pool == k).sum() - quota[k])
        quota[k] += 1
    for k, n in quota.items():
        gp = g[g.pool == k]
        if n == 0 or gp.empty:
            continue
        for t, m in sqrt_alloc(gp, n).items():
            s_ = gp[gp.template == t]
            take = s_.sample(min(m, len(s_)), random_state=int(rng.integers(1e9)))
            # weight = size of the (pool, template) stratum / how many we drew from it
            picked.append(take.assign(stratum_N=len(s_), stratum_n=len(take)))
gold = pd.concat(picked).reset_index(drop=True)
gold["weight"] = gold.stratum_N / gold.stratum_n
gold["gid"] = [f"G{i:04d}" for i in range(len(gold))]
gold = gold.sample(frac=1, random_state=7).reset_index(drop=True)   # shuffle so chunks mix sites
gold.drop(columns=["_dupkey"]).to_parquet("gold/gold_sample.parquet")


def view(r):
    return dict(
        gid=r.gid, url=r.url, title=r.title[:160], lang=r.lang,
        kind=("PDF, %d pages" % r.pdf_pages if r.is_pdf else "HTML") + (", external domain" if r.third_party else ""),
        header_text=r.head[:350], body_text=re.sub(r"\s+", " ", r.body[:550]),
    )


with open("gold/gold_items.jsonl", "w") as f:
    for r in gold.itertuples():
        f.write(json.dumps(view(r), ensure_ascii=False) + "\n")

print(gold.groupby("site").size().to_string())
print("own/3rd-party:", gold.third_party.value_counts().to_dict(), "| pdf:", int(gold.is_pdf.sum()))
print("distinct templates:", gold.template.nunique())
# chunk into 4 files of 200 for the annotators
items = open("gold/gold_items.jsonl").read().splitlines()
for k in range(4):
    open(f"gold/chunk_{k}.jsonl", "w").write("\n".join(items[k * 200:(k + 1) * 200]) + "\n")
print("chunks:", [len(items[k * 200:(k + 1) * 200]) for k in range(4)])
