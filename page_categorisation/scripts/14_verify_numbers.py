"""Re-compute the figures quoted in Week1_Prototype_Review.pptx / README.md straight from data/ and results/."""
import json, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import pandas as pd
from pagecat.models import row_to_features
from pagecat.rules import declared_audience, AUD_RULES

R = pd.read_parquet("data/records.parquet"); F = pd.read_parquet("data/features.parquet"); g = pd.read_parquet("gold/gold_final.parquet")
sz = R.groupby("site").size()
print(f"records {len(R)}, sites {R.site.nunique()}, per site {sz.min()}-{sz.max()}")
print("units", len(F), "html/pdf", (~F.is_pdf).sum(), F.is_pdf.sum(), "| third-party share", round(F.third_party.mean(), 3))
print("languages", F.lang.value_counts(normalize=True).head(3).round(3).to_dict(), "n_langs", F.lang.nunique())
print("majority baseline: type", round(g.type.value_counts(normalize=True).iloc[0], 3), "audience", round(g.audience.value_counts(normalize=True).iloc[0], 3))
g = g.merge(F[["uid", "host_decl_hcp", "host_decl_pat"]], on="uid", how="left")
g["dec"] = [declared_audience(row_to_features(r)) for r in g.itertuples()]
hits = [rx for fld, rx, w in AUD_RULES["Healthcare Professional"] if fld == "h"]
g["own"] = [any(rx.search(h) for rx in hits) for h in g["head"]]
th = g[g.audience == "Healthcare Professional"]
print("true-HCP pages", len(th), "own-header declaration", round(th.own.mean(), 3), "incl. host", round((th.dec == "Healthcare Professional").mean(), 3))
d = g[g.dec == "Healthcare Professional"]
print("counted HCP-only", len(d), "| patient-facing", int((d.audience == "Patient / Caregiver").sum()), "| of those with own-header declaration", int(((d.audience == "Patient / Caregiver") & d.own).sum()))
h = F.groupby("host").agg(n=("uid", "size"), hcp=("host_decl_hcp", "max")).query("n>=5").sort_values("hcp", ascending=False)
print(h.head(5).round(2).to_string())
corp = ["www.astrazeneca.com", "www.astrazeneca-us.com", "www.astrazeneca.es", "www.astrazenecaconnect.net", "www.az-oncology.jp"]
print("corporate max", round(F[F.host.isin(corp)].host_decl_hcp.max(), 3))
