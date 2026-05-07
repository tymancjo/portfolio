import os
import markdown2
from PIL import Image
from datetime import datetime

# --- Configuration ---
PHOTOS_DIR = "photos"
OUTPUT_DIR = "."
INDEX_TEMPLATE_FILE = "index_template.html"
GALLERY_TEMPLATE_FILE = "gallery_template.html"
DEFAULT_GALLERY_DESCRIPTION = "Brak opisu dla tej galerii."
THUMB_SIZE = (800, 1200) # Max width/height for thumbnails
THUMB_DIR_NAME = "_thumbs"

def get_thumbnail_path(photo_path):
    """Ensures a thumbnail exists and returns its path."""
    dir_name = os.path.dirname(photo_path)
    base_name = os.path.basename(photo_path)
    thumb_dir = os.path.join(dir_name, THUMB_DIR_NAME)
    
    if not os.path.exists(thumb_dir):
        os.makedirs(thumb_dir)
    
    thumb_path = os.path.join(thumb_dir, base_name)
    
    # Check if thumbnail needs (re)generation
    if not os.path.exists(thumb_path) or os.path.getmtime(photo_path) > os.path.getmtime(thumb_path):
        try:
            with Image.open(photo_path) as img:
                # Use Image.LANCZOS for high-quality downsampling
                img.thumbnail(THUMB_SIZE, Image.Resampling.LANCZOS)
                img.save(thumb_path, quality=85, optimize=True)
                print(f"Generated thumbnail: {thumb_path}")
        except Exception as e:
            print(f"Error generating thumbnail for {photo_path}: {e}")
            return photo_path # Fallback to original
            
    return thumb_path

def load_template(template_path):
    with open(template_path, "r", encoding="utf-8") as f:
        return f.read()

def generate_gallery_page(gallery_id, gallery_title, photos, description, template):
    """Generates an HTML page for a single gallery using a template."""
    
    photos_html = []
    for photo in photos:
        thumb_path = get_thumbnail_path(photo)
        photos_html.append(f'<a href="{photo}" class="gallery-item"><img src="{thumb_path}" alt="{gallery_title}" loading="lazy"></a>')
    
    html_content = template.replace("{{ gallery_name }}", gallery_id)
    html_content = html_content.replace("{{ gallery_title }}", gallery_title)
    html_content = html_content.replace("{{ description }}", description)
    html_content = html_content.replace("{{ photos_html }}", "\n            ".join(photos_html))
    
    output_path = os.path.join(OUTPUT_DIR, f"{gallery_id}.html")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"Generated gallery page: {output_path}")

def build_portfolio():
    """Main function to build the entire portfolio."""

    if not os.path.exists(PHOTOS_DIR):
        print(f"Error: '{PHOTOS_DIR}' directory not found.")
        return

    index_template = load_template(INDEX_TEMPLATE_FILE)
    gallery_template = load_template(GALLERY_TEMPLATE_FILE)
    
    gallery_links_html = []
    
    # Iterate through subdirectories in PHOTOS_DIR (each is a gallery)
    # Filter out hidden dirs and the thumbnail dirs
    galleries = sorted([d for d in os.listdir(PHOTOS_DIR) 
                       if os.path.isdir(os.path.join(PHOTOS_DIR, d)) and not d.startswith((".", "_"))])

    for gallery_dir in galleries:
        gallery_path = os.path.join(PHOTOS_DIR, gallery_dir)
        print(f"Processing gallery: {gallery_dir}")
        
        # Read gallery description from info.md
        description = DEFAULT_GALLERY_DESCRIPTION
        info_md_path = os.path.join(gallery_path, "info.md")
        if os.path.exists(info_md_path):
            with open(info_md_path, "r", encoding="utf-8") as f:
                description = markdown2.markdown(f.read())
        
        photos_in_gallery_unsorted = []
        for photo_name in os.listdir(gallery_path):
            if photo_name.lower().endswith((".png", ".jpg", ".jpeg", ".gif", ".webp")):
                full_path = os.path.join(gallery_path, photo_name)
                photos_in_gallery_unsorted.append(full_path)
        
        # Sort photos by modification time (newest first)
        photos_in_gallery = sorted(photos_in_gallery_unsorted, key=os.path.getmtime, reverse=True)
        
        if photos_in_gallery:
            gallery_title = gallery_dir.replace('_', ' ').title()
            if gallery_dir[0:2].isdigit() and gallery_dir[2] == '_':
                gallery_title = gallery_dir[3:].replace('_', ' ').title()

            generate_gallery_page(gallery_dir, gallery_title, photos_in_gallery, description, gallery_template)
            
            # Add link to index.html
            cover_photo = photos_in_gallery[0]
            cover_thumb = get_thumbnail_path(cover_photo)
            
            gallery_links_html.append(f"""
        <a href="{gallery_dir}.html" class="gallery-card">
            <div class="img-wrapper">
                <img src="{cover_thumb}" alt="{gallery_title} cover" loading="lazy">
            </div>
            <h2>{gallery_title}</h2>
            <div class="description">{description}</div>
        </a>""")
        else:
            print(f"No photos found in gallery: {gallery_dir}")

    # Finalize index.html
    index_html_content = index_template.replace("{{ gallery_links }}", "\n".join(gallery_links_html))
    index_html_path = os.path.join(OUTPUT_DIR, "index.html")
    
    with open(index_html_path, "w", encoding="utf-8") as f:
        f.write(index_html_content)
    
    print(f"Updated {index_html_path}")
    print("Portfolio build complete.")

if __name__ == "__main__":
    build_portfolio()
