"""Generalisation diagnostics (deck slide 14): learning curve over # training sites, and
random-split CV (site leaks across the split) vs leave-one-site-out. The gap = pure site shift."""
import json, sys, warnings
import numpy as np, pandas as pd
from sklearn.model_selection import StratifiedKFold, KFold
warnings.filterwarnings("ignore")
sys.path.insert(0, "src")
from pagecat import models as M
from pagecat.taxonomy import AUD, TYPES

task = sys.argv[1]
labels = TYPES if task == "type" else AUD
gold = pd.read_parquet("gold/gold_final.parquet")
feat = pd.read_parquet("data/features.parquet")[["uid", "host_decl_hcp", "host_decl_pat"]]
gold = gold.drop(columns=[c for c in ("host_decl_hcp", "host_decl_pat") if c in gold]).merge(feat, on="uid", how="left")
X = np.hstack([np.load("data/emb.npy")[gold.uid.values], np.load("data/emb_head.npy")[gold.uid.values]])
y = gold[task].values
sites = sorted(gold.site.unique())
rng = np.random.default_rng(0)

def acc(tr, te):
    m = M.FusionLR().fit(gold[tr], X[tr], y[tr]); cl, P = m.predict_proba(gold[te], X[te])
    return float((cl[P.argmax(1)] == y[te]).mean())

curve = {}
for k in (1, 2, 4, 6, 9):
    vals = []
    for s in sites:
        others = [o for o in sites if o != s]
        for rep in range(1 if k == 9 else 2):
            tr_sites = rng.choice(others, k, replace=False)
            vals.append(acc(gold.site.isin(tr_sites).values, (gold.site == s).values))
    curve[k] = (float(np.mean(vals)), float(np.std(vals)))
    print(task, "train sites", k, curve[k], flush=True)

cv = []
for tr, te in KFold(5, shuffle=True, random_state=0).split(X):
    m_tr, m_te = np.zeros(len(gold), bool), np.zeros(len(gold), bool); m_tr[tr] = True; m_te[te] = True
    cv.append(acc(m_tr, m_te))
print(task, "random 5-fold CV (sites mixed):", np.mean(cv))
json.dump(dict(curve=curve, random_cv=float(np.mean(cv))), open(f"results/learning_curve_{task}.json", "w", encoding="utf-8"), indent=1)
