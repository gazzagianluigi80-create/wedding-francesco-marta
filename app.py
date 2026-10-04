import io
import json
import os
import random
import threading
import zipfile
from datetime import datetime
from functools import wraps

import qrcode
from flask import (
    Flask, jsonify, redirect, render_template, request,
    send_file, send_from_directory, session, url_for
)
from PIL import Image, ImageOps
from werkzeug.utils import secure_filename

import config

app = Flask(__name__)
app.secret_key = config.SECRET_KEY
app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024  # 50 MB per request (multi-file)

os.makedirs(config.UPLOAD_FOLDER, exist_ok=True)

_lock = threading.Lock()


# ---------- Helpers ----------

def get_public_url():
    """URL pubblico effettivo: file custom (da admin) > config/env."""
    try:
        if os.path.exists(config.QR_CUSTOM_URL_FILE):
            with open(config.QR_CUSTOM_URL_FILE, "r", encoding="utf-8") as f:
                custom = f.read().strip()
                if custom:
                    return custom.rstrip("/")
    except OSError:
        pass
    return config.PUBLIC_URL.rstrip("/")


def load_photos():
    if not os.path.exists(config.PHOTOS_JSON):
        return []
    try:
        with open(config.PHOTOS_JSON, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except (json.JSONDecodeError, OSError):
        return []


def save_photos(photos):
    tmp = config.PHOTOS_JSON + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(photos, f, ensure_ascii=False, indent=2)
    os.replace(tmp, config.PHOTOS_JSON)


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("authed"):
            # Le chiamate fetch si aspettano JSON, non un redirect HTML
            if request.path.startswith("/api/"):
                return jsonify({"ok": False, "error": "login_required"}), 401
            # rimanda al form password mantenendo la destinazione
            return redirect(url_for("upload", next=request.path))
        return view(*args, **kwargs)
    return wrapped


def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("admin"):
            return redirect(url_for("admin"))
        return view(*args, **kwargs)
    return wrapped


def make_qr_image(url):
    qr = qrcode.QRCode(box_size=10, border=4)  # border >= 4 moduli per scansione sicura
    qr.add_data(url)
    qr.make(fit=True)
    return qr.make_image(fill_color="#2E2E2E", back_color="white").convert("RGB")


def compress_and_save(file_storage):
    """Ridimensiona lato max 1920px, salva JPEG 85%. Ritorna filename."""
    img = Image.open(file_storage.stream)
    img = ImageOps.exif_transpose(img)  # rispetta orientamento scatto cellulare
    if img.mode in ("RGBA", "LA", "P"):
        img = img.convert("RGB")
    img.thumbnail((config.MAX_SIDE, config.MAX_SIDE), Image.LANCZOS)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    rand = f"{random.randint(1000, 9999)}"
    base = secure_filename(os.path.splitext(file_storage.filename or "foto")[0])[:30] or "foto"
    filename = f"{stamp}_{rand}_{base}.jpg"
    dest = os.path.join(config.UPLOAD_FOLDER, filename)
    img.save(dest, "JPEG", quality=config.JPEG_QUALITY, optimize=True)
    return filename


def storage_size():
    total = 0
    try:
        for name in os.listdir(config.UPLOAD_FOLDER):
            p = os.path.join(config.UPLOAD_FOLDER, name)
            if os.path.isfile(p):
                total += os.path.getsize(p)
    except OSError:
        pass
    return total


def human_size(n):
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} TB"


# ---------- Pagine pubbliche ----------

@app.route("/")
def landing():
    return render_template(
        "landing.html",
        couple=config.COUPLE_NAMES,
        public_url=get_public_url(),
    )


@app.route("/qr")
def qr_page():
    """Pagina stampabile con QR grande + testo + link + download PNG."""
    return render_template("qr.html", couple=config.COUPLE_NAMES, public_url=get_public_url())


@app.route("/qr.png")
def qr_png():
    img = make_qr_image(get_public_url() + "/upload")
    buf = io.BytesIO()
    img.save(buf, "PNG")
    buf.seek(0)
    return send_file(buf, mimetype="image/png", as_attachment=False, download_name="qr-matrimonio.png")


@app.route("/qr-download")
def qr_download():
    img = make_qr_image(get_public_url() + "/upload")
    buf = io.BytesIO()
    img.save(buf, "PNG")
    buf.seek(0)
    return send_file(buf, mimetype="image/png", as_attachment=True, download_name="qr-matrimonio.png")


# ---------- Upload (protetto da password evento) ----------

@app.route("/upload", methods=["GET", "POST"])
def upload():
    if request.method == "POST" and "password" in request.form and "photos" not in request.files:
        # Tentativo di login evento
        if request.form.get("password", "") == config.EVENT_PASSWORD:
            session["authed"] = True
            nxt = request.args.get("next") or request.form.get("next") or url_for("upload")
            return redirect(nxt)
        return render_template("upload.html", couple=config.COUPLE_NAMES,
                               momentis=config.MOMENTI, need_password=True,
                               error="Password non corretta. Chiedila agli sposi.",
                               next_url=request.args.get("next", "")), 403

    if not session.get("authed"):
        return render_template("upload.html", couple=config.COUPLE_NAMES,
                               momentis=config.MOMENTI, need_password=True,
                               next_url=request.args.get("next", ""))

    if request.method == "POST":
        # Upload vero e proprio (anche via fetch JSON)
        files = request.files.getlist("photos")
        name = (request.form.get("name") or "").strip()[:60]
        momento = (request.form.get("momento") or "").strip()[:60]
        caption = (request.form.get("caption") or "").strip()[:140]
        if momento not in config.MOMENTI:
            momento = ""
        saved = []
        errors = []
        with _lock:
            photos = load_photos()
            for fs in files:
                if not fs or not fs.filename:
                    continue
                ext = os.path.splitext(fs.filename)[1].lower()
                if ext not in config.ALLOWED_EXT:
                    errors.append(f"{fs.filename}: formato non supportato")
                    continue
                try:
                    filename = compress_and_save(fs)
                except Exception as exc:  # noqa: BLE001 - feedback utente
                    errors.append(f"{fs.filename}: errore ({exc})")
                    continue
                photos.append({
                    "filename": filename,
                    "name": name,
                    "momento": momento,
                    "caption": caption,
                    "datetime": datetime.now().isoformat(timespec="seconds"),
                })
                saved.append(filename)
            photos.sort(key=lambda p: p.get("datetime", ""), reverse=True)
            save_photos(photos)
        # Risposta JSON per upload AJAX con progress, altrimenti pagina ringraziamento
        if request.headers.get("X-Requested-With") == "XMLHttpRequest" or "application/json" in request.headers.get("Accept", ""):
            return jsonify({"ok": True, "saved": saved, "errors": errors, "count": len(saved)})
        return render_template("upload.html", couple=config.COUPLE_NAMES,
                               momentis=config.MOMENTI, success=True,
                               saved_count=len(saved), errors=errors)
    return render_template("upload.html", couple=config.COUPLE_NAMES, momentis=config.MOMENTI)


@app.route("/logout")
def logout():
    session.pop("authed", None)
    return redirect(url_for("landing"))


# ---------- Galleria condivisa ----------

@app.route("/gallery")
@login_required
def gallery():
    momento = request.args.get("momento", "")
    return render_template("gallery.html", couple=config.COUPLE_NAMES,
                           momentis=config.MOMENTI, active_filter=momento,
                           is_admin=bool(session.get("admin")))


@app.route("/api/photos")
@login_required
def api_photos():
    momento = request.args.get("momento", "")
    photos = load_photos()
    photos.sort(key=lambda p: p.get("datetime", ""), reverse=True)
    if momento:
        photos = [p for p in photos if p.get("momento") == momento]
    return jsonify({"photos": photos, "total": len(load_photos())})


@app.route("/uploads/<path:filename>")
def serve_upload(filename):
    if not session.get("authed") and not session.get("admin"):
        return redirect(url_for("upload", next=request.path))
    return send_from_directory(config.UPLOAD_FOLDER, filename)


# ---------- Admin ----------

@app.route("/admin", methods=["GET", "POST"])
def admin():
    if request.method == "POST" and not session.get("admin"):
        if request.form.get("password", "") == config.ADMIN_PASSWORD:
            session["admin"] = True
            return redirect(url_for("admin"))
        return render_template("admin.html", need_password=True,
                               error="Password admin errata."), 403
    if not session.get("admin"):
        return render_template("admin.html", need_password=True)
    photos = load_photos()
    photos.sort(key=lambda p: p.get("datetime", ""), reverse=True)
    return render_template(
        "admin.html",
        need_password=False,
        total=len(photos),
        size=human_size(storage_size()),
        public_url=get_public_url(),
        photos=photos,
    )


@app.route("/admin/set-url", methods=["POST"])
@admin_required
def admin_set_url():
    new_url = (request.form.get("public_url") or "").strip().rstrip("/")
    if new_url and (new_url.startswith("http://") or new_url.startswith("https://")):
        with open(config.QR_CUSTOM_URL_FILE, "w", encoding="utf-8") as f:
            f.write(new_url)
    return redirect(url_for("admin"))


@app.route("/admin/download")
@admin_required
def admin_download():
    """ZIP di tutte le foto + photos.json (filesystem Render effimero: scaricare spesso!)."""
    buf = io.BytesIO()
    photos = load_photos()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for p in photos:
            fp = os.path.join(config.UPLOAD_FOLDER, p.get("filename", ""))
            if os.path.isfile(fp):
                z.write(fp, arcname=p.get("filename", ""))
        z.writestr("photos.json", json.dumps(photos, ensure_ascii=False, indent=2))
    buf.seek(0)
    stamp = datetime.now().strftime("%Y%m%d_%H%M")
    return send_file(buf, mimetype="application/zip", as_attachment=True,
                     download_name=f"matrimonio-foto-{stamp}.zip")


@app.route("/admin/delete/<filename>", methods=["POST"])
@admin_required
def admin_delete(filename):
    filename = secure_filename(filename)
    with _lock:
        photos = [p for p in load_photos() if p.get("filename") != filename]
        save_photos(photos)
    try:
        os.remove(os.path.join(config.UPLOAD_FOLDER, filename))
    except OSError:
        pass
    # torna alla galleria se la cancellazione parte da lì
    ref = request.referrer or ""
    if "/gallery" in ref:
        return redirect(url_for("gallery"))
    return redirect(url_for("admin"))


@app.route("/admin/logout")
def admin_logout():
    session.pop("admin", None)
    return redirect(url_for("landing"))


@app.route("/health")
def health():
    return "ok", 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")), debug=True)
