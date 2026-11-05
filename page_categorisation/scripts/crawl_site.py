#!/usr/bin/env python
"""Crawl a live website into the DCR scan format, so classify_scan.py can run on a site nobody supplied a scan for.

  python scripts/crawl_site.py https://example.com -o new_site_scan.json --max-pages 200
  python scripts/classify_scan.py new_site_scan.json -o new_site_results.jsonl

Output is a JSON list of records with the same 14 fields as the supplied scans, so `scan.featurise` reads it
unchanged: Report ID/URL, File ref, File storagekey, File URL, File Mimetype, File Status, PDF Pages,
File URL Shortestpath, File text, File text lines, File text sep, File text language, File text translated.
The two language fields are left empty exactly as they are in all 34,319 supplied records - language is
detected downstream from the text itself.

Polite by default and deliberately so: robots.txt is always honoured, one request at a time, 1 s between
requests, 200 pages max unless you raise it. Only use it on sites you are allowed to crawl.
"""
import argparse, hashlib, json, re, sys, time
from collections import deque
from urllib.parse import urldefrag, urljoin, urlparse
from urllib.robotparser import RobotFileParser

import requests
from bs4 import BeautifulSoup

UA = "DCR-page-categorisation-prototype/1.0 (research crawler; +contact your DCR representative)"
SKIP_EXT = re.compile(r"\.(jpg|jpeg|png|gif|svg|webp|ico|css|js|woff2?|ttf|eot|mp4|webm|mp3|zip|gz|xlsx?|docx?|pptx?)$", re.I)
DROP_TAGS = ("script", "style", "noscript", "template", "svg")


def reg_domain(host):
    """example.co.uk -> example.co.uk ; www.a.example.com -> example.com (same rule as scan.py)."""
    p = host.lower().split(".")
    return ".".join(p[-3:]) if len(p) >= 3 and p[-2] in ("co", "com", "org", "ac", "gov") and len(p[-1]) == 2 else ".".join(p[-2:])


def normalise(url):
    u = urlparse(urldefrag(url)[0])
    if u.scheme not in ("http", "https"):
        return None
    return u._replace(scheme=u.scheme.lower(), netloc=u.netloc.lower(), path=u.path or "/").geturl()


def text_lines(html):
    """Every visible line, nav and cookie banner included - featurise strips boilerplate itself, per host."""
    soup = BeautifulSoup(html, "lxml")
    for t in soup(DROP_TAGS):
        t.decompose()
    return [ln.strip() for ln in soup.get_text("\n").splitlines() if ln.strip()]


def pdf_lines(content):
    try:
        import io as _io
        from pypdf import PdfReader
        r = PdfReader(_io.BytesIO(content))
        lines = [ln.strip() for p in r.pages for ln in (p.extract_text() or "").splitlines() if ln.strip()]
        return lines, len(r.pages)
    except Exception as e:
        print("  ! pdf unreadable (%s)" % type(e).__name__, file=sys.stderr)
        return [], 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("url", help="start URL, e.g. https://example.com")
    ap.add_argument("-o", "--out", required=True, help="scan JSON to write")
    ap.add_argument("--max-pages", type=int, default=200, help="stop after this many fetches (default 200)")
    ap.add_argument("--delay", type=float, default=1.0, help="seconds between requests (default 1.0)")
    ap.add_argument("--timeout", type=float, default=20.0)
    ap.add_argument("--same-host", action="store_true", help="stay on the exact host instead of the whole domain")
    ap.add_argument("--no-pdf", action="store_true", help="skip PDFs instead of extracting their text")
    ap.add_argument("--retries", type=int, default=3, help="retries per URL on 429/503 (default 3)")
    ap.add_argument("--max-backoff", type=float, default=60.0, help="cap on a single backoff wait, seconds")
    a = ap.parse_args()

    start = normalise(a.url)
    if not start:
        sys.exit("not an http(s) URL: %s" % a.url)
    host, dom = urlparse(start).netloc, reg_domain(urlparse(start).netloc)

    rp = RobotFileParser()                                  # always honoured; no override flag on purpose
    rp.set_url("%s://%s/robots.txt" % (urlparse(start).scheme, host))
    try:
        rp.read()
        print("robots.txt read from %s" % rp.url, file=sys.stderr)
    except Exception:
        print("robots.txt unreachable - treating everything as allowed", file=sys.stderr)
        rp = None
    delay = max(a.delay, (rp.crawl_delay(UA) or 0) if rp else 0)

    in_scope = (lambda u: urlparse(u).netloc == host) if a.same_host else (lambda u: reg_domain(urlparse(u).netloc) == dom)
    sess = requests.Session(); sess.headers["User-Agent"] = UA
    queue, seen, recs, skipped = deque([(start, [start])]), {start}, [], 0

    while queue and len(recs) < a.max_pages:
        url, path = queue.popleft()
        if rp and not rp.can_fetch(UA, url):
            skipped += 1; continue
        r = None
        for attempt in range(a.retries + 1):                 # 429/503 cost a page each if not retried:
            try:                                             # an unretried rate-limit wasted 18% of a 200-page crawl
                r = sess.get(url, timeout=a.timeout, allow_redirects=True)
            except Exception as e:
                print("  ! %s (%s)" % (url[:90], type(e).__name__), file=sys.stderr)
                break
            if r.status_code not in (429, 503) or attempt == a.retries:
                break
            wait = float(r.headers.get("Retry-After") or 0) or delay * 2 ** (attempt + 1)
            print("  . %s on %s - waiting %.0fs (attempt %d/%d)"
                  % (r.status_code, url[-60:], wait, attempt + 1, a.retries), file=sys.stderr)
            time.sleep(min(wait, a.max_backoff))
        if r is None:
            continue
        mime = (r.headers.get("Content-Type") or "").split(";")[0].strip().lower()
        is_pdf, is_html = mime == "application/pdf", "html" in mime
        if is_pdf and a.no_pdf:
            continue
        lines, pages = ([], 0)
        if r.status_code == 200 and is_html:
            lines = text_lines(r.text)
        elif r.status_code == 200 and is_pdf:
            lines, pages = pdf_lines(r.content)

        recs.append({
            "Report ID": int(hashlib.sha1(dom.encode()).hexdigest()[:7], 16),
            "Report URL": start,
            "File ref": len(recs) + 1,
            "File storagekey": hashlib.sha256(r.content).hexdigest(),
            "File URL": url,
            "File Mimetype": mime or "application/octet-stream",
            "File Status": str(r.status_code),
            "PDF Pages": pages,
            "File URL Shortestpath": "\n".join(path),       # depth = newline count, as in the supplied scans
            "File text": "\n".join(lines),
            "File text lines": lines,
            "File text sep": "\u00a6".join(lines),
            "File text language": "",                        # empty in every supplied record; detected later
            "File text translated": "",
        })
        print("  [%4d] %s %s %s" % (len(recs), r.status_code, mime or "?", url[:95]), file=sys.stderr)

        if r.status_code == 200 and is_html:                 # links only from HTML, never from PDFs
            for href in BeautifulSoup(r.text, "lxml").find_all("a", href=True):
                nxt = normalise(urljoin(url, href["href"]))
                if nxt and nxt not in seen and in_scope(nxt) and not SKIP_EXT.search(urlparse(nxt).path):
                    seen.add(nxt); queue.append((nxt, path + [nxt]))
        if queue and len(recs) < a.max_pages:
            time.sleep(delay)

    json.dump(recs, open(a.out, "w", encoding="utf-8"), ensure_ascii=False)
    html_n = sum("html" in r["File Mimetype"] for r in recs)
    bad = [r for r in recs if r["File Status"] not in ("200", "202")]
    if bad:
        print("%d records are non-200 and will be dropped by featurise: %s"
              % (len(bad), dict((s2, sum(1 for r in bad if r["File Status"] == s2)) for s2 in {r["File Status"] for r in bad})),
              file=sys.stderr)
    print("\n%d records -> %s (%d HTML, %d PDF, %d other; %d URLs skipped by robots.txt, %d still queued)"
          % (len(recs), a.out, html_n, sum(r["PDF Pages"] > 0 for r in recs),
             len(recs) - html_n - sum(r["PDF Pages"] > 0 for r in recs), skipped, len(queue)), file=sys.stderr)
    print("next: python scripts/classify_scan.py %s -o %s" % (a.out, re.sub(r"\.json$", "", a.out) + "_results.jsonl"),
          file=sys.stderr)


if __name__ == "__main__":
    main()
