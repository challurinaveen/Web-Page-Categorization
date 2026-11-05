"""Crawl a live site into DCR scan records, yielding them one at a time.

Same rules as scripts/crawl_site.py - robots.txt always honoured, one request at a time, a
delay between requests, 429/503 retried with backoff - but written as a generator so a caller
with a progress bar (the Streamlit app) can show each page as it lands.

Deliberately light: requests + beautifulsoup4 + lxml, with pypdf imported only when a PDF turns
up. Nothing here pulls in torch, sklearn or pandas, so it runs on a small cloud dyno.
"""
import hashlib
import re
import time
from collections import deque
from urllib.parse import urldefrag, urljoin, urlparse
from urllib.robotparser import RobotFileParser

import requests
from bs4 import BeautifulSoup

UA = "DCR-page-categorisation-prototype/1.0 (research crawler; +contact your DCR representative)"
SKIP_EXT = re.compile(r"\.(jpg|jpeg|png|gif|svg|webp|ico|css|js|woff2?|ttf|eot|mp4|webm|mp3|"
                      r"zip|gz|xlsx?|docx?|pptx?)$", re.I)
DROP_TAGS = ("script", "style", "noscript", "template", "svg")


def reg_domain(host):
    """example.co.uk -> example.co.uk ; www.a.example.com -> example.com (same rule as scan.py)."""
    p = host.lower().split(".")
    return (".".join(p[-3:]) if len(p) >= 3 and p[-2] in ("co", "com", "org", "ac", "gov")
            and len(p[-1]) == 2 else ".".join(p[-2:]))


def normalise(url):
    u = urlparse(urldefrag(url)[0])
    if u.scheme not in ("http", "https"):
        return None
    return u._replace(scheme=u.scheme.lower(), netloc=u.netloc.lower(), path=u.path or "/").geturl()


def text_lines(html):
    """Every visible line, nav and cookie banner included - boilerplate is stripped downstream."""
    soup = BeautifulSoup(html, "lxml")
    for t in soup(DROP_TAGS):
        t.decompose()
    return [ln.strip() for ln in soup.get_text("\n").splitlines() if ln.strip()]


def pdf_lines(content):
    try:
        import io as _io
        from pypdf import PdfReader
        r = PdfReader(_io.BytesIO(content))
        return [ln.strip() for p in r.pages
                for ln in (p.extract_text() or "").splitlines() if ln.strip()], len(r.pages)
    except Exception:
        return [], 0


def robots_for(start, session):
    """The site's robots.txt, or None if it cannot be read (then nothing is crawled)."""
    u = urlparse(start)
    rp = RobotFileParser()
    rp.set_url("%s://%s/robots.txt" % (u.scheme, u.netloc))
    try:
        r = session.get(rp.url, timeout=10)
        rp.parse(r.text.splitlines() if r.status_code == 200 else [])
        return rp
    except Exception:
        return None


def crawl(start, max_pages=25, delay=1.0, timeout=20, same_host=False, include_pdf=True,
          retries=2, max_backoff=30, on_event=None):
    """Yield DCR-format records for `start` and the pages it links to.

    on_event(kind, detail) is called as things happen: "fetched", "skipped", "blocked",
    "ratelimit", "error". It is only for display - the crawl does not depend on it.
    """
    def say(kind, detail):
        if on_event:
            on_event(kind, detail)

    start = normalise(start)
    if not start:
        raise ValueError("not an http(s) URL")
    host, dom = urlparse(start).netloc.lower(), reg_domain(urlparse(start).netloc)

    session = requests.Session()
    session.headers["User-Agent"] = UA
    rp = robots_for(start, session)

    def in_scope(u):
        h = urlparse(u).netloc.lower()
        return h == host if same_host else reg_domain(h) == dom

    queue, seen, n = deque([(start, [start])]), {start}, 0
    while queue and n < max_pages:
        url, path = queue.popleft()
        if rp and not rp.can_fetch(UA, url):
            say("blocked", url)
            continue

        r = None
        for attempt in range(retries + 1):
            try:
                r = session.get(url, timeout=timeout, allow_redirects=True)
            except Exception as e:
                say("error", "%s (%s)" % (url, type(e).__name__))
                r = None
                break
            if r.status_code not in (429, 503) or attempt == retries:
                break
            wait = float(r.headers.get("Retry-After") or 0) or delay * 2 ** (attempt + 1)
            say("ratelimit", "%s on %s - waiting %.0fs" % (r.status_code, url, min(wait, max_backoff)))
            time.sleep(min(wait, max_backoff))
        if r is None:
            continue

        mime = (r.headers.get("Content-Type") or "").split(";")[0].strip().lower()
        is_pdf, is_html = mime == "application/pdf", "html" in mime
        if is_pdf and not include_pdf:
            say("skipped", url)
            continue

        lines, pages = [], 0
        if r.status_code == 200 and is_html:
            lines = text_lines(r.text)
        elif r.status_code == 200 and is_pdf:
            lines, pages = pdf_lines(r.content)

        n += 1
        say("fetched", "%s %s" % (r.status_code, url))
        yield {
            "Report ID": int(hashlib.sha1(dom.encode()).hexdigest()[:7], 16),
            "Report URL": start,
            "File ref": n,
            "File storagekey": hashlib.sha256(r.content).hexdigest(),
            "File URL": url,
            "File Mimetype": mime or "application/octet-stream",
            "File Status": str(r.status_code),
            "PDF Pages": pages,
            "File URL Shortestpath": "\n".join(path),
            "File text": "\n".join(lines),
            "File text lines": lines,
            "File text sep": "\u00a6".join(lines),
            "File text language": "",      # empty in every supplied record; detected downstream
            "File text translated": "",
        }

        if r.status_code == 200 and is_html:        # links only from HTML, never from PDFs
            for a in BeautifulSoup(r.text, "lxml").find_all("a", href=True):
                nxt = normalise(urljoin(url, a["href"]))
                if (nxt and nxt not in seen and in_scope(nxt)
                        and not SKIP_EXT.search(urlparse(nxt).path)):
                    seen.add(nxt)
                    queue.append((nxt, path + [nxt]))
        if queue and n < max_pages:
            time.sleep(delay)
