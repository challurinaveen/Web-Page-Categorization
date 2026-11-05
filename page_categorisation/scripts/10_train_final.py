"""Fit the tier-2 models on ALL gold labels and store them with the tuned cascade config."""
import pickle, sys, json, warnings
import numpy as np, pandas as pd
warnings.filterwarnings("ignore")
sys.path.insert(0, "src")
from pagecat import models as M
gold = pd.read_parquet("gold/gold_final.parquet")
feat = pd.read_parquet("data/features.parquet")[["uid", "host_decl_hcp", "host_decl_pat"]]
gold = gold.drop(columns=[c for c in ("host_decl_hcp", "host_decl_pat") if c in gold]).merge(feat, on="uid", how="left")
X = np.hstack([np.load("data/emb.npy")[gold.uid.values], np.load("data/emb_head.npy")[gold.uid.values]])
mt = M.FusionLR().fit(gold, X, gold.type.values)
ma = M.FusionLR().fit(gold, X, gold.audience.values)
cfg = json.load(open("results/cascade_cfg.json", encoding="utf-8"))
pickle.dump(dict(type_model=mt, aud_model=ma, cfg=cfg), open("models/cascade.pkl", "wb"))
print("saved models/cascade.pkl", cfg["tau_rules_type"], cfg["tau_rules_aud"], cfg["publish"], cfg["review"])
