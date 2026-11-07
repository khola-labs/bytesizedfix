#!/usr/bin/env python3
"""Render the Byte-Sized Fix course hub from data/roadmap.json into docs/.

    python3 build.py            # rebuild docs/
    python3 build.py --today 2026-11-20   # pretend "today" (affects 'Up next' + past-date wording)

Standard library only. Every page uses relative links, so docs/ works at any base
path (GitHub Pages /bytesizedfix/, a custom domain, or `python3 -m http.server`).
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import shutil
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data" / "roadmap.json"
SRC = ROOT / "src"
OUT = ROOT / "docs"
ASSETS = ["style.css", "app.js", "favicon.svg", "favicon-32.png", "apple-touch-icon.png", "kursor-320.webp", "og.jpg"]

TRACKS = [  # (track name in JSON, page slug, nav label, short label)
    ("DSA", "dsa", "DSA", "DSA"),
    ("System Design", "system-design", "System Design", "SD"),
    ("Interview Craft", "interview", "Interview Craft", "Interview"),
]
TRACK_SLUG = {t[0]: t[1] for t in TRACKS}
TRACK_INTRO = {
    "DSA": "Data structures and algorithms, pattern by pattern: from Big-O to DP, every lesson built on an everyday Indian story. Code on screen is Python.",
    "System Design": "From “what happens when you open a URL” to designing UPI, Tatkal and IPL streaming. Fundamentals, distributed systems, LLD and India-first case studies.",
    "Interview Craft": "How to perform in the room: solving a coding problem out loud, running a design interview, STAR stories and a full mock.",
}
SLOT_OFFSET = {"Mon": 0, "Tue": 1, "Wed": 2, "Thu": 3, "Fri": 4, "Sat": 5, "Sun": 6}
CASE_STUDY_MODULE = "SF"
FIRST_STEPS = [  # (lesson id, why) — the "START HERE" order on the home page
    ("I01", "The map: how the course is laid out and how to use this hub."),
    ("D01", "Start of the DSA track. Every later DSA lesson measures code this way."),
    ("S01", "Start of the System Design track: what really happens between tap and page."),
    ("I02", "How to attack a coding problem you have never seen. Use it from your first practice problem."),
    ("C02", "See where it all leads: a full UPI-like design. The short pilot is already out."),
]


# ---------------------------------------------------------------- data helpers
def load(today: dt.date):
    d = json.loads(DATA.read_text(encoding="utf-8"))
    meta, lessons = d["meta"], d["lessons"]
    site = meta["site"]
    week1 = dt.date.fromisoformat(site["week1_monday"])
    mods = {m["code"]: m for m in meta["modules"]}
    mod_order = [m["code"] for m in meta["modules"]]
    by_id = {}
    for l in lessons:
        l["num"] = int(re.sub(r"\D", "", l["course_no"]) or 0)
        l["slug"] = l["id"].lower()
        l["date"] = None
        if isinstance(l.get("release_week"), int) and l["release_week"] >= 1 and l.get("release_slot") in SLOT_OFFSET:
            l["date"] = week1 + dt.timedelta(weeks=l["release_week"] - 1, days=SLOT_OFFSET[l["release_slot"]])
        l["out"] = bool(l.get("video_id"))
        l["short_out"] = bool(l.get("short_id"))
        by_id[l["id"]] = l
    # learning order inside each track: module order, then course number
    order = {}
    for track, *_ in TRACKS:
        seq = sorted((l for l in lessons if l["track"] == track), key=lambda l: (mod_order.index(l["module"]), l["num"]))
        for i, l in enumerate(seq):
            l["prev"] = seq[i - 1]["id"] if i else None
            l["next"] = seq[i + 1]["id"] if i + 1 < len(seq) else None
        order[track] = seq
    # sanity checks
    problems = []
    for l in lessons:
        for p in l["prerequisites"]:
            if p not in by_id:
                problems.append(f"{l['id']}: unknown prerequisite {p}")
    seen = {}
    for l in lessons:
        if l["date"]:
            if l["date"] in seen:
                problems.append(f"{l['id']} and {seen[l['date']]} share release date {l['date']}")
            seen[l["date"]] = l["id"]
    kws = {}
    for l in lessons:
        k = l["cheatsheet_keyword"]
        if k in kws:
            problems.append(f"keyword {k} used by {kws[k]} and {l['id']}")
        kws[k] = l["id"]
    for p in problems:
        print("WARNING:", p)
    return meta, site, lessons, by_id, mods, mod_order, order


def fmt_date(d: dt.date | None) -> str:
    return f"{d:%a} {d.day} {d:%b %Y}" if d else ""


def status_badge(l, today) -> str:
    if l["out"]:
        return '<span class="badge out">Out now</span>'
    parts = []
    if l["short_out"]:
        parts.append('<span class="badge out">Short out now</span>')
    if l["date"] and l["date"] >= today:
        label = "Full lesson " if l["short_out"] else "Coming "
        parts.append(f'<span class="badge soon">{label}{fmt_date(l["date"])}</span>')
    else:
        parts.append('<span class="badge soon">Full lesson coming soon</span>' if l["short_out"] else '<span class="badge soon">Coming soon</span>')
    return " ".join(parts)


def lesson_label(l) -> str:
    return f"{l['course_no'] if l['track'] == 'Interview Craft' else 'L' + str(l['num'])}"


def yt_watch(vid: str, short=False) -> str:
    return f"https://www.youtube.com/shorts/{vid}" if short else f"https://www.youtube.com/watch?v={vid}"


# ---------------------------------------------------------------- page shell
def page(*, title, desc, body, depth=0, current=None, path="", site, extra_head="") -> str:
    r = "../" * depth
    nav = [("index.html", "Home", "home")] + [(f"{slug}.html", label, slug) for _, slug, label, _ in TRACKS] + [
        ("lessons.html", "All lessons", "lessons"), ("calendar.html", "Calendar", "calendar")]
    cur = ' aria-current="page"'
    nav_html = "".join(
        f'<a href="{r}{href}"{cur if key == current else ""}>{escape(label)}</a>' for href, label, key in nav)
    canon = site["base_url"] + path
    full_title = title if title.startswith("Byte-Sized Fix") else f"{title} · Byte-Sized Fix"
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{escape(full_title)}</title>
<meta name="description" content="{escape(desc)}">
<link rel="canonical" href="{escape(canon)}">
<meta name="theme-color" content="#111a32">
<meta property="og:type" content="website">
<meta property="og:site_name" content="Byte-Sized Fix">
<meta property="og:title" content="{escape(full_title)}">
<meta property="og:description" content="{escape(desc)}">
<meta property="og:url" content="{escape(canon)}">
<meta property="og:image" content="{escape(site['base_url'])}assets/og.jpg">
<meta name="twitter:card" content="summary_large_image">
<link rel="icon" href="{r}assets/favicon.svg" type="image/svg+xml">
<link rel="icon" href="{r}assets/favicon-32.png" sizes="32x32" type="image/png">
<link rel="apple-touch-icon" href="{r}assets/apple-touch-icon.png">
<link rel="stylesheet" href="{r}assets/style.css">
<script src="{r}assets/app.js" defer></script>
{extra_head}</head>
<body>
<a class="skip" href="#main">Skip to content</a>
<header class="site-head">
<div class="wrap">
<a class="brand" href="{r}index.html"><img src="{r}assets/favicon.svg" alt="" width="28" height="28">BYTE-SIZED FIX</a>
<nav class="nav" aria-label="Main">{nav_html}</nav>
</div>
</header>
<main id="main" tabindex="-1">
<div class="wrap">
{body}
</div>
</main>
<footer class="site-foot">
<div class="wrap">
<p><strong>Free forever. Made by Khola Labs.</strong><br>No ads, no sign-up, no tracking. Your progress stays in your browser.</p>
<ul>
<li><a href="{escape(site['youtube'])}" rel="noopener">YouTube</a></li>
<li><a href="{escape(site['instagram'])}" rel="noopener">Instagram</a></li>
<li><a href="{r}lessons.html">All lessons</a></li>
<li><a href="{r}calendar.html">Release calendar</a></li>
</ul>
</div>
</footer>
</body>
</html>
"""


def check(key, label, extra_cls="") -> str:
    return (f'<label class="check js-only {extra_cls}" hidden><input type="checkbox" data-progress="{escape(key)}">'
            f'<span>{label}</span></label>')


def lesson_row(l, today, r, mods, show_module=False) -> str:
    mod = f' · {escape(mods[l["module"]]["title"])}' if show_module else ""
    search = " ".join([l["id"], l["title_plain"], l["title_hook"], l["track"], mods[l["module"]]["title"],
                       l["cheatsheet_keyword"], " ".join(l["learning_goals"]), " ".join(p["title"] for p in l["practice"])]).lower()
    return f"""<li class="lesson-row" data-row data-lesson="{l['id']}" data-track="{escape(l['track'])}" data-module="{l['module']}" data-out="{1 if (l['out'] or l['short_out']) else 0}" data-search="{escape(search)}">
<span class="tick"><label class="js-only" hidden><input type="checkbox" data-progress="L:{l['id']}"><span class="visually-hidden">Mark {escape(l['title_plain'])} as done</span></label></span>
<span class="body"><a class="t" href="{r}lessons/{l['slug']}.html"><span class="num">{escape(lesson_label(l))}</span>{escape(l['title_plain'])}</a>
<span class="sub">{escape(l['title_hook'])}</span>
<span class="meta">{status_badge(l, today)}<span>~{l['target_length_min']} min</span><span>{len(l['practice'])} practice</span>{f'<span>{escape(l["track"])}{mod}</span>' if show_module else ''}</span></span>
</li>"""


def meter(ids, label="") -> str:
    return f"""<div data-meter="{' '.join(ids)}" class="js-only" hidden>{f'<p class="meter-label"><strong>{escape(label)}</strong></p>' if label else ''}
<div class="meter" role="meter" aria-label="{escape(label or 'Progress')}" aria-valuemin="0" aria-valuemax="{len(ids)}" aria-valuenow="0"><span></span></div>
<p class="meter-label" data-meter-label>0 / {len(ids)} lessons done</p></div>"""


STORAGE_NOTE = '<p class="storage-note" data-storage-note hidden>Your browser is blocking local storage, so ticks won’t be saved after you leave this page. Everything else works.</p>'


# ---------------------------------------------------------------- pages
def home(meta, site, lessons, by_id, mods, mod_order, order, today):
    r = ""
    n_practice = sum(len(l["practice"]) for l in lessons)
    out_now = [l for l in lessons if l["out"] or l["short_out"]]
    upcoming = sorted((l for l in lessons if l["date"] and l["date"] >= today and not l["out"]), key=lambda l: l["date"])[:4]
    track_cards = []
    for track, slug, label, _ in TRACKS:
        seq = order[track]
        nmods = len({l["module"] for l in seq})
        first = seq[0]
        track_cards.append(f"""<div class="card">
<h3><a href="{slug}.html">{escape(label)}</a></h3>
<p>{escape(TRACK_INTRO[track])}</p>
<p class="meter-label">{len(seq)} lessons · {nmods} module{'s' if nmods > 1 else ''} · starts with <a href="lessons/{first['slug']}.html">{escape(first['title_plain'])}</a></p>
{meter([l['id'] for l in seq], 'Your progress')}
</div>""")
    steps = []
    for lid, why in FIRST_STEPS:
        l = by_id[lid]
        steps.append(f'<li><a href="lessons/{l["slug"]}.html"><strong>{escape(l["title_plain"])}</strong></a> {status_badge(l, today)}<span class="why">{escape(why)}</span></li>')
    out_cards = []
    for l in out_now:
        label = l.get("short_label") or ("Full lesson" if l["out"] else "Short")
        out_cards.append(f"""<div class="card accent">
<p class="eyebrow">{escape(l['track'])} · {escape(label)} out now</p>
<h3><a href="lessons/{l['slug']}.html">{escape(l['title_plain'])}</a></h3>
<p class="hook">{escape(l['title_hook'])}</p>
<div class="btns"><a class="btn" href="{yt_watch(l['video_id'] or l['short_id'], short=not l['out'])}" rel="noopener">▶ Watch on YouTube</a><a class="btn ghost" href="lessons/{l['slug']}.html">Lesson page &amp; practice</a></div>
</div>""")
    up = "".join(f'<li class="lesson-row"><span class="tick" aria-hidden="true">⏳</span><span class="body"><a class="t" href="lessons/{l["slug"]}.html">{escape(l["title_plain"])}</a><span class="meta"><span class="badge soon">{fmt_date(l["date"])}</span><span>{escape(l["track"])}</span></span></span></li>' for l in upcoming)
    body = f"""<section class="hero">
<img src="assets/kursor-320.webp" alt="Kursor, the Byte-Sized Fix robot with a >_ terminal for a face" width="180" height="180">
<div>
<p class="eyebrow">&gt;_ Free course · Hinglish narration · English on-screen</p>
<h1>DSA + System Design, <span class="y">one free path.</span></h1>
<p class="lead">100 animated lessons that take you from Big-O to designing UPI. Every lesson comes with a short, a cheat-sheet, hand-picked practice problems and the sources we used. All in one place, free forever.</p>
<div class="btns"><a class="btn" href="#start">Start here</a><a class="btn ghost" href="lessons.html">Browse all {len(lessons)} lessons</a><a class="btn ghost" href="{escape(site['youtube'])}" rel="noopener">YouTube channel</a></div>
</div>
</section>

<form class="filters" action="lessons.html" method="get" role="search" style="grid-template-columns:1fr auto">
<div><label for="home-q">Search lessons</label><input type="search" id="home-q" name="q" placeholder="e.g. heap, sliding window, sharding, UPI"></div>
<div><button class="btn" type="submit">Search</button></div>
</form>

<div class="grid three">
<div class="card"><h2 class="h3" style="font-size:1.1rem">{len(lessons)} lessons</h2><p>{len(order['DSA'])} DSA · {len(order['System Design'])} System Design · {len(order['Interview Craft'])} Interview Craft, in {len(mods)} modules.</p></div>
<div class="card"><h2 style="font-size:1.1rem">2 new lessons a week</h2><p><strong>Tuesday:</strong> DSA. <strong>Friday:</strong> System Design. Plus Shorts and Reels in between. See the <a href="calendar.html">release calendar</a>.</p></div>
<div class="card"><h2 style="font-size:1.1rem">{n_practice} practice links</h2><p>Free problems on LeetCode, Hello Interview, the System Design Primer and more, ordered from first try to stretch.</p></div>
</div>

<h2>Out now</h2>
<div class="grid two">{''.join(out_cards)}</div>

<h2 id="start">Start here</h2>
<p>New to all of it? Go in this order. After step 3 you can run the two tracks side by side: one DSA lesson and one System Design lesson a week.</p>
<ol class="steps">{''.join(steps)}</ol>

<h2>The tracks</h2>
<div class="grid three">{''.join(track_cards)}</div>

<h2>Who it’s for</h2>
<div class="grid two">
<div class="card"><h3>Students</h3><p>2nd to 4th year CS and IT students preparing for placements. Start at lesson 1 of either track; nothing is assumed beyond basic Python.</p></div>
<div class="card"><h3>Working engineers</h3><p>0–5 years of experience, preparing for SDE-1/SDE-2 interviews at product companies, including the machine-coding (LLD) round.</p></div>
</div>

<h2>Why this course</h2>
<ul>
<li><strong>One path, both tracks.</strong> DSA, System Design, LLD and interview craft in one ordered course, with one hub for practice.</li>
<li><strong>Animated, in Hinglish.</strong> Code-drawn animations, narrated in Hinglish, with English text and Python code on screen.</li>
<li><strong>Indian case studies.</strong> UPI, Tatkal booking, IPL streaming, 10-minute delivery, fantasy-cricket leaderboards.</li>
<li><strong>Intuition over memorising.</strong> Each DSA lesson teaches the pattern with a story, then gives problems from first-try to stretch.</li>
</ul>

<h2>How each lesson works</h2>
<ol>
<li>Watch the long lesson (8–20 min) or its 60–90 s Short.</li>
<li>When a lesson is out, comment its keyword on the Reel or Short to get the one-page cheat-sheet in your DMs.</li>
<li>Solve the practice problems on the lesson page and tick them off.</li>
<li>Go deeper with the linked sources when you want the full theory.</li>
</ol>

<h2>Coming up</h2>
<ul class="lessons">{up}</ul>
<p><a href="calendar.html">Full release calendar →</a></p>

<h2>Your progress</h2>
<p>Tick lessons and problems as you go. Ticks are saved only in this browser, on this device. No account needed.</p>
{STORAGE_NOTE}
<div class="card">{meter([l['id'] for l in lessons], 'Whole course')}
<noscript><p>Turn on JavaScript to track your progress.</p></noscript>
<button type="button" class="btn ghost" id="reset-progress" hidden>Reset my progress</button></div>

<h2>Follow along</h2>
<div class="btns"><a class="btn" href="{escape(site['youtube'])}" rel="noopener">YouTube: @thebytesizedfix</a><a class="btn ghost" href="{escape(site['instagram'])}" rel="noopener">Instagram: @thebytesizedfix</a></div>
"""
    return page(title="Byte-Sized Fix · Free DSA + System Design course in Hinglish",
                desc="A free, animated DSA and System Design course in Hinglish: 100 lessons, practice problems, cheat-sheets and Indian case studies like UPI and Tatkal.",
                body=body, current="home", path="", site=site)


def track_page(track, slug, label, site, order, mods, mod_order, today):
    r = ""
    seq = order[track]
    blocks = []
    for code in mod_order:
        ls = [l for l in seq if l["module"] == code]
        if not ls:
            continue
        m = mods[code]
        blocks.append(f"""<section class="module" id="{code.lower()}" aria-labelledby="h-{code.lower()}">
<h2 id="h-{code.lower()}">{escape(m['title'])}</h2>
<p class="blurb">{escape(m['blurb'])}</p>
{meter([l['id'] for l in ls])}
<ul class="lessons">{''.join(lesson_row(l, today, r, mods) for l in ls)}</ul>
</section>""")
    toc = "".join(f'<li><a href="#{c.lower()}">{escape(mods[c]["title"])}</a></li>' for c in mod_order if any(l["module"] == c for l in seq))
    body = f"""<p class="crumbs"><a href="index.html">Home</a> › {escape(label)}</p>
<p class="eyebrow">Track · {len(seq)} lessons</p>
<h1>{escape(label)}</h1>
<p class="lead">{escape(TRACK_INTRO[track])}</p>
{STORAGE_NOTE}
<div class="card">{meter([l['id'] for l in seq], 'Track progress')}<p class="meter-label">Lessons are listed in learning order. Release order differs a little; see the <a href="calendar.html">calendar</a>.</p></div>
{f'<nav aria-label="Modules"><h2>Modules</h2><ol>{toc}</ol></nav>' if len(blocks) > 1 else ''}
{''.join(blocks)}"""
    return page(title=f"{label} track", desc=f"{label}: {TRACK_INTRO[track]}", body=body, current=slug, path=f"{slug}.html", site=site)


def catalogue(lessons, site, order, mods, mod_order, today):
    r = ""
    groups = []
    for track, slug, label, _ in TRACKS:
        for code in mod_order:
            ls = [l for l in order[track] if l["module"] == code]
            if ls:
                groups.append(f'<section class="module" data-group><h2>{escape(mods[code]["title"])}</h2><ul class="lessons">{"".join(lesson_row(l, today, r, mods) for l in ls)}</ul></section>')
    track_opts = "".join(f'<option value="{escape(t)}">{escape(lbl)}</option>' for t, _, lbl, _ in TRACKS)
    mod_opts = "".join(f'<option value="{c}" data-track="{escape(next(l["track"] for l in lessons if l["module"] == c))}">{escape(mods[c]["title"])}</option>' for c in mod_order)
    body = f"""<p class="crumbs"><a href="index.html">Home</a> › All lessons</p>
<h1>All lessons</h1>
<p class="lead">Search by topic, problem name or cheat-sheet keyword, or filter by track and module.</p>
{STORAGE_NOTE}
<form class="filters" id="filters" role="search" action="lessons.html" method="get">
<div><label for="f-q">Search</label><input type="search" id="f-q" name="q" placeholder="e.g. two sum, DP, Kafka, LRU" autocomplete="off"></div>
<div><label for="f-track">Track</label><select id="f-track" name="track"><option value="">All tracks</option>{track_opts}</select></div>
<div><label for="f-module">Module</label><select id="f-module" name="module"><option value="">All modules</option>{mod_opts}</select></div>
<div><label for="f-status">Show</label><select id="f-status"><option value="">Everything</option><option value="out">Out now</option><option value="coming">Coming soon</option><option value="todo">Not done yet</option><option value="done">Done</option></select></div>
</form>
<p id="count" role="status" aria-live="polite">{len(lessons)} lessons</p>
{''.join(groups)}"""
    return page(title="All lessons", desc="Search and filter all 100 lessons of the free Byte-Sized Fix DSA + System Design course.",
                body=body, current="lessons", path="lessons.html", site=site)


def calendar_page(lessons, site, today):
    weeks = {}
    unscheduled = []
    for l in lessons:
        if l["date"]:
            weeks.setdefault(l["release_week"], []).append(l)
        else:
            unscheduled.append(l)
    items = []
    for w in sorted(weeks):
        cells = []
        for l in sorted(weeks[w], key=lambda l: l["date"]):
            cells.append(f'<div class="slot"><small>{fmt_date(l["date"])} · {escape(l["track"])}</small><a href="lessons/{l["slug"]}.html">{escape(l["title_plain"])}</a> {status_badge(l, today) if (l["out"] or l["short_out"]) else ""}</div>')
        items.append(f'<li class="week"><span class="wk">Week {w}</span><div class="slots">{"".join(cells)}</div></li>')
    pre = "".join(f'<li><a href="lessons/{l["slug"]}.html">{escape(l["title_plain"])}</a> · course trailer, date to be announced</li>' for l in unscheduled)
    body = f"""<p class="crumbs"><a href="index.html">Home</a> › Release calendar</p>
<h1>Release calendar</h1>
<p class="lead">Two long lessons a week: <strong>DSA on Tuesday</strong>, <strong>System Design on Friday</strong>. Dates are the plan and may shift; each lesson page shows the latest status.</p>
<p>Release order is not learning order: hook-friendly case studies (UPI, Tatkal, IPL) come early and are made to stand alone. For learning order, use the <a href="dsa.html">DSA</a> and <a href="system-design.html">System Design</a> track pages.</p>
{f'<ul class="pre-list">{pre}</ul>' if pre else ''}
<ol class="weeks">{''.join(items)}</ol>"""
    return page(title="Release calendar", desc="When each Byte-Sized Fix lesson comes out: DSA every Tuesday, System Design every Friday.",
                body=body, current="calendar", path="calendar.html", site=site)


def video_block(l, today):
    r = "../"
    title = l["title_plain"]
    if l["out"]:
        main = f"""<div class="video"><button type="button" class="play" data-yt="{escape(l['video_id'])}" data-title="{escape(title)}">
<span class="icon" aria-hidden="true">▶</span><span>Play the full lesson</span><small>Loads YouTube (privacy-enhanced mode)</small></button></div>
<p><a href="{yt_watch(l['video_id'])}" rel="noopener">Watch on YouTube</a></p>"""
    else:
        when = f"coming {fmt_date(l['date'])}" if l["date"] and l["date"] >= today else "coming soon"
        main = f"""<div class="video placeholder" role="img" aria-label="Video placeholder: full lesson {escape(when)}">
<img src="{r}assets/kursor-320.webp" alt="" width="72" height="72">
<strong>Full lesson {escape(when)}</strong><span>Kursor is still drawing this one.</span></div>"""
    short = ""
    if l["short_out"]:
        lab = l.get("short_label") or "Short version"
        short = f"""<div><h2 style="margin-top:0;font-size:1.1rem">{escape(lab)}</h2>
<div class="video vertical"><button type="button" class="play" data-yt="{escape(l['short_id'])}" data-title="{escape(title)} (Short)">
<span class="icon" aria-hidden="true">▶</span><span>Play the Short</span><small>Loads YouTube (privacy-enhanced mode)</small></button></div>
<p><a href="{yt_watch(l['short_id'], short=True)}" rel="noopener">Watch the Short on YouTube</a></p></div>"""
    return f'<div class="media-row{" has-short" if short else ""}"><div>{main}</div>{short}</div>'


def lesson_page(l, by_id, mods, site, today):
    r = "../"
    slug_track = TRACK_SLUG[l["track"]]
    mod = mods[l["module"]]
    goals = "".join(f"<li>{escape(g)}</li>" for g in l["learning_goals"])
    if l["prerequisites"]:
        pre = "<ul>" + "".join(
            f'<li><a href="{by_id[p]["slug"]}.html">{escape(by_id[p]["title_plain"])}</a> <span class="meter-label" style="display:inline">({escape(by_id[p]["track"])} {escape(lesson_label(by_id[p]))})</span></li>'
            for p in l["prerequisites"]) + "</ul>"
    else:
        pre = "<p>None. You can start here.</p>"
    prac = []
    free = " \u00b7 free"
    for p in l["practice"]:
        key = f"P:{l['id']}|{p['url']}"
        diff = f'<span class="diff {escape(p["difficulty"])}">{escape(p["difficulty"])}</span> · ' if p.get("difficulty") else ""
        note = f'<span class="note">{escape(p["note"])}</span>' if p.get("note") else ""
        prac.append(f"""<li data-row><label class="js-only" hidden><input type="checkbox" data-progress="{escape(key)}"><span class="visually-hidden">Mark {escape(p['title'])} as solved</span></label>
<span class="p-main"><a href="{escape(p['url'])}" rel="noopener">{escape(p['title'])}</a><span class="src">{diff}{escape(p['platform'])}{' · free' if p.get('free') else ''}</span>{note}</span></li>""")
    srcs = "".join(f'<li><a href="{escape(s["url"])}" rel="noopener">{escape(s["title"])}</a></li>' for s in l["sources"])
    alts = ""
    if l.get("code_alternatives"):
        alts = "<h2>Code in other languages</h2><p>The lesson uses Python on screen. Prefer C++ or Java? Try these:</p><ul>" + "".join(
            f'<li><a href="{escape(a["url"])}" rel="noopener">{escape(a.get("lang", ""))}: {escape(a.get("title", a["url"]))}</a></li>' for a in l["code_alternatives"]) + "</ul>"
    pager = []
    if l["prev"]:
        p = by_id[l["prev"]]
        pager.append(f'<a class="prev" href="{p["slug"]}.html" rel="prev"><small>← Previous</small>{escape(p["title_plain"])}</a>')
    if l["next"]:
        n = by_id[l["next"]]
        pager.append(f'<a class="next" href="{n["slug"]}.html" rel="next"><small>Next →</small>{escape(n["title_plain"])}</a>')
    disclaimer = ""
    if l["module"] == CASE_STUDY_MODULE:
        disclaimer = '<p class="disclaimer">This is a learning design for a system <em>like</em> the one named. It is not a description of any company’s internal architecture.</p>'
    code_note = "<span>Code on screen: Python</span>" if l["track"] == "DSA" else ""
    kw = escape(l["cheatsheet_keyword"])
    # Only promise the DM once something is out (the ManyChat flow is made when the lesson/Short goes live).
    if l.get("video_id") or l.get("short_id"):
        cheat_line = f'<p>Comment <span class="badge kw">{kw}</span> on the Reel or Short and we’ll DM you the one-page cheat-sheet, the video link and this page.</p>'
    else:
        cheat_line = f'<p>The one-page cheat-sheet comes out with this lesson. When it’s live, comment <span class="badge kw">{kw}</span> on the Reel or Short to get it in your DMs.</p>'
    body = f"""<p class="crumbs"><a href="../index.html">Home</a> › <a href="../{slug_track}.html">{escape(l['track'])}</a> › <a href="../{slug_track}.html#{l['module'].lower()}">{escape(mod['title'])}</a></p>
<div class="lesson-head">
<p class="eyebrow">{escape(l['track'])} · Lesson {escape(lesson_label(l))} · {escape(mod['title'])}</p>
<h1>{escape(l['title_plain'])}</h1>
<p class="lead hook">“{escape(l['title_hook'])}”</p>
<div class="lesson-facts">{status_badge(l, today)}<span>Lesson ~{l['target_length_min']} min</span><span>Short {escape(str(l.get('short', {}).get('length_s', '60-90')))} s</span>{code_note}<span>Cheat-sheet: <span class="badge kw">{kw}</span></span></div>
{check('L:' + l['id'], '<strong>I’ve finished this lesson</strong>')}
</div>
{STORAGE_NOTE}
{video_block(l, today)}
{disclaimer}
<h2>What you’ll learn</h2>
<ul class="goals">{goals}</ul>
<h2>The story behind it</h2>
<p>{escape(l['hook_story'])}</p>
<h2>Before this lesson</h2>
{pre}
<h2>Practice <span class="meter-label js-only" style="display:inline;font-weight:400" data-pmeter="{l['id']}" hidden></span></h2>
<p>Ordered from first try to stretch. All free.</p>
<ul class="practice">{''.join(prac)}</ul>
{alts}
<h2>Get the cheat-sheet</h2>
<div class="kwbox">{cheat_line}
<p class="meter-label">Find us on <a href="{escape(site['instagram'])}" rel="noopener">Instagram</a> and <a href="{escape(site['youtube'])}" rel="noopener">YouTube</a> as @thebytesizedfix.</p></div>
<h2>Sources &amp; further reading</h2>
<ul>{srcs}</ul>
{check('L:' + l['id'], 'Mark this lesson as done')}
<nav class="pager" aria-label="Lessons">{''.join(pager)}</nav>"""
    desc = f"{l['title_plain']} — free animated lesson in Hinglish with {len(l['practice'])} practice problems and a cheat-sheet. {l['title_hook']}."
    return page(title=f"{l['title_plain']} ({l['track']} {lesson_label(l)})", desc=desc, body=body, depth=1,
                current=slug_track, path=f"lessons/{l['slug']}.html", site=site)


NOT_FOUND = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Page not found · Byte-Sized Fix</title><meta name="robots" content="noindex">
<style>
:root{color-scheme:dark}body{margin:0;min-height:100vh;display:grid;place-items:center;background:#0a1022;color:#eef1f8;font:1rem/1.6 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;padding:1rem;box-sizing:border-box}
main{max-width:30rem;text-align:center}.k{font:700 3rem/1 ui-monospace,Menlo,Consolas,monospace;color:#ffd60a}
a{color:#ffd60a}a:focus-visible{outline:3px solid #ffd60a;outline-offset:2px}
</style></head><body><main>
<p class="k" aria-hidden="true">&gt;_ 404</p>
<h1>Kursor couldn’t find that page</h1>
<p>The link may be old, or the lesson may have moved.</p>
<p><a id="home" href="/bytesizedfix/">Go to the course home</a> · <a id="all" href="/bytesizedfix/lessons.html">Browse all lessons</a></p>
</main>
<script>
// Works at /bytesizedfix/ (GitHub Pages project site) and at a root domain.
(function(){var p=location.pathname,i=p.indexOf("/bytesizedfix/"),b=i>=0?p.slice(0,i)+"/bytesizedfix/":"/";
document.getElementById("home").href=b;document.getElementById("all").href=b+"lessons.html";})();
</script>
</body></html>
"""


# ---------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--today", help="YYYY-MM-DD (default: real today)")
    args = ap.parse_args()
    today = dt.date.fromisoformat(args.today) if args.today else dt.date.today()

    meta, site, lessons, by_id, mods, mod_order, order = load(today)

    (OUT / "assets").mkdir(parents=True, exist_ok=True)
    (OUT / "lessons").mkdir(exist_ok=True)
    for a in ASSETS:
        shutil.copy2(SRC / a, OUT / "assets" / a)

    pages = {}
    pages["index.html"] = home(meta, site, lessons, by_id, mods, mod_order, order, today)
    for track, slug, label, _ in TRACKS:
        pages[f"{slug}.html"] = track_page(track, slug, label, site, order, mods, mod_order, today)
    pages["lessons.html"] = catalogue(lessons, site, order, mods, mod_order, today)
    pages["calendar.html"] = calendar_page(lessons, site, today)
    for l in lessons:
        pages[f"lessons/{l['slug']}.html"] = lesson_page(l, by_id, mods, site, today)
    for path, html in pages.items():
        (OUT / path).write_text(html, encoding="utf-8")
    (OUT / "404.html").write_text(NOT_FOUND, encoding="utf-8")
    (OUT / ".nojekyll").write_text("", encoding="utf-8")
    (OUT / "robots.txt").write_text(f"User-agent: *\nAllow: /\n\nSitemap: {site['base_url']}sitemap.xml\n", encoding="utf-8")
    lastmod = today.isoformat()
    urls = "".join(
        f"  <url><loc>{escape(site['base_url'] + ('' if p == 'index.html' else p))}</loc><lastmod>{lastmod}</lastmod></url>\n"
        for p in pages)
    (OUT / "sitemap.xml").write_text(
        f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n{urls}</urlset>\n', encoding="utf-8")
    # Anything in docs/ we didn't just write is stale (e.g. a removed lesson): move it to the Trash, never delete.
    keep = {OUT / p for p in pages} | {OUT / "assets" / a for a in ASSETS} | {OUT / n for n in ("404.html", ".nojekyll", "robots.txt", "sitemap.xml")}
    stale = [f for f in OUT.rglob("*") if f.is_file() and f not in keep]
    if stale:
        trash = Path.home() / ".Trash" / f"bsf-docs-stale-{dt.datetime.now():%Y%m%d-%H%M%S}"
        trash.mkdir(parents=True)
        for f in stale:
            shutil.move(str(f), str(trash / f.relative_to(OUT).as_posix().replace("/", "__")))
        print(f"moved {len(stale)} stale file(s) to {trash}")
    print(f"built {len(pages) + 1} HTML pages into {OUT} (today={today})")


if __name__ == "__main__":
    main()
