"""Analyse the Haiku 5.5 pilot (results/llm_haiku.jsonl) against the gold set and the cheap cascade.

Everything printed / written to results/llm_haiku_summary.json is measured from those files.
usage: 12_llm_analysis.py [WALL_SECONDS_OF_PILOT_RUN]
"""
import glob
import json
import os
import re
import sys

import numpy as np
import pandas as pd

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
os.chdir(ROOT)
WALL = float(sys.argv[1]) if len(sys.argv) > 1 else None
rng = np.random.default_rng(0)

g = pd.read_parquet("gold/gold_final.parquet")
L = pd.DataFrame([json.loads(l) for l in open("results/llm_haiku.jsonl")])
assert L.type.notna().all(), "run has errors"
d = g.merge(L, on="gid", suffixes=("_gold", "_llm"))
d["ok_t"] = d.type_gold == d.type_llm
d["ok_a"] = d.audience_gold == d.audience_llm
O = pd.read_parquet("results/cascade_oof.parquet")
d = d.merge(O[["gid", "pred_type", "pred_aud"]], on="gid")
d["casc_t"] = d.pred_type == d.type_gold
d["casc_a"] = d.pred_aud == d.audience_gold
n = len(d)
S = {"n": n}


def boot(ok, w=None, B=2000):
    ok = np.asarray(ok, float)
    w = np.ones(len(ok)) if w is None else np.asarray(w, float)
    idx = rng.integers(0, len(ok), (B, len(ok)))
    est = (ok[idx] * w[idx]).sum(1) / w[idx].sum(1)
    return [float(np.percentile(est, 2.5)), float(np.percentile(est, 97.5))]


def wilson(k, m, z=1.96):
    p = k / m
    c = (p + z * z / (2 * m)) / (1 + z * z / m)
    h = z * np.sqrt(p * (1 - p) / m + z * z / (4 * m * m)) / (1 + z * z / m)
    return [float(c - h), float(c + h)]


# ---- overall ----
for ax, col, cc in (("type", "ok_t", "casc_t"), ("audience", "ok_a", "casc_a")):
    S[ax] = dict(
        llm=float(d[col].mean()), llm_ci=boot(d[col]), llm_weighted=float(np.average(d[col], weights=d.weight)), llm_weighted_ci=boot(d[col], d.weight),
        cascade=float(d[cc].mean()), cascade_weighted=float(np.average(d[cc], weights=d.weight)),
        paired_gain=float(d[col].mean() - d[cc].mean()),
        only_llm_right=int((d[col] & ~d[cc]).sum()), only_cascade_right=int((~d[col] & d[cc]).sum()))
    print(f"{ax:9s} Haiku {S[ax]['llm']:.1%} CI {S[ax]['llm_ci'][0]:.1%}-{S[ax]['llm_ci'][1]:.1%} | weighted {S[ax]['llm_weighted']:.1%} | cascade {S[ax]['cascade']:.1%} | "
          f"LLM-only-right {S[ax]['only_llm_right']} vs cascade-only-right {S[ax]['only_cascade_right']}")

# ---- self-reported confidence ----
rows = []
for c in (3, 2, 1):
    m = d.confidence == c
    rows.append(dict(conf=c, n=int(m.sum()), share=float(m.mean()), type_acc=float(d.ok_t[m].mean()), type_ci=wilson(int(d.ok_t[m].sum()), int(m.sum())),
                     aud_acc=float(d.ok_a[m].mean()), aud_ci=wilson(int(d.ok_a[m].sum()), int(m.sum()))))
S["by_confidence"] = rows
for r in rows:
    print(f"conf {r['conf']}: {r['n']:3d} pages ({r['share']:.1%})  type {r['type_acc']:.1%} {r['type_ci'][0]:.0%}-{r['type_ci'][1]:.0%}  audience {r['aud_acc']:.1%}")
cum = []
for thr in (3, 2, 1):
    m = d.confidence >= thr
    cum.append(dict(min_conf=thr, coverage=float(m.mean()), type_acc=float(d.ok_t[m].mean()), aud_acc=float(d.ok_a[m].mean())))
S["cumulative"] = cum
print("cumulative (accept conf >= k):", [(c["min_conf"], round(c["coverage"], 3), round(c["type_acc"], 3), round(c["aud_acc"], 3)) for c in cum])

# ---- vs the raw annotators (gold was built from them, so compare raw agreement, not gold accuracy) ----
def load(tag):
    r = []
    for f in sorted(glob.glob(f"gold/ann_{tag}_*.jsonl")):
        r += [json.loads(l) for l in open(f) if l.strip()]
    return pd.DataFrame(r).drop_duplicates("gid").set_index("gid")


A, B = load("A"), load("B")
d = d.set_index("gid")
S["agreement_with_annotators"] = {}
for tag, X in (("A", A), ("B", B)):
    X = X.reindex(d.index)
    S["agreement_with_annotators"][tag] = dict(type=float((X.type == d.type_llm).mean()), audience=float((X.audience == d.audience_llm).mean()))
S["annotator_A_vs_B"] = dict(type=float((A.reindex(d.index).type == B.reindex(d.index).type).mean()), audience=float((A.reindex(d.index).audience == B.reindex(d.index).audience).mean()))
print("Haiku vs raw annotator A/B:", S["agreement_with_annotators"], "| A vs B:", S["annotator_A_vs_B"])
d = d.reset_index()

# ---- per site ----
ps = d.groupby("site").agg(n=("gid", "size"), llm_type=("ok_t", "mean"), llm_aud=("ok_a", "mean"), casc_type=("casc_t", "mean"), casc_aud=("casc_a", "mean")).round(3)
S["per_site"] = ps.reset_index().to_dict("records")
print(ps.to_string())
print("worst/best site, LLM type: %.0f%% / %.0f%%; audience %.0f%% / %.0f%%" % (100 * ps.llm_type.min(), 100 * ps.llm_type.max(), 100 * ps.llm_aud.min(), 100 * ps.llm_aud.max()))

# ---- slices ----
S["slices"] = {}
for name, m in (("html", ~d.is_pdf), ("pdf", d.is_pdf), ("own_domain", ~d.third_party), ("external", d.third_party)):
    S["slices"][name] = dict(n=int(m.sum()), type=float(d.ok_t[m].mean()), aud=float(d.ok_a[m].mean()), cascade_type=float(d.casc_t[m].mean()), cascade_aud=float(d.casc_a[m].mean()))
    print(f"{name:10s} n={m.sum():3d} Haiku type {d.ok_t[m].mean():.1%} aud {d.ok_a[m].mean():.1%} | cascade type {d.casc_t[m].mean():.1%} aud {d.casc_a[m].mean():.1%}")

# ---- per class recall (n >= 10) ----
pc = []
for c, m in d.groupby("type_gold"):
    if len(m) >= 10:
        pc.append(dict(cls=c, n=len(m), llm_recall=float(m.ok_t.mean()), cascade_recall=float(m.casc_t.mean())))
pc = sorted(pc, key=lambda r: -r["n"])
S["per_class_type"] = pc
print("per-class recall (n>=10):")
for r in pc:
    print(f"  {r['cls']:28s} n={r['n']:3d} Haiku {r['llm_recall']:.0%}  cascade {r['cascade_recall']:.0%}")
pa = []
for c, m in d.groupby("audience_gold"):
    pa.append(dict(cls=c, n=len(m), llm_recall=float(m.ok_a.mean()), cascade_recall=float(m.casc_a.mean())))
S["per_class_audience"] = pa
print("audience recall:", [(r["cls"], r["n"], round(r["llm_recall"], 2)) for r in pa])

# ---- most common mistakes ----
err = d[~d.ok_t].groupby(["type_gold", "type_llm"]).size().sort_values(ascending=False).head(8)
S["top_type_confusions"] = [dict(gold=a, llm=b, n=int(v)) for (a, b), v in err.items()]
print("top type confusions (gold -> Haiku):")
for r in S["top_type_confusions"]:
    print(f"  {r['gold']} -> {r['llm']}: {r['n']}")
erra = d[~d.ok_a].groupby(["audience_gold", "audience_llm"]).size().sort_values(ascending=False).head(6)
S["top_aud_confusions"] = [dict(gold=a, llm=b, n=int(v)) for (a, b), v in erra.items()]
print("top audience confusions:", [(r["gold"], r["llm"], r["n"]) for r in S["top_aud_confusions"]])

# ---- cost & tokens (measured from API usage) ----
u = pd.DataFrame([x for x in L.usage])
tin, tout, cr, cw = u.inp.sum(), u.out.sum(), u.cread.sum(), u.cwrite.sum()
cost = (tin * 0.10 + cr * 0.10 * 0.1 + cw * 0.10 * 1.25 + tout * 0.50) / 1e6
S["cost"] = dict(usd_total=float(cost), usd_per_1k=float(cost / n * 1000), usd_per_million=float(cost / n * 1e6),
                 avg_uncached_in=float(tin / n), avg_cached_in=float(cr / n), avg_out=float(tout / n), cache_write_tokens=int(cw),
                 usd_per_1k_if_no_cache=float(((tin + cr) * 0.10 + tout * 0.50) / n * 1000 / 1e6),
                 cost_all_10625_pages=float(cost / n * 10625), cost_8622_units=float(cost / n * 8622))
if WALL:
    S["speed"] = dict(wall_seconds=WALL, pages_per_second=float(n / WALL), parallel_requests=8)
print("cost:", json.dumps(S["cost"], indent=1))
print("speed:", S.get("speed"))

# ---- how big must a human check be? (binomial 95% half-width at p=0.8) ----
S["human_check_halfwidth_pts"] = {str(k): float(196 * np.sqrt(0.8 * 0.2 / k)) for k in (80, 100, 200, 400)}
print("human-check half-width (points) at 80% accuracy:", {k: round(v, 1) for k, v in S["human_check_halfwidth_pts"].items()})

# ---- verify the template count quoted in the report ----
f = pd.read_parquet("data/features.parquet")
src = open("scripts/04_sample_gold.py").read()
m = re.search(r"def template\(url: str\) -> str:\n(.*?)\n\n", src, re.S)
ns = {"re": re}
exec("import re\ndef template(url: str) -> str:\n" + m.group(1), ns)
S["templates_all_10625"] = int(f.url.map(ns["template"]).nunique())
print("distinct URL templates over the 10,625 pages:", S["templates_all_10625"], "| units:", len(f))

json.dump(S, open("results/llm_haiku_summary.json", "w"), indent=1)
d.to_parquet("results/llm_haiku_scored.parquet")
print("wrote results/llm_haiku_summary.json")
