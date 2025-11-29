import os
import markdown2 # Now safe to import directly

# --- Configuration ---
PHOTOS_DIR = "photos"
OUTPUT_DIR = "." # Output HTML files in the root directory
GALLERY_TEMPLATE_FILE = "gallery_template.html"
INDEX_TEMPLATE_FILE = "index_template.html" # Assuming we'll generate the main index.html
DEFAULT_GALLERY_DESCRIPTION = "Brak opisu dla tej galerii."

def generate_gallery_page(gallery_name, photos, description):
    """Generates an HTML page for a single gallery."""
    # This function will be expanded to read a template and populate it
    # For now, it creates a very basic HTML structure
    html_content = f"""
<!DOCTYPE html>
<html lang="pl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Fotografia Tymancja - {gallery_name}</title>
    <link rel="stylesheet" href="style.css">
</head>
<body>
    <header>
        <h1>Fotografia Tymancja - {gallery_name}</h1>
        <p class="back-to-home"><a href="index.html">start</a></p>
        <p>{description}</p>
    </header>

    <main class="gallery-grid">
        {"\n".join([f'<a href="{p}" class="gallery-item"><img src="{p}" alt="{gallery_name} photo"></a>' for p in photos])}
    </main>

    <footer>
        <p>&copy; 2025 Fotografia Tymancja</p>
    </footer>

    <script src="main.js"></script>
</body>
</html>
    """
    with open(os.path.join(OUTPUT_DIR, f"{gallery_name}.html"), "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"Generated gallery page: {gallery_name}.html")

def build_portfolio():
    """Main function to build the entire portfolio."""

    if not os.path.exists(PHOTOS_DIR):
        print(f"Error: '{PHOTOS_DIR}' directory not found.")
        return

    gallery_links_html = []
    
    # Iterate through subdirectories in PHOTOS_DIR (each is a gallery)
    for gallery_dir in sorted(os.listdir(PHOTOS_DIR)):
        gallery_path = os.path.join(PHOTOS_DIR, gallery_dir)
        if os.path.isdir(gallery_path):
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
            
            # Generate individual gallery page
            if photos_in_gallery:
                generate_gallery_page(gallery_dir, photos_in_gallery, description)
                # Add link to index.html
                # For now, just a simple link, will be a card later
                first_photo = photos_in_gallery[0] # Newest photo is the cover
                gallery_links_html.append(f"""
        <a href="{gallery_dir}.html" class="gallery-card">
            <img src="{first_photo}" alt="{gallery_dir} cover">
            <h2>{gallery_dir.replace('_', ' ').title()}</h2>
            <p>{description}</p>
        </a>""")
            else:
                print(f"No photos found in gallery: {gallery_dir}")

    # Update index.html with gallery links
    index_html_path = os.path.join(OUTPUT_DIR, "index.html")
    if os.path.exists(index_html_path):
        with open(index_html_path, "r", encoding="utf-8") as f:
            index_content = f.read()
        
        # This is a simple replacement strategy. A proper templating system would be better.
        # But for static HTML, this might suffice for now.
        new_gallery_links_section = f"""<main id="gallery-links">
{'\n'.join(gallery_links_html)}
    </main>"""
        old_gallery_links_section_start = index_content.find('<main id="gallery-links">')
        old_gallery_links_section_end = index_content.find('</main>', old_gallery_links_section_start) + len('</main>')
        
        if old_gallery_links_section_start != -1 and old_gallery_links_section_end != -1:
            index_content = index_content[:old_gallery_links_section_start] + \
                            new_gallery_links_section + \
                            index_content[old_gallery_links_section_end:]
            
            with open(index_html_path, "w", encoding="utf-8") as f:
                f.write(index_content)
            print("Updated index.html with gallery links.")
        else:
            print("Warning: Could not find <main id='gallery-links'> section in index.html to update.")
    else:
        print(f"Error: index.html not found at {index_html_path}")

    print("Portfolio build complete.")

if __name__ == "__main__":
    build_portfolio()
