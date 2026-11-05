"""Leave-one-site-out (LOSO) benchmark of every approach, for Type and Audience.

For each of the 10 sites: train on gold labels of the other 9, score the held-out site cold.
Outputs results/oof_{task}.parquet (per-item predictions + confidence per approach) and
results/benchmark.json. Weighted accuracy ('acc_pop') re-weights the stratified gold sample to
the (de-duplicated) crawl population.
"""
import json
import sys
import time
import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")
sys.path.insert(0, "src")
from pagecat import models as M
from pagecat.evaluate import ece, summarize
from pagecat.taxonomy import AUD, AUDIENCES, PAGE_TYPES, TYPES

gold = pd.read_parquet("gold/gold_final.parquet")           # features + final labels + weights
feat = pd.read_parquet("data/features.parquet")[["uid", "host_decl_hcp", "host_decl_pat"]]
gold = gold.drop(columns=[c for c in ("host_decl_hcp", "host_decl_pat") if c in gold]).merge(feat, on="uid", how="left")
E_all = np.load("data/emb.npy")
E = E_all[gold.uid.values]
EH = np.load("data/emb_head.npy")[gold.uid.values]
EC = np.hstack([E, EH])                                       # page-content + page-header embeddings
sites = sorted(gold.site.unique())

from sentence_transformers import SentenceTransformer
enc = SentenceTransformer("intfloat/multilingual-e5-small", device="cpu")
encode = lambda t: enc.encode(t, normalize_embeddings=True, show_progress_bar=False)

TASKS = {"type": (TYPES, PAGE_TYPES), "audience": (AUD, AUDIENCES)}
RESULTS, TIMES = {}, {}


def align(classes, P, labels):
    out = np.zeros((len(P), len(labels)))
    for j, c in enumerate(classes):
        out[:, labels.index(c)] = P[:, j]
    return out


for task, (labels, desc) in TASKS.items():
    y = gold[task].values
    approaches = {
        "rules": lambda: M.Rules(task),
        "tfidf_lr": lambda: M.TfidfLR(),
        "emb_lr": lambda: M.EmbLR(),
        "zeroshot_emb": lambda: M.ZeroShot(desc, encode),
        "fusion_lr": lambda: M.FusionLR(),
        "fusion_head_lr": lambda: M.FusionLR(),
    }
    MAT = {"fusion_head_lr": EC}
    oof = {a: np.zeros((len(gold), len(labels))) for a in approaches}
    for a, mk in approaches.items():
        t0 = time.time()
        for s in sites:
            te, tr = (gold.site == s).values, (gold.site != s).values
            X = MAT.get(a, E)
            m = mk().fit(gold[tr], X[tr], y[tr])
            cl, P = m.predict_proba(gold[te], X[te])
            oof[a][te] = align(cl, P, labels)
        TIMES[(task, a)] = time.time() - t0
        print(f"[{task}] {a:13s} done in {TIMES[(task,a)]:.0f}s", flush=True)

    # ---- cascade: rules when confident, otherwise the fusion model
    for tau in (0.5, 0.6, 0.7, 0.8):
        use_rules = oof["rules"].max(1) >= tau
        oof[f"cascade@{tau}"] = np.where(use_rules[:, None], oof["rules"], oof["fusion_head_lr"])

    rows, df_out = {}, gold[["gid", "uid", "site", "third_party", "is_pdf", "weight", task]].copy()
    for a, P in oof.items():
        pred = np.array(labels)[P.argmax(1)]
        conf = P.max(1)
        df_out[f"{a}__pred"], df_out[f"{a}__conf"] = pred, conf
        r = summarize(y, pred, gold.weight.values, labels)
        r["ece"] = ece(conf, pred == y)
        own = ~gold.third_party.values
        r["acc_own_domain"] = float((pred[own] == y[own]).mean())
        r["acc_third_party"] = float((pred[~own] == y[~own]).mean())
        r["per_site"] = {s: float((pred[(gold.site == s).values] == y[(gold.site == s).values]).mean()) for s in sites}
        r["worst_site"] = min(r["per_site"].values())
        if a.startswith("cascade"):
            tau = float(a.split("@")[1])
            r["share_rules_tier"] = float((oof["rules"].max(1) >= tau).mean())
        rows[a] = r
    RESULTS[task] = rows
    df_out.to_parquet(f"results/oof_{task}.parquet")
    tab = pd.DataFrame({a: {k: v for k, v in r.items() if k in ("acc", "acc_pop", "macro_f1", "ece", "acc_own_domain", "worst_site")}
                        for a, r in rows.items()}).T.round(3)
    print(f"\n=== {task.upper()} (LOSO, n={len(gold)}) ===\n{tab.to_string()}\n", flush=True)

json.dump(dict(results=RESULTS, fit_predict_seconds={f"{k[0]}:{k[1]}": v for k, v in TIMES.items()}),
          open("results/benchmark.json", "w", encoding="utf-8"), indent=1, default=float)
