"""records.parquet -> features.parquet (classification units only) + language stats."""
import sys
import time

import pandas as pd

sys.path.insert(0, "src")
from pagecat.preprocess import build

df = pd.read_parquet("data/records.parquet")
u = df[df.unit].reset_index(drop=True)
t0 = time.time()
rows = []
for r in u.itertuples():
    f = build(r)
    rows.append(dict(
        uid=len(rows), site=r.site, url=r.url, host=r.host, reg_domain=r.reg_domain,
        third_party=r.third_party, is_pdf=r.is_pdf, pdf_pages=r.pdf_pages, depth=r.depth,
        parent=r.parent, title=f.title, url_toks=" ".join(f.url_toks), lang=f.lang,
        n_body=f.n_body, body=f.body, head=f.head, embed_text=f.embed_text(),
    ))
out = pd.DataFrame(rows)
# site-level context: share of each host's pages whose header carries an explicit audience declaration
from pagecat import rules
from pagecat.models import row_to_features
dec = [rules.declared_audience(row_to_features(r)) for r in out.itertuples()]
out["_dh"], out["_dp"] = [d == "Healthcare Professional" for d in dec], [d == "Patient / Caregiver" for d in dec]
g = out.groupby("host")
out["host_n"] = g.uid.transform("size")
out["host_decl_hcp"] = (g._dh.transform("mean") * (out.host_n >= 5)).astype(float)
out["host_decl_pat"] = (g._dp.transform("mean") * (out.host_n >= 5)).astype(float)
out = out.drop(columns=["_dh", "_dp"])
out.to_parquet("data/features.parquet")
dt = time.time() - t0
print(f"{len(out)} units featurised in {dt:.1f}s  ({len(out)/dt:.0f} pages/s, single core)")
print(out.groupby("site").lang.agg(lambda s: dict(s.value_counts().head(4))).to_string())
print("empty-title share:", (out.title == "").mean().round(3), "| empty body share:", (out.n_body < 40).mean().round(3))
