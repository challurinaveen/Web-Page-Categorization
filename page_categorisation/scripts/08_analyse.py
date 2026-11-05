"""Post-benchmark analysis: cascade tuning on LOSO predictions, calibration, gating thresholds, figures.

Everything here uses leave-one-site-out predictions only (no item is scored by a model that saw its site).
Writes results/cascade_cfg.json (consumed by the prototype) and figures/*.png.
"""
import json
import sys
import warnings

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression

warnings.filterwarnings("ignore")
sys.path.insert(0, "src")
from pagecat import models as M
from pagecat import rules
from pagecat.cascade import platt
from pagecat.evaluate import confusion, coverage_curve, ece, reliability
from pagecat.taxonomy import AUD, TYPES

plt.rcParams.update({"figure.dpi": 130, "axes.spines.top": False, "axes.spines.right": False, "font.size": 9})
C = dict(rules="#8c8c8c", tfidf="#c98b2b", emb="#4c78a8", zs="#b7b7b7", fusion="#2f6f4f", casc="#b4402f")

gold = pd.read_parquet("gold/gold_final.parquet")
feat = pd.read_parquet("data/features.parquet")[["uid", "host_decl_hcp", "host_decl_pat"]]
gold = gold.drop(columns=[c for c in ("host_decl_hcp", "host_decl_pat") if c in gold]).merge(feat, on="uid", how="left")
ot, oa = pd.read_parquet("results/oof_type.parquet"), pd.read_parquet("results/oof_audience.parquet")
assert (ot.gid.values == gold.gid.values).all()
n = len(gold)

# raw rule confidences (what the prototype thresholds on)
rt = [rules.classify_type(M.row_to_features(r)) for r in gold.itertuples()]
ra = [rules.classify_audience(M.row_to_features(r)) for r in gold.itertuples()]
rt_lab, rt_c = np.array([r.label or "Other" for r in rt]), np.array([r.confidence if r.label else 0 for r in rt])
ra_lab, ra_c = np.array([r.label or "Unclear" for r in ra]), np.array([r.confidence if r.label else 0 for r in ra])
mt_lab, mt_c = ot["fusion_head_lr__pred"].values, ot["fusion_head_lr__conf"].values
ma_lab, ma_c = oa["fusion_head_lr__pred"].values, oa["fusion_head_lr__conf"].values
yt, ya = gold.type.values, gold.audience.values

# ---------------------------------------------------------------- 1. choose rule-acceptance thresholds
grid = [0.0, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.01]
rows = []
for tt in grid:
    for ta in grid:
        ok = (rt_c >= tt) & (ra_c >= ta) & (rt_c > 0) & (ra_c > 0)
        T = np.where(ok, rt_lab, mt_lab); A = np.where(ok, ra_lab, ma_lab)
        rows.append(dict(tau_type=tt, tau_aud=ta, share_rules=ok.mean(), type_acc=(T == yt).mean(), aud_acc=(A == ya).mean()))
sweep = pd.DataFrame(rows)
sweep["score"] = (sweep.type_acc + sweep.aud_acc) / 2
best = sweep.sort_values("score", ascending=False).iloc[0]
print("rule-threshold sweep (top 5 by mean(type_acc, aud_acc))\n", sweep.sort_values("score", ascending=False).head(5).round(3).to_string())
tt, ta = float(best.tau_type), float(best.tau_aud)
ok = (rt_c >= tt) & (ra_c >= ta) & (rt_c > 0) & (ra_c > 0)
T_lab = np.where(ok, rt_lab, mt_lab); A_lab = np.where(ok, ra_lab, ma_lab)
T_raw = np.where(ok, rt_c, mt_c); A_raw = np.where(ok, ra_c, ma_c)
print(f"\nchosen tau_type={tt} tau_aud={ta}; rules tier handles {ok.mean():.1%}; "
      f"cascade type acc={(T_lab==yt).mean():.3f} (rules-only {(rt_lab==yt).mean():.3f}, model-only {(mt_lab==yt).mean():.3f}), "
      f"audience acc={(A_lab==ya).mean():.3f} (rules-only {(ra_lab==ya).mean():.3f}, model-only {(ma_lab==ya).mean():.3f}), "
      f"audience majority baseline={(pd.Series(ya).value_counts(normalize=True).iloc[0]):.3f}")

# ---------------------------------------------------------------- 2. calibration (Platt per tier)
def fit_platt(conf, correct):
    if len(conf) < 15 or correct.min() == correct.max():
        return [1.0, 0.0]
    c = np.clip(conf, 1e-4, 1 - 1e-4)
    lr = LogisticRegression(C=1e3).fit(np.log(c / (1 - c))[:, None], correct)
    return [float(lr.coef_[0, 0]), float(lr.intercept_[0])]

cal = dict(
    rules_type=fit_platt(rt_c[ok], (rt_lab == yt)[ok]), rules_aud=fit_platt(ra_c[ok], (ra_lab == ya)[ok]),
    model_type=fit_platt(mt_c[~ok], (mt_lab == yt)[~ok]), model_aud=fit_platt(ma_c[~ok], (ma_lab == ya)[~ok]))
Tc = np.where(ok, platt(T_raw, cal["rules_type"]), platt(T_raw, cal["model_type"]))
Ac = np.where(ok, platt(A_raw, cal["rules_aud"]), platt(A_raw, cal["model_aud"]))
for nm, raw, cc, lab, y in (("type", T_raw, Tc, T_lab, yt), ("audience", A_raw, Ac, A_lab, ya)):
    print(f"{nm}: ECE raw={ece(raw, lab == y):.3f} -> calibrated={ece(cc, lab == y):.3f}")

# ---------------------------------------------------------------- 3. gating thresholds on joint confidence
joint = np.minimum(Tc, Ac)
both_ok = (T_lab == yt) & (A_lab == ya)
avg_ok = ((T_lab == yt).astype(float) + (A_lab == ya)) / 2
cur = pd.DataFrame([dict(thr=t, coverage=(joint >= t).mean(), acc_type=(T_lab == yt)[joint >= t].mean(),
                         acc_aud=(A_lab == ya)[joint >= t].mean(), acc_both=both_ok[joint >= t].mean() if (joint >= t).any() else np.nan)
                    for t in np.round(np.arange(0.2, 0.96, 0.05), 2)])
print("\njoint-confidence gate (LOSO):\n", cur.round(3).to_string(index=False))

def pick(target):
    c = cur[(cur.acc_type >= target) & (cur.acc_aud >= target) & (cur.coverage >= 0.02)]
    return None if c.empty else float(c.thr.iloc[0])
publish = pick(0.90) or 0.9
review = pick(0.75) or 0.5
cfg = dict(tau_rules_type=tt, tau_rules_aud=ta, publish=publish, review=review, cal=cal,
           note="thresholds from leave-one-site-out predictions on 800 gold pages; re-fit on every new gold batch")
json.dump(cfg, open("results/cascade_cfg.json", "w", encoding="utf-8"), indent=1)
st = np.where(joint >= publish, "auto", np.where(joint >= review, "sampled", "llm_review"))
tier = pd.DataFrame(dict(status=st, tc=T_lab == yt, ac=A_lab == ya, site=gold.site))
print(f"\npublish>={publish}, review>={review}")
print(tier.groupby("status").agg(share=("tc", lambda s: len(s) / n), type_acc=("tc", "mean"), aud_acc=("ac", "mean")).round(3))
print("per-site share needing LLM/human review:", tier.assign(r=tier.status == "llm_review").groupby("site").r.mean().round(2).to_dict())
json.dump(dict(cascade_type_acc=float((T_lab == yt).mean()), cascade_aud_acc=float((A_lab == ya).mean()),
               rules_share=float(ok.mean()), status_share=tier.status.value_counts(normalize=True).to_dict(),
               status_type_acc=tier.groupby("status").tc.mean().to_dict(), status_aud_acc=tier.groupby("status").ac.mean().to_dict()),
          open("results/cascade_summary.json", "w", encoding="utf-8"), indent=1)
pd.DataFrame(dict(gid=gold.gid, site=gold.site, third_party=gold.third_party, true_type=yt, pred_type=T_lab, type_conf=Tc,
                  true_aud=ya, pred_aud=A_lab, aud_conf=Ac, status=st, url=gold.url)).to_parquet("results/cascade_oof.parquet")

# ---------------------------------------------------------------- 4. figures
bj = json.load(open("results/benchmark.json", encoding="utf-8"))["results"]
names = [("rules", "Rules", C["rules"]), ("tfidf_lr", "TF-IDF + LR", C["tfidf"]), ("emb_lr", "Embedding + LR", C["emb"]),
         ("zeroshot_emb", "Zero-shot embedding", C["zs"]), ("fusion_head_lr", "Fusion (emb+header+rules)", C["fusion"])]
fig, ax = plt.subplots(1, 2, figsize=(9.5, 3.4), sharey=True)
for a_, task, base in ((ax[0], "type", pd.Series(yt).value_counts(normalize=True).iloc[0]), (ax[1], "audience", pd.Series(ya).value_counts(normalize=True).iloc[0])):
    vals = [bj[task][k]["acc"] for k, _, _ in names] + [(T_lab == yt).mean() if task == "type" else (A_lab == ya).mean()]
    labs = [l for _, l, _ in names] + ["Cascade (rules→model)"]
    cols = [c for _, _, c in names] + [C["casc"]]
    b = a_.bar(range(len(vals)), vals, color=cols)
    a_.axhline(base, color="k", ls="--", lw=0.8); a_.text(len(vals) - 0.5, base + 0.01, f"majority class {base:.0%}", ha="right", fontsize=7.5)
    for i, v in enumerate(vals):
        a_.text(i, v + 0.01, f"{v:.0%}", ha="center", fontsize=8)
    a_.set_xticks(range(len(vals))); a_.set_xticklabels(labs, rotation=35, ha="right", fontsize=8)
    a_.set_title(f"Page {task}: accuracy on a site never seen in training", fontsize=9, loc="left")
ax[0].set_ylabel("Leave-one-site-out accuracy"); ax[0].set_ylim(0, 0.85)
plt.tight_layout(); plt.savefig("figures/01_approach_comparison.png"); plt.close()

# per-site
ps = pd.DataFrame(dict(site=gold.site.str.replace("www.", ""), Type=(T_lab == yt), Audience=(A_lab == ya))).groupby("site").mean().sort_values("Type")
ps.plot.barh(figsize=(7, 3.8), color=[C["fusion"], C["casc"]]); plt.xlabel("Cascade accuracy, site held out"); plt.xlim(0, 1)
plt.title("Accuracy varies strongly by unseen site", loc="left", fontsize=9); plt.tight_layout(); plt.savefig("figures/02_per_site.png"); plt.close()

# reliability + coverage
fig, ax = plt.subplots(1, 2, figsize=(9, 3.5))
for cc, lab, y, nm, col in ((Tc, T_lab, yt, "type", C["fusion"]), (Ac, A_lab, ya, "audience", C["casc"])):
    r = reliability(cc, lab == y, 8); ax[0].plot(r.mean_conf, r.acc, "o-", color=col, label=f"{nm} (ECE {ece(cc, lab==y):.2f})")
    cv = coverage_curve(cc, lab == y); ax[1].plot(cv.coverage, cv.accuracy, color=col, label=nm)
ax[0].plot([0, 1], [0, 1], "k--", lw=0.8); ax[0].set_xlabel("Calibrated confidence"); ax[0].set_ylabel("Actual accuracy"); ax[0].legend(); ax[0].set_title("Calibration (LOSO)", loc="left", fontsize=9)
ax[1].set_xlabel("Share of pages auto-accepted"); ax[1].set_ylabel("Accuracy of accepted pages"); ax[1].legend(); ax[1].set_title("Coverage vs accuracy as the gate tightens", loc="left", fontsize=9)
plt.tight_layout(); plt.savefig("figures/03_calibration_coverage.png"); plt.close()

# confusion (type)
labs_present = [l for l in TYPES if (yt == l).any()]
cm = confusion(yt, T_lab, labs_present); cmn = cm.div(cm.sum(1).clip(lower=1), axis=0)
fig, ax = plt.subplots(figsize=(8.2, 7)); im = ax.imshow(cmn.values, cmap="Greens", vmin=0, vmax=1)
ax.set_xticks(range(len(labs_present))); ax.set_xticklabels(labs_present, rotation=60, ha="right", fontsize=7)
ax.set_yticks(range(len(labs_present))); ax.set_yticklabels([f"{l} ({int(cm.loc[l].sum())})" for l in labs_present], fontsize=7)
ax.set_xlabel("Predicted"); ax.set_ylabel("Gold"); ax.set_title("Page type: row-normalised confusion (cascade, leave-one-site-out)", loc="left", fontsize=9)
plt.colorbar(im, shrink=0.6); plt.tight_layout(); plt.savefig("figures/04_type_confusion.png"); plt.close()
cm.to_csv("results/type_confusion.csv")

# learning curve
try:
    fig, ax = plt.subplots(1, 2, figsize=(9, 3.3))
    for a_, task in zip(ax, ("type", "audience")):
        lc = json.load(open(f"results/learning_curve_{task}.json", encoding="utf-8"))
        ks = sorted(int(k) for k in lc["curve"]); m = [lc["curve"][str(k)][0] for k in ks]; sd = [lc["curve"][str(k)][1] for k in ks]
        a_.errorbar(ks, m, yerr=sd, marker="o", color=C["fusion"], capsize=3, label="held-out site (cold)")
        a_.axhline(lc["random_cv"], color=C["casc"], ls="--", label=f"random split, sites mixed ({lc['random_cv']:.0%})")
        a_.set_xlabel("Number of training sites"); a_.set_ylabel("Accuracy"); a_.set_title(f"Learning curve - {task}", loc="left", fontsize=9); a_.legend(fontsize=7.5)
    plt.tight_layout(); plt.savefig("figures/05_learning_curve.png"); plt.close()
except FileNotFoundError:
    print("learning-curve results not ready; figure 05 skipped")
print("figures written")
