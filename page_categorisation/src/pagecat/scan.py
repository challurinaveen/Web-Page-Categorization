"""Raw scan file (filetext.json, DCR standard format) -> classifiable feature rows.

Mirrors scripts/01_ingest.py + 02_features.py but is self-contained so a *new* site can be scored
without any training-time artefacts: boilerplate and the host's audience declaration are learned
from the scan itself (unsupervised, no labels).
"""
import json
import re
from collections import Counter
from urllib.parse import urlparse

import pandas as pd

from . import rules
from .preprocess import build, row_to_features

SHELL_HOSTS = ("documentservices.adobe.com", "google.com", "gstatic.com", "recaptcha.net",
               "youtube-nocookie.com", "youtube.com", "vimeo.com", "doubleclick.net")
GENERIC_BP = re.compile(
    r"^(page: ?\d+|skip to .*|skip directly.*|saltar .*|ir al contenido.*|ir a la navegaci.*|vai al contenuto|aller au contenu|"
    r"till huvudinneh.*|gå till innehåll.*|スキップ.*|.*(cookie|kakor|cookies|consent|samtycke|privacy choices|your privacy, your choice).*|"
    r"accept all|reject all|aceptar todo|rechazar todo|close|cerrar|search|buscar|menu|english|español|logo|.{0,2})$", re.I)


def _reg(host):
    p = host.lower().split(".")
    return ".".join(p[-3:]) if len(p) >= 3 and p[-2] in ("co", "com", "org", "ac", "gov") and len(p[-1]) == 2 else ".".join(p[-2:])


def featurise(records: list[dict], bp_min_pages=20, bp_fraction=0.30) -> pd.DataFrame:
    rows = []
    site_reg = _reg(urlparse(records[0]["Report URL"]).netloc) if records else ""
    for r in records:
        u = urlparse(r["File URL"]); host = u.netloc.lower(); mime = r["File Mimetype"]
        html, pdf = "html" in mime, mime == "application/pdf"
        text = r.get("File text") or ""
        shell = any(host.endswith(h) for h in SHELL_HOSTS) or (html and len(text.strip()) < 60)
        if not (r["File Status"] == "200" and (html or pdf) and not shell):
            continue
        rows.append(dict(url=r["File URL"], host=host, reg_domain=_reg(host), mime=mime, is_pdf=pdf,
                         pdf_pages=r.get("PDF Pages", 0), depth=r["File URL Shortestpath"].count("\n"),
                         third_party=not (re.search(r"astrazeneca|azone|az-oncology|azmedical", host) or _reg(host) == site_reg),
                         lines=r.get("File text lines") or [], parent=""))
    if not rows:
        # Nothing classifiable: every record was an error, an image or an empty shell. An empty
        # frame has no columns, so the boilerplate pass below would raise AttributeError on
        # df.is_pdf; hand back the right shape instead and let the caller report "0 of N".
        return pd.DataFrame(columns=[
            "url", "host", "reg_domain", "third_party", "is_pdf", "pdf_pages", "depth", "parent",
            "title", "url_toks", "lang", "n_body", "body", "head", "embed_text",
            "host_decl_hcp", "host_decl_pat"])
    df = pd.DataFrame(rows)
    # boilerplate: per host for big own hosts, per registrable domain for the rest
    bp, bd = {}, {}
    for host, g in df[~df.is_pdf & ~df.third_party].groupby("host"):
        if len(g) >= bp_min_pages:
            c = Counter(); [c.update({l.strip() for l in ls if l.strip()}) for ls in g.lines]
            bp[host] = {l for l, n in c.items() if n / len(g) >= bp_fraction}
    for dom, g in df[~df.is_pdf & ~df.host.isin(bp)].groupby("reg_domain"):
        if len(g) >= 6:
            c = Counter(); [c.update({l.strip() for l in ls if l.strip()}) for ls in g.lines]
            bd[dom] = {l for l, n in c.items() if n / len(g) >= 0.5}
    out = []
    for r in df.itertuples():
        b = bp.get(r.host) or bd.get(r.reg_domain) or set()
        body = [l.strip() for l in r.lines if l.strip() and l.strip() not in b and not GENERIC_BP.match(l.strip())]
        f = build(dict(url=r.url, mime=r.mime, is_pdf=r.is_pdf, pdf_pages=r.pdf_pages, depth=r.depth, lines=r.lines, body_lines=body))
        out.append(dict(url=r.url, host=r.host, reg_domain=r.reg_domain, third_party=r.third_party, is_pdf=r.is_pdf,
                        pdf_pages=r.pdf_pages, depth=r.depth, parent=r.parent, title=f.title, url_toks=" ".join(f.url_toks),
                        lang=f.lang, n_body=f.n_body, body=f.body, head=f.head, embed_text=f.embed_text()))
    feats = pd.DataFrame(out)
    dec = [rules.declared_audience(row_to_features(r)) for r in feats.itertuples()]
    feats["_dh"], feats["_dp"] = [d == "Healthcare Professional" for d in dec], [d == "Patient / Caregiver" for d in dec]
    g = feats.groupby("host"); n = g.url.transform("size")
    feats["host_decl_hcp"] = (g._dh.transform("mean") * (n >= 5)).astype(float)
    feats["host_decl_pat"] = (g._dp.transform("mean") * (n >= 5)).astype(float)
    return feats.drop(columns=["_dh", "_dp"])
