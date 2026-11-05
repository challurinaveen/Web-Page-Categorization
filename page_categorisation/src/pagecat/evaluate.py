"""Benchmark metrics: accuracy / macro-F1 / per-class PRF / confusion / kappa / calibration / gating."""
import numpy as np
import pandas as pd
from sklearn.metrics import (accuracy_score, cohen_kappa_score, confusion_matrix,
                             precision_recall_fscore_support)


def summarize(y_true, y_pred, weights=None, labels=None) -> dict:
    y_true, y_pred = np.asarray(y_true), np.asarray(y_pred)
    labels = labels or sorted(set(y_true) | set(y_pred))
    p, r, f, s = precision_recall_fscore_support(y_true, y_pred, labels=labels, zero_division=0)
    present = s > 0
    out = dict(n=len(y_true), acc=accuracy_score(y_true, y_pred),
               macro_f1=float(np.mean(f[present])) if present.any() else 0.0,
               kappa_vs_truth=cohen_kappa_score(y_true, y_pred))
    if weights is not None:     # population-level estimate from the stratified sample
        w = np.asarray(weights, float)
        out["acc_pop"] = float(np.sum(w * (y_true == y_pred)) / w.sum())
    return out


def per_class(y_true, y_pred, labels) -> pd.DataFrame:
    p, r, f, s = precision_recall_fscore_support(y_true, y_pred, labels=labels, zero_division=0)
    return pd.DataFrame(dict(label=labels, precision=p, recall=r, f1=f, support=s)).set_index("label")


def confusion(y_true, y_pred, labels) -> pd.DataFrame:
    return pd.DataFrame(confusion_matrix(y_true, y_pred, labels=labels), index=labels, columns=labels)


def ece(conf, correct, bins=10) -> float:
    """Expected calibration error: weighted gap between stated confidence and actual accuracy."""
    conf, correct = np.asarray(conf, float), np.asarray(correct, float)
    edges = np.linspace(0, 1, bins + 1)
    tot = 0.0
    for lo, hi in zip(edges[:-1], edges[1:]):
        m = (conf > lo) & (conf <= hi) if lo > 0 else (conf >= lo) & (conf <= hi)
        if m.any():
            tot += m.mean() * abs(conf[m].mean() - correct[m].mean())
    return float(tot)


def reliability(conf, correct, bins=10) -> pd.DataFrame:
    conf, correct = np.asarray(conf, float), np.asarray(correct, float)
    edges = np.linspace(0, 1, bins + 1)
    rows = []
    for lo, hi in zip(edges[:-1], edges[1:]):
        m = (conf > lo) & (conf <= hi) if lo > 0 else (conf >= lo) & (conf <= hi)
        if m.any():
            rows.append(dict(lo=lo, hi=hi, n=int(m.sum()), mean_conf=conf[m].mean(), acc=correct[m].mean()))
    return pd.DataFrame(rows)


def coverage_curve(conf, correct, grid=None) -> pd.DataFrame:
    """Accuracy of the auto-accepted subset as the confidence threshold rises."""
    conf, correct = np.asarray(conf, float), np.asarray(correct, float)
    grid = np.linspace(0, 0.99, 34) if grid is None else grid
    rows = []
    for t in grid:
        m = conf >= t
        rows.append(dict(threshold=t, coverage=m.mean(), accuracy=correct[m].mean() if m.any() else np.nan))
    return pd.DataFrame(rows)


def threshold_for_accuracy(conf, correct, target=0.95):
    """Lowest threshold whose accepted set reaches `target` accuracy (None if unreachable)."""
    c = coverage_curve(conf, correct, np.linspace(0, 0.995, 200))
    ok = c[(c.accuracy >= target) & (c.coverage > 0.02)]
    return None if ok.empty else float(ok.threshold.iloc[0])


def agreement(a, b, labels) -> dict:
    a, b = np.asarray(a), np.asarray(b)
    return dict(n=len(a), raw_agreement=float((a == b).mean()),
                kappa=float(cohen_kappa_score(a, b, labels=labels)))
