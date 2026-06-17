"""Local portfolio management engine. Run with: uv run --extra local python local_engine/app.py"""

import json
import os
import subprocess
import sys
from flask import Flask, render_template, request, redirect, url_for, jsonify, stream_with_context, Response
from werkzeug.utils import secure_filename

# Resolve repo root (parent of local_engine/)
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
    return sorted([
        f for f in os.listdir(gallery_path)
        if os.path.splitext(f)[1].lower() in ALLOWED_EXTENSIONS
    ])


def build_manifest_from_disk(gallery_path):
    """Create a manifest dict from current disk state, preserving existing manifest data."""
    existing = load_manifest(gallery_path) or {}
    existing_map = {e["filename"]: e for e in existing.get("photos", [])}
    files = get_all_photos(gallery_path)

    photos = []
    for i, f in enumerate(existing.get("photos", [])):
        if f["filename"] in set(files):
            photos.append(f)

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


def list_galleries():
    galleries = []
    for name in sorted(os.listdir(PHOTOS_DIR)):
        path = os.path.join(PHOTOS_DIR, name)
        if not os.path.isdir(path) or name.startswith(('.', '_')):
            continue
        sub_dirs = [d for d in os.listdir(path)
                    if os.path.isdir(os.path.join(path, d)) and not d.startswith(('.', '_'))]
        is_collection = bool(sub_dirs)
        if is_collection:
            count = sum(
                len([f for f in os.listdir(os.path.join(path, sd))
                     if os.path.splitext(f)[1].lower() in ALLOWED_EXTENSIONS])
                for sd in sub_dirs
            )
        else:
            count = len([f for f in os.listdir(path)
                         if os.path.splitext(f)[1].lower() in ALLOWED_EXTENSIONS])
        galleries.append({"id": name, "is_collection": is_collection,
                          "count": count, "sub_dirs": sub_dirs})
    return galleries


# --- Routes ---

@app.route("/")
def dashboard():
    galleries = list_galleries()
    return render_template("dashboard.html", galleries=galleries)


@app.route("/gallery/<gallery_id>")
def gallery_editor(gallery_id):
    gallery_path = os.path.join(PHOTOS_DIR, gallery_id)
    if not os.path.isdir(gallery_path):
        return "Gallery not found", 404

    # Check if collection
    sub_dirs = [d for d in os.listdir(gallery_path)
                if os.path.isdir(os.path.join(gallery_path, d)) and not d.startswith(('.', '_'))]
    if sub_dirs:
        # Show collection sub-galleries list
        subs = []
        for sd in sorted(sub_dirs):
            sp = os.path.join(gallery_path, sd)
            count = len([f for f in os.listdir(sp) if os.path.splitext(f)[1].lower() in ALLOWED_EXTENSIONS])
            subs.append({"id": sd, "full_id": f"{gallery_id}__{sd}", "path": sp, "count": count})
        return render_template("collection_editor.html", gallery_id=gallery_id, subs=subs)

    manifest = build_manifest_from_disk(gallery_path)
    description = ""
    info_path = os.path.join(gallery_path, "info.md")
    if os.path.exists(info_path):
        with open(info_path, "r", encoding="utf-8") as f:
            description = f.read()

    return render_template("gallery_editor.html", gallery_id=gallery_id,
                           manifest=manifest, description=description,
                           thumb_prefix=f"../photos/{gallery_id}/_thumbs/",
                           photo_prefix=f"../photos/{gallery_id}/")


@app.route("/gallery/<gallery_id>/manifest", methods=["POST"])
def save_gallery_manifest(gallery_id):
    gallery_path = os.path.join(PHOTOS_DIR, gallery_id)
    data = request.get_json()
    save_manifest(gallery_path, data)
    return jsonify({"ok": True})


@app.route("/gallery/<path:gallery_id>/upload", methods=["POST"])
def upload_photos(gallery_id):
    # Support sub-gallery ids like "00_Czechy__00_Brno" → path "00_Czechy/00_Brno"
    gallery_rel = gallery_id.replace("__", os.sep)
    gallery_path = os.path.join(PHOTOS_DIR, gallery_rel)
    os.makedirs(gallery_path, exist_ok=True)

    files = request.files.getlist("photos")
    saved = []
    for f in files:
        ext = os.path.splitext(f.filename)[1].lower()
        if ext in ALLOWED_EXTENSIONS:
            filename = secure_filename(f.filename)
            f.save(os.path.join(gallery_path, filename))
            saved.append(filename)
    return jsonify({"saved": saved})


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
    gallery_path = os.path.join(PHOTOS_DIR, name)
    os.makedirs(gallery_path, exist_ok=True)
    return redirect(url_for("gallery_editor", gallery_id=name))


@app.route("/gallery/<path:gallery_id>/description", methods=["POST"])
def save_description(gallery_id):
    gallery_rel = gallery_id.replace("__", os.sep)
    gallery_path = os.path.join(PHOTOS_DIR, gallery_rel)
    text = request.form.get("description", "")
    info_path = os.path.join(gallery_path, "info.md")
    with open(info_path, "w", encoding="utf-8") as f:
        f.write(text)
    return redirect(url_for("gallery_editor", gallery_id=gallery_id))


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


def main():
    print("Portfolio local engine starting at http://localhost:5000")
    app.run(debug=True, host="localhost", port=5000)


if __name__ == "__main__":
    main()
