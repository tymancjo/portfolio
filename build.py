import os
import markdown2
from PIL import Image
from datetime import datetime

# --- Configuration ---
PHOTOS_DIR = "photos"
OUTPUT_DIR = "."
INDEX_TEMPLATE_FILE = "index_template.html"
GALLERY_TEMPLATE_FILE = "gallery_template.html"
COLLECTION_TEMPLATE_FILE = "collection_template.html"
DEFAULT_DESCRIPTION = "Brak opisu dla tej galerii."
THUMB_SIZE = (800, 1200)
THUMB_DIR_NAME = "_thumbs"


def get_thumbnail_path(photo_path):
    """Ensures a thumbnail exists and returns its path."""
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
    """Convert directory name to human-readable title, stripping leading NN_ prefix."""
    if len(dir_name) > 2 and dir_name[:2].isdigit() and dir_name[2] == '_':
        return dir_name[3:].replace('_', ' ').title()
    return dir_name.replace('_', ' ').title()


def load_description(dir_path):
    """Load and convert info.md to HTML, or return default."""
    info_md_path = os.path.join(dir_path, "info.md")
    if os.path.exists(info_md_path):
        with open(info_md_path, "r", encoding="utf-8") as f:
            return markdown2.markdown(f.read())
    return DEFAULT_DESCRIPTION


def get_photos(dir_path):
    """Return list of photo paths in dir_path, sorted newest first."""
    photos = [
        os.path.join(dir_path, f)
        for f in os.listdir(dir_path)
        if f.lower().endswith((".png", ".jpg", ".jpeg", ".gif", ".webp"))
    ]
    return sorted(photos, key=os.path.getmtime, reverse=True)


def is_collection(gallery_path):
    """Returns True if gallery_path contains sub-gallery folders."""
    return any(
        os.path.isdir(os.path.join(gallery_path, d)) and not d.startswith(('.', '_'))
        for d in os.listdir(gallery_path)
    )


def pluralize_photos(count):
    """Return correctly inflected Polish noun for photo count."""
    if count == 1:
        return "zdjęcie"
    if 2 <= count % 10 <= 4 and not (12 <= count % 100 <= 14):
        return "zdjęcia"
    return "zdjęć"


def make_gallery_card(href, cover_thumb, title, description, photo_count):
    """Return HTML for a single gallery card."""
    label = f"{photo_count} {pluralize_photos(photo_count)}"
    return f"""        <a href="{href}" class="gallery-card">
            <div class="img-wrapper">
                <img src="{cover_thumb}" alt="{title} cover" loading="lazy">
            </div>
            <h2>{title}</h2>
            <div class="description">{description}</div>
            <span class="photo-count">{label}</span>
        </a>"""


def generate_gallery_page(gallery_id, gallery_title, photos, description, template,
                           breadcrumb_html="", year=2025):
    """Generate an HTML page for a flat photo gallery."""
    photos_html = [
        f'<a href="{photo}" class="gallery-item">'
        f'<img src="{get_thumbnail_path(photo)}" alt="{gallery_title}" loading="lazy"></a>'
        for photo in photos
    ]

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
    """Generate an HTML page for a collection (gallery with sub-galleries)."""
    html = template
    html = html.replace("{{ collection_title }}", gallery_title)
    html = html.replace("{{ description }}", description)
    html = html.replace("{{ subgallery_links }}", "\n".join(subgallery_links_html))
    html = html.replace("{{ year }}", str(year))

    output_path = os.path.join(OUTPUT_DIR, f"{gallery_id}.html")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"  → {output_path}")


def build_portfolio():
    """Main function to build the entire portfolio."""
    if not os.path.exists(PHOTOS_DIR):
        print(f"Error: '{PHOTOS_DIR}' directory not found.")
        return

    index_template = load_template(INDEX_TEMPLATE_FILE)
    gallery_template = load_template(GALLERY_TEMPLATE_FILE)
    collection_template = load_template(COLLECTION_TEMPLATE_FILE)

    current_year = datetime.now().year
    gallery_links_html = []

    galleries = sorted([
        d for d in os.listdir(PHOTOS_DIR)
        if os.path.isdir(os.path.join(PHOTOS_DIR, d)) and not d.startswith(('.', '_'))
    ])

    for gallery_dir in galleries:
        gallery_path = os.path.join(PHOTOS_DIR, gallery_dir)
        gallery_title = clean_title(gallery_dir)
        description = load_description(gallery_path)
        print(f"Processing: {gallery_dir}")

        if is_collection(gallery_path):
            # --- Collection: folder contains sub-gallery dirs ---
            sub_dirs = sorted([
                d for d in os.listdir(gallery_path)
                if os.path.isdir(os.path.join(gallery_path, d)) and not d.startswith(('.', '_'))
            ])

            subgallery_links_html = []
            collection_cover_thumb = None
            total_count = 0

            for sub_dir in sub_dirs:
                sub_path = os.path.join(gallery_path, sub_dir)
                sub_title = clean_title(sub_dir)
                sub_description = load_description(sub_path)
                sub_id = f"{gallery_dir}__{sub_dir}"
                sub_photos = get_photos(sub_path)

                if not sub_photos:
                    print(f"  Skipping empty sub-gallery: {sub_dir}")
                    continue

                total_count += len(sub_photos)
                cover_thumb = get_thumbnail_path(sub_photos[0])
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
            else:
                print(f"  No sub-galleries with photos — skipping collection: {gallery_dir}")

        else:
            # --- Flat gallery: folder contains photos directly ---
            photos = get_photos(gallery_path)
            if not photos:
                print(f"  No photos found — skipping: {gallery_dir}")
                continue

            generate_gallery_page(gallery_dir, gallery_title, photos, description,
                                   gallery_template, year=current_year)
            cover_thumb = get_thumbnail_path(photos[0])
            gallery_links_html.append(make_gallery_card(
                f"{gallery_dir}.html", cover_thumb, gallery_title, description, len(photos)
            ))

    # Write index.html
    index_html = index_template.replace("{{ gallery_links }}", "\n".join(gallery_links_html))
    index_html = index_html.replace("{{ year }}", str(current_year))
    index_html_path = os.path.join(OUTPUT_DIR, "index.html")
    with open(index_html_path, "w", encoding="utf-8") as f:
        f.write(index_html)

    print(f"\nUpdated {index_html_path}")
    print("Build complete.")


if __name__ == "__main__":
    build_portfolio()
