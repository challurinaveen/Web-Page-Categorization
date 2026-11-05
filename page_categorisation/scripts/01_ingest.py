"""Flatten the 10 site-scan JSON files into one page-level table.

Output: data/records.parquet  (one row per scan record, units + non-pages flagged)

Key decisions
- Classification unit = HTTP-200 HTML page or PDF. Images/icons/viewer shells are
  flagged `unit=False` and never classified (they carry OCR noise, not page text).
- `third_party` = host outside the AstraZeneca family of the scanned site. The scans
  follow outbound links, so ~15-30% of HTML "pages" belong to PubMed, NICE, CMS etc.
- Boilerplate (nav, cookie banner, footer) is removed per host by document frequency
  of exact lines: a line seen on >= 30% of a host's own pages is boilerplate.
"""
import glob
import json
import re
import sys
from collections import Counter, defaultdict
from urllib.parse import urlparse

import pandas as pd

ROOT = sys.argv[1] if len(sys.argv) > 1 else "../content"
OUT = sys.argv[2] if len(sys.argv) > 2 else "data/records.parquet"

AZ_FAMILY = re.compile(r"(astrazeneca|azone|az-oncology|azmedical|short\.az|az\.com)", re.I)
SHELL_HOSTS = ("documentservices.adobe.com", "google.com", "gstatic.com", "recaptcha.net",
               "youtube-nocookie.com", "youtube.com", "vimeo.com", "doubleclick.net")
BP_MIN_PAGES = 20      # need this many pages on a host before frequency stats are trusted
BP_FRACTION = 0.30     # line seen on >= this share of host pages => boilerplate


GENERIC_BP = re.compile(
    r"^(page: ?\d+|skip to .*|skip directly.*|saltar .*|ir al contenido.*|ir a la navegaci.*|vai al contenuto|aller au contenu|"
    r"till huvudinneh.*|gå till innehåll.*|スキップ.*|.*(cookie|kakor|cookies|consent|samtycke|privacy choices|your privacy, your choice).*|"
    r"accept all|reject all|aceptar todo|rechazar todo|close|cerrar|search|buscar|menu|english|español|logo|.{0,2})$", re.I)


def reg_domain(host: str) -> str:
    parts = host.lower().split(".")
    if len(parts) >= 3 and parts[-2] in ("co", "com", "org", "ac", "gov") and len(parts[-1]) == 2:
        return ".".join(parts[-3:])
    return ".".join(parts[-2:])


def parent_url(shortest: str, url: str) -> str:
    """Penultimate hop of the discovery path = the page that linked to this one."""
    hops = [h.split(" [")[0].lstrip("|- ").strip() for h in shortest.split("\n") if h.strip()]
    if len(hops) >= 2:
        return hops[-2]
    return ""


def main():
    rows = []
    for f in sorted(glob.glob(f"{ROOT}/*/*/filetext.json")):
        site = f.replace("\\", "/").split("/")[-3]      # glob returns backslashes on Windows
        site_reg = reg_domain(site)
        for r in json.load(open(f, encoding="utf-8")):
            url = r["File URL"]
            u = urlparse(url)
            host = u.netloc.lower()
            mime = r["File Mimetype"]
            is_html, is_pdf = "html" in mime, mime == "application/pdf"
            ok = r["File Status"] == "200"
            text = r["File text"] or ""
            shell = any(host.endswith(h) for h in SHELL_HOSTS) or (is_html and len(text.strip()) < 60)
            rows.append(dict(
                site=site, url=url, host=host, path=u.path, query=u.query,
                reg_domain=reg_domain(host), mime=mime, status=r["File Status"],
                pdf_pages=r["PDF Pages"], is_pdf=is_pdf,
                third_party=not (AZ_FAMILY.search(host) is not None or reg_domain(host) == site_reg),
                unit=bool(ok and (is_html or is_pdf) and not shell),
                depth=r["File URL Shortestpath"].count("\n"),
                parent=parent_url(r["File URL Shortestpath"], url),
                n_chars=len(text), lines=r["File text lines"] if (is_html or is_pdf) else [],
            ))
    df = pd.DataFrame(rows)

    # ---- per-host boilerplate by exact-line document frequency (own-domain HTML only)
    bp = {}
    own_html = df[df.unit & ~df.is_pdf & ~df.third_party]
    for host, g in own_html.groupby("host"):
        if len(g) < BP_MIN_PAGES:
            continue
        c = Counter()
        for lines in g.lines:
            c.update({l.strip() for l in lines if l.strip()})
        bp[host] = {l for l, n in c.items() if n / len(g) >= BP_FRACTION}
    print("hosts with boilerplate model:", {h: len(s) for h, s in bp.items()})

    # third-party / small hosts: model boilerplate per registrable domain instead (e.g. all nature.com pages)
    bp_dom = {}
    ext_html = df[df.unit & ~df.is_pdf & ~df.host.isin(bp)]
    for dom, g in ext_html.groupby("reg_domain"):
        if len(g) < 6:
            continue
        c = Counter()
        for lines in g.lines:
            c.update({l.strip() for l in lines if l.strip()})
        bp_dom[dom] = {l for l, n in c.items() if n / len(g) >= 0.5}
    print("domains with boilerplate model:", len(bp_dom))

    def strip(row):
        b = bp.get(row.host) or bp_dom.get(row.reg_domain) or set()
        return [l.strip() for l in row.lines
                if l.strip() and l.strip() not in b and not GENERIC_BP.match(l.strip())]

    df["body_lines"] = [strip(r) if r.unit else [] for r in df.itertuples()]
    df["clean_text"] = df.body_lines.map(lambda ls: "\n".join(ls))
    df["raw_head"] = df.lines.map(lambda ls: " | ".join(l.strip() for l in ls[:40] if l.strip())[:1500])
    df["n_clean"] = df.clean_text.str.len()
    df["lines"] = df.lines.map(lambda ls: json.dumps(ls[:200], ensure_ascii=False))
    df["body_lines"] = df.body_lines.map(lambda ls: json.dumps(ls[:400], ensure_ascii=False))
    df["clean_text"] = df.clean_text.str.slice(0, 20000)
    df.to_parquet(OUT)
    u = df[df.unit]
    print(df.groupby("site").agg(records=("url", "size"), units=("unit", "sum"),
                                 third_party=("third_party", "sum")))
    print("units:", len(u), "| pdf:", int(u.is_pdf.sum()), "| third-party units:", int(u.third_party.sum()))
    print("median clean/raw ratio:", (u.n_clean / u.n_chars.clip(lower=1)).median())


if __name__ == "__main__":
    main()
