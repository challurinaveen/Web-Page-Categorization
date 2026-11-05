"""Final gold = A/B where they agree, adjudicated label where they did not."""
import glob, json
import pandas as pd
import sys
sys.path.insert(0, "src")
from pagecat.taxonomy import AUD, TYPES

def load(p):
    rows = [json.loads(l) for f in sorted(glob.glob(p)) for l in open(f) if l.strip()]
    return pd.DataFrame(rows).drop_duplicates("gid", keep="last").set_index("gid")

A, B, J = load("gold/ann_A_*.jsonl"), load("gold/ann_B_*.jsonl"), load("gold/adj.jsonl")
B = B.reindex(A.index)
g = pd.read_parquet("gold/gold_sample.parquet").set_index("gid")
lab = pd.DataFrame(index=g.index)
for c in ("type", "audience"):
    lab[c] = A[c].where(A[c] == B[c])
    adj = J[c].reindex(lab.index)
    lab[c] = lab[c].fillna(adj)
lab["source"] = ((A.type == B.type) & (A.audience == B.audience)).map({True: "agreed", False: "adjudicated"})
assert lab.type.isin(TYPES).all() and lab.audience.isin(AUD).all(), "unlabelled/invalid"
out = g.join(lab).reset_index()
out.to_parquet("gold/gold_final.parquet")
print(out.source.value_counts().to_dict())
print(out.type.value_counts().to_string()); print(out.audience.value_counts().to_string())
print(pd.crosstab(out.site.str.replace("www.", ""), out.audience))
