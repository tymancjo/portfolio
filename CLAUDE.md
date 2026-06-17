# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Build

```bash
# Install dependencies (uv preferred, Python 3.12)
uv sync

# Regenerate all HTML + missing thumbnails
python build.py
```

No test suite, no lint step. `build.py` is the only build artifact.

## Architecture

Static photography portfolio. Python generates HTML; the server serves only static files.

### How it works

1. `build.py` scans `photos/` for gallery directories
2. For each directory it renders HTML via one of three templates, then writes it to the repo root
3. Thumbnails (max 800×1200 LANCZOS) are auto-generated into `photos/<gallery>/_thumbs/` and cached by mtime
4. `index.html` is regenerated last with cards linking to each gallery

### Directory conventions

- `photos/<NN_name>/` — flat gallery (images directly inside → `gallery_template.html`)
- `photos/<NN_name>/<sub>/` — collection + sub-galleries (`collection_template.html` + `gallery_template.html` with breadcrumb)
- `photos/<any>/info.md` — gallery description, converted from Markdown to HTML at build time
- Leading `NN_` prefix on directory names is stripped for display titles (`clean_title()`)

### Output filenames

- Flat gallery `photos/01_foo/` → `01_foo.html`
- Sub-gallery `photos/00_bar/00_baz/` → `00_bar__00_baz.html` (double underscore separator)
- Collection index `photos/00_bar/` → `00_bar.html`

### Templates

| File | Used for |
|---|---|
| `index_template.html` | Landing page |
| `gallery_template.html` | Flat gallery or sub-gallery |
| `collection_template.html` | Collection (parent of sub-galleries) |

Template variables use `{{ var }}` syntax replaced by plain `str.replace()` — not Jinja.

### Frontend

- `style.css` — CSS Variables, Flexbox/Grid, masonry layout for galleries
- `main.js` — vanilla JS lightbox with keyboard (←/→/Esc) and touch swipe navigation
- Fonts: Playfair Display (headings) + Inter (body), loaded from Google Fonts

### Deployment

Push to `master` → GitHub Pages serves the static files. `.nojekyll` prevents Jekyll processing (required for `_thumbs` directories to be served).
