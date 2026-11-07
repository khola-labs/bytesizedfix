# Byte-Sized Fix: course hub

The static website for the free Byte-Sized Fix **DSA + System Design** course (Hinglish narration, English on-screen, Python code).
It's plain HTML, CSS and vanilla JS: no framework, no tracking, no cookies, no external scripts.

- `data/roadmap.json` is the source of truth: 100 lessons, 19 modules, practice links and sources.
- `build.py` renders every page into `docs/`. It needs only the Python 3 standard library.
- `src/` holds the static assets (CSS, JS, Kursor images, favicon), which are copied into `docs/assets/`.
- `docs/` is the generated site, ready for GitHub Pages ("Deploy from a branch → /docs").
- `tools/check_links.py` is the internal link checker. `tools/make_assets.py` rebuilds the images from `src/kursor_source.png` (needs Pillow).

## Rebuild

```sh
python3 build.py                     # writes docs/
python3 tools/check_links.py         # every internal link + #anchor must resolve
cd docs && python3 -m http.server 8000   # preview at http://localhost:8000/
```

`python3 build.py --today 2026-12-01` previews how the "Coming up" list and the date badges will look on another day.
Badges are worked out at build time, so rebuild and push after each release.
Generated files that are no longer produced, such as a removed lesson, are moved to `~/.Trash`. Nothing is deleted.

## Mark a lesson as released

Edit the lesson in `data/roadmap.json`:

| field | effect |
|---|---|
| `"video_id": "abc123XYZ"` | The lesson becomes **Out now**. Its page gets a click-to-load YouTube embed (youtube-nocookie) and a "Watch on YouTube" link. |
| `"short_id": "oPQW__hyUN0"` | Adds a vertical Short player. The lesson shows **Short out now** and the full-lesson date. |
| `"short_label": "..."` | Heading over the Short (C02 uses "Pilot / short version"). |
| `"code_alternatives": [{"lang": "C++", "title": "...", "url": "..."}]` | Adds a "Code in other languages" section. The roadmap had none yet. |
| `release_week`, `release_slot` | Sets the date. Week 1 starts Monday 9 Nov 2026 (`meta.site.week1_monday`), and the slot is a weekday (`Tue` or `Fri`). |

Then run `python3 build.py`, commit and push.

The roadmap v1 data used Tue for System Design and Fri for DSA. In this copy the slots are swapped to match the decision "Tue DSA, Fri SD" (see `meta.site.slot_note`).
If you copy a newer roadmap.json over this one, keep `meta.site`, `video_id`, `short_id`, `short_label` and the swapped slots.

## Deploy (GitHub Pages)

1. Create the repo `khola-labs/bytesizedfix` and push this folder (`main` branch).
2. Go to Settings → Pages → Build and deployment → "Deploy from a branch" → `main` / `/docs`.
3. The site goes live at https://khola-labs.github.io/bytesizedfix/. All links are relative, so it also works under a custom domain. The canonical URL, the sitemap and the OG image use `meta.site.base_url`, so change that if the URL changes.

`docs/.nojekyll` turns off Jekyll processing. `404.html` works out the base path at runtime.

## Privacy

The site loads no third-party code. YouTube loads only after a visitor presses play (privacy-enhanced domain).
Progress ticks live in `localStorage` (key `bsf-course-progress-v1`) on the visitor's device. If storage is blocked, the site still works and shows a note that ticks won't be saved.
