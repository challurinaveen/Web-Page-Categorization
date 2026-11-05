"""Turn one scan record into the features every classifier tier consumes.

Input (dict-like): url, mime, pdf_pages, depth, parent, lines (raw text lines),
                   body_lines (boilerplate-stripped lines).
Only the URL and the page text are used - nothing else about the page is assumed.
"""
import json
import re
from dataclasses import dataclass, field
from urllib.parse import parse_qs, unquote, urlparse

try:
    from langdetect import DetectorFactory, detect
    DetectorFactory.seed = 0
except ImportError:  # language falls back to script heuristics
    detect = None

_SPLIT = re.compile(r"[^0-9A-Za-zÀ-ÿ぀-ヿ一-鿿]+")
_NOISE_SEG = re.compile(r"^(content|dam|intelligentcontent|astrazeneca-champion|global|home|en|"
                        r"index|html?|aspx?|php|jcr_content|www|az|us|uk|es|pt|be|se|no|dk|fi|jp|nl|fr|sv|"
                        r"siteassets|globalassets|media|files?|pdfs?|\d+)$", re.I)
_GENERIC_TITLE = re.compile(r"^(page: ?\d+$|skip to|ir al|home|inicio|menu|search|buscar|close|cerrar|logo|"
                            r"accept|aceptar|opening document|welcome to)", re.I)
HIRAGANA_KATAKANA = re.compile(r"[぀-ヿ]")
CJK = re.compile(r"[一-鿿]")


_HEXISH = re.compile(r"^(?=.*\d)[0-9a-f]{3,}$|^[0-9a-z]{20,}$|^[a-z]\d{3,}$", re.I)   # guids, hashes, ids


def url_tokens(url: str) -> list[str]:
    """Path + informative query values as lower-case tokens, noise segments removed."""
    u = urlparse(url)
    toks = []
    for seg in u.path.split("/"):
        for t in _SPLIT.split(unquote(seg).lower()):
            if t and not _NOISE_SEG.match(t) and not _HEXISH.match(t):
                toks.append(t)
    q = parse_qs(u.query)
    for k in ("pdfTitle", "title", "q", "query", "requesturl"):
        for v in q.get(k, []):
            toks += [t for t in _SPLIT.split(unquote(v).lower()) if t and not _NOISE_SEG.match(t) and not _HEXISH.match(t)][:40]
    return toks


def url_shape(url: str) -> dict:
    u = urlparse(url)
    segs = [s for s in u.path.split("/") if s]
    return dict(n_seg=len(segs), has_query=bool(u.query), is_root=(len(segs) == 0),
                ext=(segs[-1].rsplit(".", 1)[-1].lower() if segs and "." in segs[-1] else ""),
                subdomain=u.netloc.split(".")[0] if u.netloc.count(".") >= 2 else "")


def pick_title(body_lines: list[str], raw_lines: list[str], url: str) -> str:
    q = parse_qs(urlparse(url).query)
    if q.get("pdfTitle"):
        return unquote(q["pdfTitle"][0])[:200]
    for src in (body_lines, raw_lines):
        for l in src[:12]:
            l = l.strip()
            if 4 <= len(l) <= 160 and not _GENERIC_TITLE.match(l):
                return l
    return ""


def detect_lang(text: str) -> str:
    s = text[:600]
    if HIRAGANA_KATAKANA.search(s):
        return "ja"
    if detect is None or len(s.strip()) < 25:
        return "und"
    try:
        return detect(s)
    except Exception:
        return "und"


@dataclass
class PageFeatures:
    url: str
    mime: str = "text/html"
    is_pdf: bool = False
    pdf_pages: int = 0
    depth: int = 0
    title: str = ""
    url_toks: list = field(default_factory=list)
    shape: dict = field(default_factory=dict)
    body: str = ""        # boilerplate-stripped text (content)
    head: str = ""        # raw first lines (gating / declared audience / site context)
    n_body: int = 0
    lang: str = "und"
    host: str = ""
    third_party: bool = False    # page sits on a domain other than the scanned site's
    host_decl_hcp: float = 0.0   # share of this host's pages that declare "for HCPs only" (site-level context)
    host_decl_pat: float = 0.0

    def embed_text(self, max_body: int = 700) -> str:
        """Compact view used for embeddings / TF-IDF: what a person would skim."""
        return f"{self.title} | {' '.join(self.url_toks[:25])} | {self.body[:max_body]}".replace("\n", " ")


def row_to_features(r) -> PageFeatures:
    """One row of data/features.parquet (or any object with the same attributes) -> PageFeatures.

    Lives here rather than in models.py so that scan.py and the tier-3-only paths can use it
    without importing scikit-learn; models.py re-exports it, so `M.row_to_features` still works.
    """
    return PageFeatures(url=r.url, is_pdf=bool(r.is_pdf), pdf_pages=int(r.pdf_pages or 0), depth=int(r.depth or 0),
                        title=r.title, url_toks=r.url_toks.split(), shape=url_shape(r.url), body=r.body,
                        head=r.head, n_body=int(r.n_body), lang=r.lang, host=r.host,
                        third_party=bool(getattr(r, "third_party", False)),
                        host_decl_hcp=float(getattr(r, "host_decl_hcp", 0.0)), host_decl_pat=float(getattr(r, "host_decl_pat", 0.0)))


def build(rec) -> PageFeatures:
    g = rec.get if isinstance(rec, dict) else lambda k, d=None: getattr(rec, k, d)
    raw = g("lines", "[]")
    raw = json.loads(raw) if isinstance(raw, str) else list(raw)
    body = g("body_lines", None)
    body = json.loads(body) if isinstance(body, str) else (list(body) if body is not None else raw)
    url = g("url")
    text = "\n".join(body)
    head = " | ".join(l.strip() for l in raw[:40] if l.strip())[:1500]
    f = PageFeatures(url=url, mime=g("mime", "text/html"), is_pdf=bool(g("is_pdf", False)),
                     pdf_pages=int(g("pdf_pages", 0) or 0), depth=int(g("depth", 0) or 0),
                     title=pick_title(body, raw, url), url_toks=url_tokens(url), shape=url_shape(url),
                     body=text[:6000], head=head, n_body=len(text), host=urlparse(url).netloc.lower())
    f.lang = detect_lang(text if len(text) > 80 else head)
    return f
