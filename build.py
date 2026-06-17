import json
import os
import markdown2
from PIL import Image
from datetime import datetime

# --- Configuration ---
PHOTOS_DIR = "photos"
ARTICLES_DIR = "articles"
SITE_DIR = "site"
OUTPUT_DIR = "."
INDEX_TEMPLATE_FILE = "index_template.html"
GALLERY_TEMPLATE_FILE = "gallery_template.html"
COLLECTION_TEMPLATE_FILE = "collection_template.html"
ARTICLE_TEMPLATE_FILE = "article_template.html"
ARTICLES_INDEX_TEMPLATE_FILE = "articles_index_template.html"
MANIFEST_FILE = "gallery.json"
DEFAULT_DESCRIPTION = "Brak opisu dla tej galerii."
THUMB_SIZE = (800, 1200)
THUMB_DIR_NAME = "_thumbs"


def get_thumbnail_path(photo_path):
    dir_name = os.path.dirname(photo_path)
    base_name = os.path.basename(photo_path)
    thumb_dir = os.path.join(dir_name, THUMB_DIR_NAME)

    if not os.path.exists(thumb_dir):
        os.makedirs(thumb_dir)

    thumb_path = os.path.join(thumb_dir, base_name)

    if not os.path.exists(thumb_path) or os.path.getmtime(photo_path) > os.path.getmtime(thumb_path):
        try:
            with Image.open(photo_path) as img:
                img.thumbnail(THUMB_SIZE, Image.Resampling.LANCZOS)
                img.save(thumb_path, quality=85, optimize=True)
                print(f"  Thumbnail: {thumb_path}")
        except Exception as e:
            print(f"  Error generating thumbnail for {photo_path}: {e}")
            return photo_path

    return thumb_path


def load_template(template_path):
    with open(template_path, "r", encoding="utf-8") as f:
        return f.read()


def clean_title(dir_name):
    if len(dir_name) > 2 and dir_name[:2].isdigit() and dir_name[2] == '_':
        return dir_name[3:].replace('_', ' ').title()
    return dir_name.replace('_', ' ').title()


def load_description(dir_path):
    info_md_path = os.path.join(dir_path, "info.md")
    if os.path.exists(info_md_path):
        with open(info_md_path, "r", encoding="utf-8") as f:
            return markdown2.markdown(f.read())
    return DEFAULT_DESCRIPTION


def load_bio(site_dir):
    bio_path = os.path.join(site_dir, "bio.md")
    if os.path.exists(bio_path):
        with open(bio_path, "r", encoding="utf-8") as f:
            return markdown2.markdown(f.read())
    return ""


def get_photos(dir_path):
    photos = [
        os.path.join(dir_path, f)
        for f in os.listdir(dir_path)
        if f.lower().endswith((".png", ".jpg", ".jpeg", ".gif", ".webp"))
    ]
    return sorted(photos, key=os.path.getmtime, reverse=True)


def load_manifest(dir_path):
    manifest_path = os.path.join(dir_path, MANIFEST_FILE)
    if not os.path.exists(manifest_path):
        return None
    with open(manifest_path, "r", encoding="utf-8") as f:
        return json.load(f)


def get_photos_ordered(dir_path):
    """Return list of photo dicts [{path, filename, title, description}], ordered by manifest or mtime."""
    manifest = load_manifest(dir_path)

    all_files = {
        f for f in os.listdir(dir_path)
        if f.lower().endswith((".png", ".jpg", ".jpeg", ".gif", ".webp"))
    }

    if manifest is None:
        # Legacy mode: mtime sort, no metadata
        paths = sorted(
            [os.path.join(dir_path, f) for f in all_files],
            key=os.path.getmtime, reverse=True
        )
        return [{"path": p, "filename": os.path.basename(p), "title": None, "description": None}
                for p in paths]

    # Manifest mode: order by manifest, append unlisted files at end
    manifest_entries = {e["filename"]: e for e in manifest.get("photos", [])}
    ordered = sorted(
        [e for e in manifest.get("photos", []) if e["filename"] in all_files and not e.get("hidden", False)],
        key=lambda e: e.get("order", 9999)
    )
    unlisted = sorted(all_files - manifest_entries.keys())

    result = []
    for entry in ordered:
        result.append({
            "path": os.path.join(dir_path, entry["filename"]),
            "filename": entry["filename"],
            "title": entry.get("title") or None,
            "description": entry.get("description") or None,
        })
    for filename in unlisted:
        result.append({
            "path": os.path.join(dir_path, filename),
            "filename": filename,
            "title": None,
            "description": None,
        })
    return result


def get_cover_path(dir_path, photos_ordered):
    """Return path for gallery cover: manifest cover field, or first photo."""
    manifest = load_manifest(dir_path)
    if manifest and manifest.get("cover"):
        cover_path = os.path.join(dir_path, manifest["cover"])
        if os.path.exists(cover_path):
            return cover_path
    if photos_ordered:
        return photos_ordered[0]["path"]
    return None


def is_collection(gallery_path):
    return any(
        os.path.isdir(os.path.join(gallery_path, d)) and not d.startswith(('.', '_'))
        for d in os.listdir(gallery_path)
    )


def pluralize_photos(count):
    if count == 1:
        return "zdjęcie"
    if 2 <= count % 10 <= 4 and not (12 <= count % 100 <= 14):
        return "zdjęcia"
    return "zdjęć"


def make_gallery_card(href, cover_thumb, title, description, photo_count):
    label = f"{photo_count} {pluralize_photos(photo_count)}"
    return f"""        <a href="{href}" class="gallery-card">
            <div class="img-wrapper">
                <img src="{cover_thumb}" alt="{title} cover" loading="lazy">
            </div>
            <h2>{title}</h2>
            <div class="description">{description}</div>
            <span class="photo-count">{label}</span>
        </a>"""


def make_photo_anchor(photo, gallery_title):
    """Return HTML anchor for a single photo in the masonry grid."""
    stem = os.path.splitext(photo["filename"])[0]
    title_attr = photo["title"] or ""
    desc_attr = photo["description"] or ""
    thumb = get_thumbnail_path(photo["path"])
    return (
        f'<a href="{photo["path"]}" class="gallery-item" '
        f'id="{stem}" '
        f'data-title="{title_attr}" '
        f'data-description="{desc_attr}">'
        f'<img src="{thumb}" alt="{gallery_title}" loading="lazy"></a>'
    )


def generate_gallery_page(gallery_id, gallery_title, photos, description, template,
                           breadcrumb_html="", year=2025):
    """Generate HTML page for a flat photo gallery. photos is list[dict] from get_photos_ordered()."""
    photos_html = [make_photo_anchor(p, gallery_title) for p in photos]

    html = template
    html = html.replace("{{ gallery_title }}", gallery_title)
    html = html.replace("{{ gallery_name }}", gallery_id)
    html = html.replace("{{ description }}", description)
    html = html.replace("{{ photos_html }}", "\n            ".join(photos_html))
    html = html.replace("{{ breadcrumb_html }}", breadcrumb_html)
    html = html.replace("{{ year }}", str(year))

    output_path = os.path.join(OUTPUT_DIR, f"{gallery_id}.html")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"  → {output_path}")


def generate_collection_page(gallery_id, gallery_title, description, subgallery_links_html,
                              template, year=2025):
    html = template
    html = html.replace("{{ collection_title }}", gallery_title)
    html = html.replace("{{ description }}", description)
    html = html.replace("{{ subgallery_links }}", "\n".join(subgallery_links_html))
    html = html.replace("{{ year }}", str(year))

    output_path = os.path.join(OUTPUT_DIR, f"{gallery_id}.html")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"  → {output_path}")


def build_changelog_section(galleries_data, max_entries=5):
    """Return full section HTML for 'Ostatnio dodane', or empty string if no data."""
    if not galleries_data:
        return ""
    recent = sorted(galleries_data, key=lambda g: g["mtime"], reverse=True)[:max_entries]
    items = []
    for g in recent:
        date_str = datetime.fromtimestamp(g["mtime"]).strftime("%d.%m.%Y")
        label = f"{g['count']} {pluralize_photos(g['count'])}"
        items.append(
            f'<a href="{g["href"]}" class="changelog-card">'
            f'<span class="changelog-title">{g["title"]}</span>'
            f'<span class="changelog-meta">{date_str} &mdash; {label}</span>'
            f'</a>'
        )
    inner = "\n".join(items)
    return (
        f'<section class="latest-changes">'
        f'<div class="section-inner">'
        f'<h2 class="section-heading">Ostatnio dodane</h2>'
        f'<div class="changelog-list">{inner}</div>'
        f'</div></section>'
    )


def load_article_meta(dir_path):
    """Parse YAML front matter from articles/<slug>/info.md. Returns dict with title, date, excerpt."""
    info_path = os.path.join(dir_path, "info.md")
    meta = {"title": None, "date": None, "excerpt": "", "hidden": "false"}
    if not os.path.exists(info_path):
        return meta
    with open(info_path, "r", encoding="utf-8") as f:
        content = f.read()
    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            for line in parts[1].strip().splitlines():
                if ":" in line:
                    key, _, val = line.partition(":")
                    meta[key.strip()] = val.strip()
    return meta


def preprocess_article_markdown(text):
    """Convert ::photo[path]{caption="..."} shorthand to <figure> HTML."""
    import re
    pattern = r'::photo\[([^\]]+)\]\{caption="([^"]*)"\}'
    def replace(m):
        src, caption = m.group(1), m.group(2)
        return f'<figure><img src="{src}" alt="{caption}"><figcaption>{caption}</figcaption></figure>'
    return re.sub(pattern, replace, text)


def generate_article_page(article_id, meta, content_html, template, year):
    html = template
    html = html.replace("{{ article_title }}", meta.get("title") or clean_title(article_id))
    html = html.replace("{{ article_date }}", meta.get("date") or "")
    html = html.replace("{{ article_content_html }}", content_html)
    html = html.replace("{{ year }}", str(year))

    output_path = os.path.join(OUTPUT_DIR, f"{article_id}.html")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"  → {output_path}")


def generate_articles_index_page(articles, template, year):
    """articles: list of {id, title, date, excerpt}"""
    cards = []
    for a in articles:
        cards.append(
            f'<a href="{a["id"]}.html" class="article-card">'
            f'<h2>{a["title"]}</h2>'
            f'<span class="article-date">{a["date"]}</span>'
            f'<p class="article-excerpt">{a["excerpt"]}</p>'
            f'</a>'
        )
    html = template
    html = html.replace("{{ article_cards_html }}", "\n".join(cards))
    html = html.replace("{{ year }}", str(year))

    output_path = os.path.join(OUTPUT_DIR, "articles.html")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"  → {output_path}")


def build_portfolio():
    if not os.path.exists(PHOTOS_DIR):
        print(f"Error: '{PHOTOS_DIR}' directory not found.")
        return

    index_template = load_template(INDEX_TEMPLATE_FILE)
    gallery_template = load_template(GALLERY_TEMPLATE_FILE)
    collection_template = load_template(COLLECTION_TEMPLATE_FILE)

    current_year = datetime.now().year
    gallery_links_html = []
    galleries_data = []  # for changelog

    galleries = sorted([
        d for d in os.listdir(PHOTOS_DIR)
        if os.path.isdir(os.path.join(PHOTOS_DIR, d)) and not d.startswith(('.', '_'))
    ])

    for gallery_dir in galleries:
        gallery_path = os.path.join(PHOTOS_DIR, gallery_dir)
        gallery_title = clean_title(gallery_dir)

        # title_override support
        manifest = load_manifest(gallery_path)
        if manifest and manifest.get("title_override"):
            gallery_title = manifest["title_override"]

        description = load_description(gallery_path)
        print(f"Processing: {gallery_dir}")

        if is_collection(gallery_path):
            sub_dirs = sorted([
                d for d in os.listdir(gallery_path)
                if os.path.isdir(os.path.join(gallery_path, d)) and not d.startswith(('.', '_'))
            ])

            subgallery_links_html = []
            collection_cover_thumb = None
            total_count = 0
            latest_mtime = 0

            for sub_dir in sub_dirs:
                sub_path = os.path.join(gallery_path, sub_dir)
                sub_title = clean_title(sub_dir)
                sub_manifest = load_manifest(sub_path)
                if sub_manifest and sub_manifest.get("title_override"):
                    sub_title = sub_manifest["title_override"]
                sub_description = load_description(sub_path)
                sub_id = f"{gallery_dir}__{sub_dir}"
                sub_photos = get_photos_ordered(sub_path)

                if not sub_photos:
                    print(f"  Skipping empty sub-gallery: {sub_dir}")
                    continue

                total_count += len(sub_photos)
                cover_path = get_cover_path(sub_path, sub_photos)
                cover_thumb = get_thumbnail_path(cover_path)
                mtime = os.path.getmtime(cover_path)
                if mtime > latest_mtime:
                    latest_mtime = mtime
                if collection_cover_thumb is None:
                    collection_cover_thumb = cover_thumb

                breadcrumb = (
                    f'<div class="breadcrumb">'
                    f'<a href="{gallery_dir}.html">← {gallery_title}</a>'
                    f'</div>'
                )
                generate_gallery_page(sub_id, sub_title, sub_photos, sub_description,
                                      gallery_template, breadcrumb_html=breadcrumb,
                                      year=current_year)
                subgallery_links_html.append(make_gallery_card(
                    f"{sub_id}.html", cover_thumb, sub_title, sub_description, len(sub_photos)
                ))

            if subgallery_links_html:
                generate_collection_page(gallery_dir, gallery_title, description,
                                         subgallery_links_html, collection_template,
                                         year=current_year)
                gallery_links_html.append(make_gallery_card(
                    f"{gallery_dir}.html", collection_cover_thumb,
                    gallery_title, description, total_count
                ))
                galleries_data.append({
                    "title": gallery_title,
                    "href": f"{gallery_dir}.html",
                    "mtime": latest_mtime,
                    "count": total_count,
                })
            else:
                print(f"  No sub-galleries with photos — skipping collection: {gallery_dir}")

        else:
            photos = get_photos_ordered(gallery_path)
            if not photos:
                print(f"  No photos found — skipping: {gallery_dir}")
                continue

            generate_gallery_page(gallery_dir, gallery_title, photos, description,
                                   gallery_template, year=current_year)
            cover_path = get_cover_path(gallery_path, photos)
            cover_thumb = get_thumbnail_path(cover_path)
            gallery_links_html.append(make_gallery_card(
                f"{gallery_dir}.html", cover_thumb, gallery_title, description, len(photos)
            ))
            galleries_data.append({
                "title": gallery_title,
                "href": f"{gallery_dir}.html",
                "mtime": os.path.getmtime(cover_path),
                "count": len(photos),
            })

    # Bio + changelog for index
    bio_html = load_bio(SITE_DIR)
    changelog_section_html = build_changelog_section(galleries_data)

    # Write index.html
    index_html = index_template.replace("{{ gallery_links }}", "\n".join(gallery_links_html))
    index_html = index_html.replace("{{ year }}", str(current_year))
    index_html = index_html.replace("{{ bio_html }}", bio_html)
    index_html = index_html.replace("{{ changelog_section_html }}", changelog_section_html)
    index_html_path = os.path.join(OUTPUT_DIR, "index.html")
    with open(index_html_path, "w", encoding="utf-8") as f:
        f.write(index_html)
    print(f"\nUpdated {index_html_path}")

    # Articles (optional)
    if os.path.exists(ARTICLES_DIR) and os.path.exists(ARTICLE_TEMPLATE_FILE):
        article_template = load_template(ARTICLE_TEMPLATE_FILE)
        articles_index_template_exists = os.path.exists(ARTICLES_INDEX_TEMPLATE_FILE)
        articles_index_template = load_template(ARTICLES_INDEX_TEMPLATE_FILE) if articles_index_template_exists else None
        article_slugs = sorted([
            d for d in os.listdir(ARTICLES_DIR)
            if os.path.isdir(os.path.join(ARTICLES_DIR, d)) and not d.startswith(('.', '_'))
        ])
        articles_list = []
        for slug in article_slugs:
            article_path = os.path.join(ARTICLES_DIR, slug)
            meta = load_article_meta(article_path)
            if meta.get("hidden") == "true":
                continue
            article_md_path = os.path.join(article_path, "article.md")
            if not os.path.exists(article_md_path):
                continue
            with open(article_md_path, "r", encoding="utf-8") as f:
                raw = f.read()
            raw = preprocess_article_markdown(raw)
            content_html = markdown2.markdown(raw, extras=["fenced-code-blocks", "tables"])
            generate_article_page(slug, meta, content_html, article_template, current_year)
            articles_list.append({
                "id": slug,
                "title": meta.get("title") or clean_title(slug),
                "date": meta.get("date") or "",
                "excerpt": meta.get("excerpt") or "",
            })
        if articles_index_template and articles_list:
            generate_articles_index_page(articles_list, articles_index_template, current_year)

    print("Build complete.")


if __name__ == "__main__":
    build_portfolio()
