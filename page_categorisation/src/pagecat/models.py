"""Tier 2 classifiers. All share one interface:  fit(df, E, y)  /  predict_proba(df, E) -> (classes, P).

df = rows of data/features.parquet, E = matching rows of the e5 embedding matrix.
"""
import numpy as np
import pandas as pd
import scipy.sparse as sp
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

from . import rules
from .preprocess import PageFeatures, row_to_features, url_shape  # noqa: F401  (re-exported)
from .taxonomy import AUD, AUDIENCES, PAGE_TYPES, TYPES


def rule_matrix(df: pd.DataFrame) -> np.ndarray:
    """Rule evidence as features: per-label summed scores (type, audience) + declared-audience flags."""
    out = np.zeros((len(df), len(TYPES) + len(AUD) + 4), dtype="float32")
    for i, r in enumerate(df.itertuples()):
        f = row_to_features(r)
        ts, _ = rules._score(f, rules.TYPE_RULES)
        ts = rules.apply_type_postrules(f, ts)
        as_, _ = rules._score(f, rules.AUD_RULES)
        for k, v in ts.items():
            out[i, TYPES.index(k)] = v
        for k, v in as_.items():
            out[i, len(TYPES) + AUD.index(k)] = v
        d = rules.declared_audience(f)
        out[i, -4] = d == "Healthcare Professional"
        out[i, -3] = d == "Patient / Caregiver"
        out[i, -2] = f.host_decl_hcp
        out[i, -1] = f.host_decl_pat
    return out


LANGS = ["en", "es", "pt", "fr", "nl", "sv", "no", "da", "ja"]


def meta_matrix(df: pd.DataFrame) -> np.ndarray:
    m = np.column_stack([
        df.is_pdf.astype(float), df.third_party.astype(float), np.log1p(df.pdf_pages.fillna(0)),
        np.log1p(df.n_body), np.minimum(df.depth, 8) / 8.0,
        df.url.map(lambda u: u.count("/") <= 3).astype(float), df.url.str.contains(r"\?").astype(float),
    ])
    L = np.column_stack([(df.lang == l).astype(float) for l in LANGS])
    return np.hstack([m, L]).astype("float32")


def text_blob(df: pd.DataFrame, n_body=1500) -> pd.Series:
    return (df.title + " || " + df.url_toks + " || " + df["head"].str.slice(0, 250) + " || " + df.body.str.slice(0, n_body))


class TfidfLR:
    """Language-agnostic char n-grams + URL-token words; the 'classical ML' baseline in the deck."""
    name = "tfidf_lr"

    def __init__(self, C=10.0):
        self.C = C

    def _mat(self, df, fit=False):
        t, u = text_blob(df), df.url_toks + " " + df.title
        if fit:
            self.vc = TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 4), min_df=3, sublinear_tf=True, max_features=150000)
            self.vw = TfidfVectorizer(token_pattern=r"[^\s]{2,}", min_df=2, sublinear_tf=True, ngram_range=(1, 2))
            return sp.hstack([self.vc.fit_transform(t), self.vw.fit_transform(u)]).tocsr()
        return sp.hstack([self.vc.transform(t), self.vw.transform(u)]).tocsr()

    def fit(self, df, E, y):
        self.clf = LogisticRegression(C=self.C, max_iter=2000, class_weight="balanced")
        self.clf.fit(self._mat(df, True), y)
        return self

    def predict_proba(self, df, E):
        return self.clf.classes_, self.clf.predict_proba(self._mat(df))


class EmbLR:
    name = "emb_lr"

    def __init__(self, C=3.0):
        self.C = C

    def fit(self, df, E, y):
        self.clf = LogisticRegression(C=self.C, max_iter=3000, class_weight="balanced").fit(E, y)
        return self

    def predict_proba(self, df, E):
        return self.clf.classes_, self.clf.predict_proba(E)


class FusionLR:
    """Embedding + rule evidence + page meta, one logistic regression: lets the learner decide how far to
    trust the hand-written rules instead of fixing the trade-off by hand."""
    name = "fusion_lr"

    def __init__(self, C=1.0, rule_scale=1.0):
        self.C, self.rule_scale = C, rule_scale

    def _X(self, df, E, fit=False):
        R, M = rule_matrix(df), meta_matrix(df)
        Z = np.hstack([R, M])
        if fit:
            self.sc = StandardScaler().fit(Z)
        return np.hstack([E, self.rule_scale * self.sc.transform(Z) * 0.25])

    def fit(self, df, E, y):
        self.clf = LogisticRegression(C=self.C, max_iter=4000, class_weight="balanced").fit(self._X(df, E, True), y)
        return self

    def predict_proba(self, df, E):
        return self.clf.classes_, self.clf.predict_proba(self._X(df, E))


class ZeroShot:
    """No labels needed: cosine similarity of the page embedding to each label's description embedding."""
    name = "zeroshot_emb"

    def __init__(self, descriptions: dict, encoder, temp=0.03):
        self.labels = list(descriptions)
        self.D = encoder(["query: " + f"{k}. {v}" for k, v in descriptions.items()])
        self.temp = temp

    def fit(self, df, E, y):
        return self

    def predict_proba(self, df, E):
        s = E @ self.D.T / self.temp
        s = np.exp(s - s.max(1, keepdims=True))
        return np.array(self.labels), s / s.sum(1, keepdims=True)


class Rules:
    """Tier-1 rules wrapped in the same interface so it can be benchmarked beside the learners."""
    def __init__(self, kind: str):
        self.kind, self.name = kind, f"rules"
        self.labels = TYPES if kind == "type" else AUD
        self.fallback = "Other" if kind == "type" else "Unclear"

    def fit(self, df, E, y):
        return self

    def predict_proba(self, df, E):
        P = np.zeros((len(df), len(self.labels)))
        for i, r in enumerate(df.itertuples()):
            f = row_to_features(r)
            res = rules.classify_type(f) if self.kind == "type" else rules.classify_audience(f)
            lab = res.label or self.fallback
            P[i, self.labels.index(lab)] = max(res.confidence, 0.05)
        # normalise so that rows are proper distributions; confidence kept in max prob via residual mass
        resid = np.clip(1 - P.sum(1), 0, 1)
        P += (resid / len(self.labels))[:, None]
        return np.array(self.labels), P / P.sum(1, keepdims=True)
