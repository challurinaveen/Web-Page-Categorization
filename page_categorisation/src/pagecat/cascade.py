"""The tiered cascade (deck slide 7): preprocess -> cheap match -> confidence gate -> LLM fallback.

Tier 1  rules          ~0.1 ms/page, no model load. Accepts when confidence >= tau_rules.
Tier 2  fusion model   needs the e5 embedding (~30 pages/s on 32 CPU cores) + logistic regression.
Gate    joint confidence = min(type_conf, audience_conf), calibrated by temperature scaling.
        >= publish  -> status "auto"        (label ships with its evidence)
        >= review   -> status "sampled"     (ships, but routed to periodic human audit)
        <  review   -> status "llm_review"  (escalate to tier 3)

Tier 3  LLM            llm_tier.run(); its answer replaces the cheap one and apply_llm() re-gates the page
        on the model's own confidence: 3 -> "auto", 2 -> "sampled", 1 -> "human_review". A failed request
        keeps the cheap label and is marked "llm_error". Off unless classify_scan.py is given --llm.
"""
import json
import pickle
from dataclasses import asdict, dataclass, field

import numpy as np
import pandas as pd

from . import models as M
from . import rules
from .llm_tier import CONF_ACC
from .taxonomy import AUD, TYPES, VERSION

LLM_STATUS = {3: "auto", 2: "sampled", 1: "human_review", 0: "llm_error"}


@dataclass
class Prediction:
    url: str
    page_type: str
    type_conf: float
    audience: str
    audience_conf: float
    declared_audience: str
    tier: str                     # "rules" | "model" | "llm"
    status: str                   # auto | sampled | llm_review | human_review | llm_error
    evidence: list = field(default_factory=list)
    taxonomy: str = VERSION
    llm_conf: int = 0                     # the LLM's own 1-3 (0 = tier 3 not run, or its request failed)
    llm_evidence: str = ""
    cascade_type: str = ""                # what tiers 1-2 said, kept beside the LLM label:
    cascade_audience: str = ""            # the two agreeing is a free second signal (the README, "The LLM tier, measured")
    agree_type: bool | None = None
    agree_audience: bool | None = None

    def to_json(self):
        return json.dumps(asdict(self), ensure_ascii=False)


def apply_llm(preds, idx, answers):
    """Promote tier-3 answers onto `preds` in place; `answers[k]` (from llm_tier.run) belongs to preds[idx[k]].

    The LLM label wins - it is worth 80.9%/90.4% against 44%/68% for the cheap tiers on the gold set - and
    the cheap label is kept in cascade_type/cascade_audience rather than thrown away, because the two tiers
    agreeing on a type is itself worth 88.3% accuracy (the README, "The LLM tier, measured"). type_conf/audience_conf stay
    comparable across tiers by carrying the measured accuracy of the confidence the model reported.
    """
    for i, a in zip(idx, answers):
        p = preds[i]
        p.cascade_type, p.cascade_audience = p.page_type, p.audience
        p.llm_conf = int(a.get("confidence") or 0)
        p.llm_evidence = a.get("evidence") or a.get("error", "")
        if a.get("type") is None:                      # request failed: keep the cheap tier's answer
            p.status = LLM_STATUS[0]
            continue
        p.page_type, p.audience = a["type"], a["audience"]
        p.type_conf, p.audience_conf = CONF_ACC[p.llm_conf]
        p.agree_type, p.agree_audience = p.page_type == p.cascade_type, p.audience == p.cascade_audience
        p.tier, p.status = "llm", LLM_STATUS[p.llm_conf]
    return preds


def platt(conf, ab):
    """Calibrated P(correct) = sigmoid(a*logit(conf)+b); (a,b) fitted on leave-one-site-out predictions."""
    c = np.clip(np.asarray(conf, float), 1e-4, 1 - 1e-4)
    return 1 / (1 + np.exp(-(ab[0] * np.log(c / (1 - c)) + ab[1])))


class Cascade:
    def __init__(self, type_model, aud_model, encoder, cfg):
        self.mt, self.ma, self.encoder, self.cfg = type_model, aud_model, encoder, cfg

    @classmethod
    def load(cls, path="models/cascade.pkl", encoder_name="intfloat/multilingual-e5-small"):
        blob = pickle.load(open(path, "rb"))
        from sentence_transformers import SentenceTransformer
        enc = SentenceTransformer(encoder_name, device="cpu")
        enc.max_seq_length = 256
        return cls(blob["type_model"], blob["aud_model"], enc, blob["cfg"])

    def _embed(self, df):
        c = self.encoder.encode(["query: " + t for t in df.embed_text], batch_size=64, normalize_embeddings=True,
                                show_progress_bar=False)
        self.encoder.max_seq_length = 128
        h = self.encoder.encode(["query: " + t[:400] for t in df["head"]], batch_size=64, normalize_embeddings=True,
                                show_progress_bar=False)
        self.encoder.max_seq_length = 256
        return np.hstack([c, h])

    def predict(self, df: pd.DataFrame) -> list[Prediction]:
        """df = rows shaped like data/features.parquet (see scan.featurise)."""
        cfg, n = self.cfg, len(df)
        t_lab, t_conf, a_lab, a_conf, tier, ev = [None] * n, np.zeros(n), [None] * n, np.zeros(n), ["rules"] * n, [[] for _ in range(n)]
        rows = list(df.itertuples())
        feats = [M.row_to_features(r) for r in rows]
        rt = [rules.classify_type(f) for f in feats]
        ra = [rules.classify_audience(f) for f in feats]
        need = []
        for i in range(n):
            ok_t, ok_a = rt[i].label and rt[i].confidence >= cfg["tau_rules_type"], ra[i].label and ra[i].confidence >= cfg["tau_rules_aud"]
            if ok_t and ok_a:
                t_lab[i], a_lab[i] = rt[i].label, ra[i].label
                t_conf[i] = platt(rt[i].confidence, cfg["cal"]["rules_type"])
                a_conf[i] = platt(ra[i].confidence, cfg["cal"]["rules_aud"])
                ev[i] = rt[i].evidence[:3] + ra[i].evidence[:3]
            else:
                need.append(i)
        if need:                                         # tier 2 only for pages the rules were unsure about
            sub = df.iloc[need]
            X = self._embed(sub)
            for mdl, lab, conf, cal in ((self.mt, t_lab, t_conf, cfg["cal"]["model_type"]),
                                        (self.ma, a_lab, a_conf, cfg["cal"]["model_aud"])):
                cl, P = mdl.predict_proba(sub, X)
                for j, i in enumerate(need):
                    lab[i], conf[i] = cl[P[j].argmax()], float(platt(P[j].max(), cal))
            for i in need:
                tier[i] = "model"
                ev[i] = (rt[i].evidence[:2] + ra[i].evidence[:2]) or ["no rule fired; embedding + rule-feature model"]
        out = []
        for i, f in enumerate(feats):
            joint = min(t_conf[i], a_conf[i])
            status = "auto" if joint >= cfg["publish"] else "sampled" if joint >= cfg["review"] else "llm_review"
            out.append(Prediction(url=f.url, page_type=t_lab[i], type_conf=round(float(t_conf[i]), 3), audience=a_lab[i],
                                  audience_conf=round(float(a_conf[i]), 3), declared_audience=rules.declared_audience(f),
                                  tier=tier[i], status=status, evidence=ev[i]))
        return out
