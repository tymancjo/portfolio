"""Local portfolio management engine. Run with: uv run --extra local python local_engine/app.py"""

import json
import os
import shutil
import subprocess
import sys
from flask import (
    Flask, render_template, request, redirect, url_for,
    jsonify, stream_with_context, Response, send_from_directory,
)
from werkzeug.utils import secure_filename

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PHOTOS_DIR = os.path.join(ROOT, "photos")
ARTICLES_DIR = os.path.join(ROOT, "articles")
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}

app = Flask(__name__)
app.secret_key = "portfolio-local-dev"
app.template_folder = os.path.join(os.path.dirname(__file__), "templates")


def manifest_path(gallery_path):
    return os.path.join(gallery_path, "gallery.json")


def load_manifest(gallery_path):
    mp = manifest_path(gallery_path)
    if os.path.exists(mp):
        with open(mp, "r", encoding="utf-8") as f:
            return json.load(f)
    return None


def save_manifest(gallery_path, data):
    with open(manifest_path(gallery_path), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def get_all_photos(gallery_path):
    if not os.path.isdir(gallery_path):
        return []
    return sorted([
        f for f in os.listdir(gallery_path)
        if os.path.splitext(f)[1].lower() in ALLOWED_EXTENSIONS
    ])


def get_cover_url(gallery_rel, gallery_path):
    """Return /photos/... URL for the gallery's cover thumbnail."""
    if not os.path.isdir(gallery_path):
        return None
    manifest = load_manifest(gallery_path)
    cover = None
    if manifest:
        cover = manifest.get("cover")
        if not cover:
            visible = [p for p in manifest.get("photos", []) if not p.get("hidden")]
            if visible:
                cover = visible[0]["filename"]
    if not cover:
        files = get_all_photos(gallery_path)
        if files:
            cover = files[0]
    if not cover:
        return None
    thumb = os.path.join(gallery_path, "_thumbs", cover)
    rel = gallery_rel.replace(os.sep, "/")
    if os.path.exists(thumb):
        return f"/photos/{rel}/_thumbs/{cover}"
    return f"/photos/{rel}/{cover}"


def build_manifest_from_disk(gallery_path):
    existing = load_manifest(gallery_path) or {}
    files = get_all_photos(gallery_path)
    photos = [f for f in existing.get("photos", []) if f["filename"] in set(files)]
    existing_filenames = {p["filename"] for p in photos}
    next_order = max((p.get("order", 0) for p in photos), default=-1) + 1
    for f in files:
        if f not in existing_filenames:
            photos.append({"filename": f, "order": next_order, "title": None, "description": None, "hidden": False})
            next_order += 1
    return {
        "version": existing.get("version", 1),
        "title_override": existing.get("title_override"),
        "cover": existing.get("cover"),
        "photos": photos,
    }


GALLERIES_ORDER_FILE = os.path.join(PHOTOS_DIR, "_order.json")
ARTICLES_ORDER_FILE = os.path.join(ARTICLES_DIR, "_order.json")


def _load_order(path):
    if os.path.exists(path):
        try:
            with open(path, encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            pass
    return []


def _apply_order(items, order, key):
    pos = {v: i for i, v in enumerate(order)}
    max_pos = len(order)
    return sorted(items, key=lambda x: (pos.get(x[key], max_pos), x[key]))


def list_galleries():
    galleries = []
    for name in sorted(os.listdir(PHOTOS_DIR)):
        path = os.path.join(PHOTOS_DIR, name)
        if not os.path.isdir(path) or name.startswith(('.', '_')):
            continue
        sub_dirs = [d for d in os.listdir(path)
                    if os.path.isdir(os.path.join(path, d)) and not d.startswith(('.', '_'))]
        is_collection = bool(sub_dirs)
        cover_url = None
        if is_collection:
            count = sum(
                len([f for f in os.listdir(os.path.join(path, sd))
                     if os.path.splitext(f)[1].lower() in ALLOWED_EXTENSIONS])
                for sd in sub_dirs
            )
            for sd in sorted(sub_dirs):
                url = get_cover_url(f"{name}/{sd}", os.path.join(path, sd))
                if url:
                    cover_url = url
                    break
        else:
            count = len([f for f in os.listdir(path)
                         if os.path.splitext(f)[1].lower() in ALLOWED_EXTENSIONS])
            cover_url = get_cover_url(name, path)
        galleries.append({
            "id": name,
            "is_collection": is_collection,
            "count": count,
            "sub_dirs": sub_dirs,
            "cover_url": cover_url,
        })
    return _apply_order(galleries, _load_order(GALLERIES_ORDER_FILE), "id")


def list_articles():
    if not os.path.isdir(ARTICLES_DIR):
        return []
    articles = []
    for slug in sorted(os.listdir(ARTICLES_DIR)):
        path = os.path.join(ARTICLES_DIR, slug)
        if not os.path.isdir(path) or slug.startswith(('.',)):
            continue
        meta = {}
        info_path = os.path.join(path, "info.md")
        if os.path.exists(info_path):
            with open(info_path, encoding="utf-8") as f:
                raw = f.read()
            if raw.startswith("---"):
                parts = raw.split("---", 2)
                if len(parts) >= 3:
                    for line in parts[1].strip().splitlines():
                        if ":" in line:
                            k, _, v = line.partition(":")
                            meta[k.strip()] = v.strip()
        has_content = os.path.exists(os.path.join(path, "article.md"))
        articles.append({
            "slug": slug,
            "title": meta.get("title", slug),
            "date": meta.get("date", ""),
            "has_content": has_content,
            "hidden": meta.get("hidden", "false") == "true",
        })
    return _apply_order(articles, _load_order(ARTICLES_ORDER_FILE), "slug")


# --- Routes ---

@app.route("/")
def dashboard():
    return render_template("dashboard.html", galleries=list_galleries())


@app.route("/gallery/<gallery_id>")
def gallery_editor(gallery_id):
    gallery_rel = gallery_id.replace("__", os.sep)
    gallery_path = os.path.join(PHOTOS_DIR, gallery_rel)
    if not os.path.isdir(gallery_path):
        return "Gallery not found", 404

    sub_dirs = [d for d in os.listdir(gallery_path)
                if os.path.isdir(os.path.join(gallery_path, d)) and not d.startswith(('.', '_'))]
    if sub_dirs:
        subs = []
        for sd in sorted(sub_dirs):
            sp = os.path.join(gallery_path, sd)
            count = len([f for f in os.listdir(sp) if os.path.splitext(f)[1].lower() in ALLOWED_EXTENSIONS])
            subs.append({
                "id": sd,
                "full_id": f"{gallery_id}__{sd}",
                "count": count,
                "cover_url": get_cover_url(f"{gallery_rel}/{sd}", sp),
            })
        return render_template("collection_editor.html", gallery_id=gallery_id, subs=subs)

    manifest = build_manifest_from_disk(gallery_path)
    description = ""
    info_path = os.path.join(gallery_path, "info.md")
    if os.path.exists(info_path):
        with open(info_path, "r", encoding="utf-8") as f:
            description = f.read()

    gallery_url_rel = gallery_rel.replace(os.sep, "/")
    return render_template(
        "gallery_editor.html",
        gallery_id=gallery_id,
        manifest=manifest,
        description=description,
        thumb_prefix=f"/photos/{gallery_url_rel}/_thumbs/",
        photo_prefix=f"/photos/{gallery_url_rel}/",
    )


@app.route("/gallery/<gallery_id>/manifest", methods=["POST"])
def save_gallery_manifest(gallery_id):
    gallery_rel = gallery_id.replace("__", os.sep)
    gallery_path = os.path.join(PHOTOS_DIR, gallery_rel)
    save_manifest(gallery_path, request.get_json())
    return jsonify({"ok": True})


@app.route("/gallery/<path:gallery_id>/upload", methods=["POST"])
def upload_photos(gallery_id):
    gallery_rel = gallery_id.replace("__", os.sep)
    gallery_path = os.path.join(PHOTOS_DIR, gallery_rel)
    os.makedirs(gallery_path, exist_ok=True)
    saved = []
    for f in request.files.getlist("photos"):
        ext = os.path.splitext(f.filename)[1].lower()
        if ext in ALLOWED_EXTENSIONS:
            filename = secure_filename(f.filename)
            f.save(os.path.join(gallery_path, filename))
            saved.append(filename)
    return jsonify({"saved": saved})


@app.route("/gallery/<path:gallery_id>/photo/<filename>/delete", methods=["POST"])
def delete_photo(gallery_id, filename):
    gallery_rel = gallery_id.replace("__", os.sep)
    gallery_path = os.path.join(PHOTOS_DIR, gallery_rel)
    safe = secure_filename(filename)
    for path in (
        os.path.join(gallery_path, safe),
        os.path.join(gallery_path, "_thumbs", safe),
    ):
        if os.path.isfile(path):
            os.remove(path)
    manifest = load_manifest(gallery_path)
    if manifest:
        manifest["photos"] = [p for p in manifest.get("photos", []) if p["filename"] != filename]
        save_manifest(gallery_path, manifest)
    return jsonify({"ok": True})


@app.route("/gallery/<path:gallery_id>/photo/<filename>", methods=["POST"])
def update_photo_meta(gallery_id, filename):
    gallery_rel = gallery_id.replace("__", os.sep)
    gallery_path = os.path.join(PHOTOS_DIR, gallery_rel)
    data = request.get_json()
    manifest = build_manifest_from_disk(gallery_path)
    for p in manifest["photos"]:
        if p["filename"] == filename:
            p["title"] = data.get("title") or None
            p["description"] = data.get("description") or None
            p["hidden"] = bool(data.get("hidden", False))
            break
    save_manifest(gallery_path, manifest)
    return jsonify({"ok": True})


@app.route("/gallery/new", methods=["POST"])
def new_gallery():
    name = request.form.get("name", "").strip()
    if not name:
        return redirect(url_for("dashboard"))
    os.makedirs(os.path.join(PHOTOS_DIR, name), exist_ok=True)
    return redirect(url_for("gallery_editor", gallery_id=name))


@app.route("/gallery/<path:gallery_id>/new-sub", methods=["POST"])
def new_sub_gallery(gallery_id):
    gallery_rel = gallery_id.replace("__", os.sep)
    sub_name = request.form.get("name", "").strip()
    if sub_name:
        os.makedirs(os.path.join(PHOTOS_DIR, gallery_rel, sub_name), exist_ok=True)
    return redirect(url_for("gallery_editor", gallery_id=gallery_id))


@app.route("/gallery/<path:gallery_id>/delete", methods=["POST"])
def delete_gallery(gallery_id):
    gallery_rel = gallery_id.replace("__", os.sep)
    gallery_path = os.path.join(PHOTOS_DIR, gallery_rel)
    if os.path.isdir(gallery_path):
        shutil.rmtree(gallery_path)
    parts = gallery_rel.split(os.sep)
    if len(parts) > 1:
        return redirect(url_for("gallery_editor", gallery_id=parts[0]))
    return redirect(url_for("dashboard"))


@app.route("/gallery/<path:gallery_id>/description", methods=["POST"])
def save_description(gallery_id):
    gallery_rel = gallery_id.replace("__", os.sep)
    gallery_path = os.path.join(PHOTOS_DIR, gallery_rel)
    with open(os.path.join(gallery_path, "info.md"), "w", encoding="utf-8") as f:
        f.write(request.form.get("description", ""))
    return redirect(url_for("gallery_editor", gallery_id=gallery_id))


@app.route("/photos/<path:filename>")
def serve_photo(filename):
    return send_from_directory(PHOTOS_DIR, filename)


@app.route("/build", methods=["POST"])
def trigger_build():
    def run():
        proc = subprocess.Popen(
            [sys.executable, os.path.join(ROOT, "build.py")],
            cwd=ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        for line in proc.stdout:
            yield f"data: {line.rstrip()}\n\n"
        proc.wait()
        yield f"data: [done] exit code {proc.returncode}\n\n"
    return Response(stream_with_context(run()), mimetype="text/event-stream")


@app.route("/galleries/reorder", methods=["POST"])
def reorder_galleries():
    order = request.get_json()
    with open(GALLERIES_ORDER_FILE, "w", encoding="utf-8") as f:
        json.dump(order, f, ensure_ascii=False)
    return jsonify({"ok": True})


@app.route("/articles/reorder", methods=["POST"])
def reorder_articles():
    order = request.get_json()
    os.makedirs(ARTICLES_DIR, exist_ok=True)
    with open(ARTICLES_ORDER_FILE, "w", encoding="utf-8") as f:
        json.dump(order, f, ensure_ascii=False)
    return jsonify({"ok": True})


@app.route("/articles")
def articles_list():
    return render_template("articles_list.html", articles=list_articles())


@app.route("/article/new", methods=["POST"])
def new_article():
    slug = request.form.get("slug", "").strip().lower().replace(" ", "-")
    if not slug:
        return redirect(url_for("articles_list"))
    os.makedirs(os.path.join(ARTICLES_DIR, slug), exist_ok=True)
    return redirect(url_for("article_editor", slug=slug))


@app.route("/article/<slug>/delete", methods=["POST"])
def delete_article(slug):
    path = os.path.join(ARTICLES_DIR, slug)
    if os.path.isdir(path):
        shutil.rmtree(path)
    return redirect(url_for("articles_list"))


@app.route("/article/<slug>/upload", methods=["POST"])
def upload_article_media(slug):
    media_dir = os.path.join(ARTICLES_DIR, slug, "media")
    os.makedirs(media_dir, exist_ok=True)
    saved = []
    for f in request.files.getlist("photos"):
        ext = os.path.splitext(f.filename)[1].lower()
        if ext in ALLOWED_EXTENSIONS:
            filename = secure_filename(f.filename)
            f.save(os.path.join(media_dir, filename))
            saved.append({"filename": filename, "url": f"articles/{slug}/media/{filename}"})
    return jsonify({"saved": saved})


@app.route("/article-media/<slug>/<path:filename>")
def serve_article_media(slug, filename):
    return send_from_directory(os.path.join(ARTICLES_DIR, slug, "media"), filename)


@app.route("/articles/<slug>/media/<path:filename>")
def serve_article_media_static(slug, filename):
    return send_from_directory(os.path.join(ARTICLES_DIR, slug, "media"), filename)


@app.route("/article/<slug>/toggle-hidden", methods=["POST"])
def toggle_article_hidden(slug):
    article_path = os.path.join(ARTICLES_DIR, slug)
    info_md = os.path.join(article_path, "info.md")
    meta = {}
    raw = ""
    if os.path.exists(info_md):
        with open(info_md, encoding="utf-8") as f:
            raw = f.read()
        if raw.startswith("---"):
            parts = raw.split("---", 2)
            if len(parts) >= 3:
                for line in parts[1].strip().splitlines():
                    if ":" in line:
                        k, _, v = line.partition(":")
                        meta[k.strip()] = v.strip()
    now_hidden = meta.get("hidden", "false") == "true"
    meta["hidden"] = "false" if now_hidden else "true"
    lines = [f"{k}: {v}" for k, v in meta.items() if v]
    os.makedirs(article_path, exist_ok=True)
    with open(info_md, "w", encoding="utf-8") as f:
        f.write("---\n" + "\n".join(lines) + "\n---\n")
    return jsonify({"hidden": not now_hidden})


@app.route("/article/<slug>", methods=["GET", "POST"])
def article_editor(slug):
    article_path = os.path.join(ARTICLES_DIR, slug)
    os.makedirs(article_path, exist_ok=True)
    article_md = os.path.join(article_path, "article.md")
    info_md = os.path.join(article_path, "info.md")

    if request.method == "POST":
        with open(article_md, "w", encoding="utf-8") as f:
            f.write(request.form.get("content", ""))
        meta_lines = []
        for key in ("title", "date", "excerpt"):
            val = request.form.get(key, "").strip()
            if val:
                meta_lines.append(f"{key}: {val}")
        if request.form.get("hidden") == "on":
            meta_lines.append("hidden: true")
        if meta_lines:
            with open(info_md, "w", encoding="utf-8") as f:
                f.write("---\n" + "\n".join(meta_lines) + "\n---\n")
        return redirect(url_for("article_editor", slug=slug))

    content = open(article_md).read() if os.path.exists(article_md) else ""
    meta = {}
    if os.path.exists(info_md):
        with open(info_md) as f:
            raw = f.read()
        if raw.startswith("---"):
            parts = raw.split("---", 2)
            if len(parts) >= 3:
                for line in parts[1].strip().splitlines():
                    if ":" in line:
                        k, _, v = line.partition(":")
                        meta[k.strip()] = v.strip()

    return render_template("article_editor.html", slug=slug, content=content, meta=meta)


# Serve built portfolio for preview — must be last (catch-all)
@app.route("/index.html")
def serve_portfolio_index():
    return send_from_directory(ROOT, "index.html")


@app.route("/<path:filename>")
def serve_root_static(filename):
    filepath = os.path.join(ROOT, filename)
    if os.path.isfile(filepath):
        return send_from_directory(ROOT, filename)
    return "Not found", 404


def main():
    print("Portfolio local engine starting at http://127.0.0.1:5001")
    app.run(debug=True, host="127.0.0.1", port=5001)


if __name__ == "__main__":
    main()
