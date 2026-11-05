"""Throughput of each tier on this machine + LLM token/cost model + LLM-annotator accuracy proxy."""
import glob, json, sys, time, warnings
import numpy as np, pandas as pd
warnings.filterwarnings("ignore")
sys.path.insert(0, "src")
from pagecat import models as M, rules
from pagecat.llm_tier import page_view

gold = pd.read_parquet("gold/gold_final.parquet")
feat = pd.read_parquet("data/features.parquet")[["uid", "host_decl_hcp", "host_decl_pat"]]
gold = gold.drop(columns=[c for c in ("host_decl_hcp", "host_decl_pat") if c in gold]).merge(feat, on="uid", how="left")
out = {}

# --- tier-1 rules throughput (single core, includes feature object build)
rows = list(gold.itertuples()); t0 = time.time()
for r in rows:
    f = M.row_to_features(r); rules.classify_type(f); rules.classify_audience(f)
out["rules_pages_per_s_1core"] = len(rows) / (time.time() - t0)

# --- LLM prompt size (chars/3.2 token estimate: conservative for multilingual text; no tokenizer access offline)
guide = open("gold/ANNOTATION_GUIDE.md", encoding="utf-8").read()
views = [page_view(r) for r in rows]
tok = lambda s: len(s) / 3.2
sys_tok = tok(guide) + 40
view_tok = np.mean([tok(v) for v in views])
out_tok = 70   # json with enum labels + <=15 word evidence
out.update(system_tokens=sys_tok, page_view_tokens=float(view_tok), output_tokens=out_tok)
P = dict(haiku=(0.10, 0.50), sonnet=(2.0, 10.0))
for m, (pi, po) in P.items():
    per_page = (sys_tok + view_tok) * pi / 1e6 + out_tok * po / 1e6
    out[f"{m}_usd_per_1k_pages_nocache"] = per_page * 1e3
    out[f"{m}_usd_per_1k_pages_batch50"] = per_page * 1e3 * 0.5

# --- LLM annotators vs final gold (proxy for an LLM tier; NOT independent: gold = their agreement + adjudication)
def load(tag):
    rr = [json.loads(l) for f in glob.glob(f"gold/ann_{tag}_*.jsonl") for l in open(f, encoding="utf-8") if l.strip()]
    return pd.DataFrame(rr).drop_duplicates("gid").set_index("gid").reindex(gold.gid)
for tag in "AB":
    a = load(tag)
    out[f"annotator_{tag}_type_acc"] = float((a.type.values == gold.type.values).mean())
    out[f"annotator_{tag}_aud_acc"] = float((a.audience.values == gold.audience.values).mean())
    hi = a.conf.values == 3
    out[f"annotator_{tag}_share_conf3"] = float(hi.mean())
    out[f"annotator_{tag}_type_acc_conf3"] = float((a.type.values == gold.type.values)[hi].mean())
    out[f"annotator_{tag}_aud_acc_conf3"] = float((a.audience.values == gold.audience.values)[hi].mean())
# agreement with the OTHER annotator on items where one says 3 = how well self-reported confidence ranks errors
A, B = load("A"), load("B")
out["llm_conf_vs_agree"] = {int(c): float((A.type == B.type)[A.conf == c].mean()) for c in (1, 2, 3)}

# --- population facts for dedup / template collapse
f = pd.read_parquet("data/features.parquet")
out["units"] = len(f); out["units_third_party"] = int(f.third_party.sum())
import re
from urllib.parse import urlparse
def tpl(u):
    p = urlparse(u); s = [re.sub(r"\d+", "#", x) for x in p.path.split("/") if x]
    return f"{p.netloc}|{'/'.join(s[:2])}"
f["tpl"] = f.url.map(tpl); f["dk"] = f.tpl + "|" + f.title.str[:60] + "|" + f.body.str[:200]
out["units_after_near_dup_removal"] = int(f.dk.nunique()); out["templates"] = int(f.tpl.nunique())
json.dump(out, open("results/scale_cost.json", "w", encoding="utf-8"), indent=1)
for k, v in out.items(): print(f"{k}: {v}")
