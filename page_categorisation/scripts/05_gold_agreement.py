"""Inter-annotator agreement + adjudication queue.

Reads gold/ann_{A,B}_{0..3}.jsonl, validates label strings against the taxonomy, reports
raw agreement and Cohen's kappa for Type and Audience, and writes the disagreements
to gold/adjudicate.jsonl (annotators' labels + the page view) for a third, informed pass.
"""
import glob
import json
import sys

import pandas as pd

sys.path.insert(0, "src")
from pagecat.evaluate import agreement
from pagecat.taxonomy import AUD, TYPES

def load(tag):
    rows = []
    for f in sorted(glob.glob(f"gold/ann_{tag}_*.jsonl")):
        for l in open(f):
            l = l.strip()
            if l:
                rows.append(json.loads(l))
    d = pd.DataFrame(rows).drop_duplicates("gid", keep="last").set_index("gid")
    return d


A, B = load("A"), load("B")
items = {json.loads(l)["gid"]: json.loads(l) for l in open("gold/gold_items.jsonl")}
common = A.index.intersection(B.index)
print(f"A={len(A)} B={len(B)} common={len(common)} of {len(items)}")
for tag, d in (("A", A), ("B", B)):
    bt, ba = (~d.type.isin(TYPES)).sum(), (~d.audience.isin(AUD)).sum()
    print(f"annotator {tag}: invalid type labels={bt}, invalid audience labels={ba}")
    if bt:
        print("  ", d[~d.type.isin(TYPES)].type.value_counts().head(8).to_dict())
    if ba:
        print("  ", d[~d.audience.isin(AUD)].audience.value_counts().head(8).to_dict())

a, b = A.loc[common], B.loc[common]
res = {}
for col, labels in (("type", TYPES), ("audience", AUD)):
    res[col] = agreement(a[col], b[col], labels)
    print(col, res[col])
# agreement among items where both annotators were confident
both = (a.conf >= 2) & (b.conf >= 2)
print("both conf>=2:", both.mean().round(3),
      "type agree there:", (a.type[both] == b.type[both]).mean().round(3),
      "aud agree there:", (a.audience[both] == b.audience[both]).mean().round(3))

dis_t = a.type != b.type
dis_a = a.audience != b.audience
print("disagree type:", int(dis_t.sum()), "audience:", int(dis_a.sum()), "either:", int((dis_t | dis_a).sum()))
print("\nTop type confusions (A -> B):")
print(pd.Series(list(zip(a.type[dis_t], b.type[dis_t]))).value_counts().head(12).to_string())
print("\nTop audience confusions (A -> B):")
print(pd.Series(list(zip(a.audience[dis_a], b.audience[dis_a]))).value_counts().head(8).to_string())

# adjudication queue
with open("gold/adjudicate.jsonl", "w") as f:
    for gid in common[(dis_t | dis_a).values]:
        it = dict(items[gid])
        it["A"] = dict(type=a.loc[gid, "type"], audience=a.loc[gid, "audience"], note=a.loc[gid].get("note", ""))
        it["B"] = dict(type=b.loc[gid, "type"], audience=b.loc[gid, "audience"], note=b.loc[gid].get("note", ""))
        f.write(json.dumps(it, ensure_ascii=False) + "\n")
json.dump(res, open("results/agreement.json", "w"), indent=1)
# taxonomy-gap notes
notes = pd.concat([A.note, B.note]).dropna()
notes = notes[notes.str.contains("NEW", na=False)]
print("\nNEW-label suggestions:", notes.str.extract(r"NEW:\s*(.*)")[0].str.strip().value_counts().head(10).to_dict())
