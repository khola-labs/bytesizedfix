#!/usr/bin/env python3
"""Check that every internal link/asset in docs/ resolves to a file (and #anchors exist).

    python3 tools/check_links.py            # check files on disk
    python3 tools/check_links.py http://127.0.0.1:8765/   # also fetch every page over HTTP
"""
import sys
import urllib.request
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlparse, unquote

DOCS = Path(__file__).resolve().parent.parent / "docs"


class P(HTMLParser):
    def __init__(self):
        super().__init__()
        self.refs, self.ids = [], set()

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if "id" in a:
            self.ids.add(a["id"])
        for k in ("href", "src"):
            if a.get(k) and not (tag == "link" and a.get("rel") == "canonical"):
                self.refs.append(a[k])


def parse(f):
    p = P()
    p.feed(f.read_text(encoding="utf-8"))
    return p


pages = sorted(DOCS.rglob("*.html"))
cache = {f: parse(f) for f in pages}
bad, n = [], 0
for f, p in cache.items():
    if f.name == "404.html":
        continue  # uses absolute /bytesizedfix/ paths rewritten at runtime
    for ref in p.refs:
        u = urlparse(ref)
        if u.scheme or ref.startswith("//") or ref.startswith("mailto:"):
            continue
        n += 1
        target = f if not u.path else (f.parent / unquote(u.path)).resolve()
        if target.is_dir():
            target = target / "index.html"
        if not target.exists() or DOCS.resolve() not in target.resolve().parents and target.resolve() != DOCS.resolve():
            bad.append(f"{f.relative_to(DOCS)} -> {ref} (missing)")
            continue
        if u.fragment and target.suffix == ".html":
            ids = cache.get(target, None) or parse(target)
            if u.fragment not in ids.ids:
                bad.append(f"{f.relative_to(DOCS)} -> {ref} (no #{u.fragment})")

print(f"{len(pages)} pages, {n} internal links checked, {len(bad)} broken")
for b in bad:
    print("  BROKEN", b)

if len(sys.argv) > 1:
    base = sys.argv[1]
    errs = 0
    for f in pages:
        url = urljoin(base, f.relative_to(DOCS).as_posix())
        try:
            with urllib.request.urlopen(url, timeout=5) as r:
                if r.status != 200:
                    errs += 1
                    print("  HTTP", r.status, url)
        except Exception as e:
            errs += 1
            print("  HTTP ERR", url, e)
    for extra in ("robots.txt", "sitemap.xml", "assets/style.css", "assets/app.js", "assets/favicon.svg"):
        try:
            urllib.request.urlopen(urljoin(base, extra), timeout=5).read()
        except Exception as e:
            errs += 1
            print("  HTTP ERR", extra, e)
    print(f"HTTP: {len(pages)} pages + extras fetched, {errs} errors")
    bad += ["http"] * errs

sys.exit(1 if bad else 0)
