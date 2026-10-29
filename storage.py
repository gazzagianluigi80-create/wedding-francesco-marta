"""Archivio delle foto. Se Cloudinary è configurato, le foto vivono nel cloud."""

import io
import json
import os
import threading
import time

import config

_lock = threading.RLock()

class StorageError(Exception):
    pass

class LocalStore:
    name = "locale"

    def __init__(self):
        os.makedirs(config.UPLOAD_FOLDER, exist_ok=True)

    def _load(self):
        if not os.path.exists(config.PHOTOS_JSON):
            return []
        try:
            with open(config.PHOTOS_JSON, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data if isinstance(data, list) else []
        except (json.JSONDecodeError, OSError):
            return []

    def _save(self, photos):
        tmp = config.PHOTOS_JSON + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(photos, f, ensure_ascii=False, indent=2)
        os.replace(tmp, config.PHOTOS_JSON)

    def list_photos(self):
        with _lock:
            photos = self._load()
        photos.sort(key=lambda p: p.get("datetime", ""), reverse=True)
        for p in photos:
            p["id"] = p.get("filename", "")
        return photos

    def save(self, data, base, meta):
        stamp = time.strftime("%Y%m%d_%H%M%S")
        filename = f"{stamp}_{meta['rand']}_{base}.jpg"
        with open(os.path.join(config.UPLOAD_FOLDER, filename), "wb") as f:
            f.write(data)
        photo = {
            "id": filename, "filename": filename, "name": meta["name"],
            "momento": meta["momento"], "caption": meta["caption"],
            "datetime": meta["datetime"],
        }
        with _lock:
            photos = self._load()
            photos.append(photo)
            photos.sort(key=lambda p: p.get("datetime", ""), reverse=True)
            self._save(photos)
        return photo

    def delete(self, photo_id):
        photo_id = os.path.basename(photo_id or "")
        if not photo_id:
            return False
        with _lock:
            photos = self._load()
            kept = [p for p in photos if p.get("filename") != photo_id]
            if len(kept) != len(photos):
                self._save(kept)
        try:
            os.remove(os.path.join(config.UPLOAD_FOLDER, photo_id))
        except OSError:
            pass
        return len(kept) != len(photos)

    def url(self, photo, width=None):
        from urllib.parse import quote
        return "/uploads/" + quote(photo.get("filename", ""))

    def read(self, photo):
        path = os.path.join(config.UPLOAD_FOLDER, photo.get("filename", ""))
        if not os.path.isfile(path):
            raise StorageError("file non trovato")
        with open(path, "rb") as f:
            return f.read()

    def storage_bytes(self):
        total = 0
        try:
            for name in os.listdir(config.UPLOAD_FOLDER):
                p = os.path.join(config.UPLOAD_FOLDER, name)
                if os.path.isfile(p):
                    total += os.path.getsize(p)
        except OSError:
            pass
        return total

class CloudinaryStore:
    name = "cloudinary"

    def __init__(self):
        import cloudinary
        import cloudinary.api
        import cloudinary.uploader
        import cloudinary.utils
        cloudinary.config(
            cloud_name=config.CLOUDINARY_CLOUD_NAME,
            api_key=config.CLOUDINARY_API_KEY,
            api_secret=config.CLOUDINARY_API_SECRET,
            secure=True,
        )
        self._cloudinary = cloudinary
        self.folder = (config.CLOUDINARY_FOLDER or "wedding").strip("/")
        self._photos = []
        self._fetched_at = 0.0
        self._usage_bytes = 0
        self._usage_at = 0.0

    def _fetch_page(self, cursor=None):
        kwargs = dict(type="upload", prefix=self.folder + "/", max_results=500, context=True, tags=False, direction="desc")
        if cursor:
            kwargs["next_cursor"] = cursor
        return self._cloudinary.api.resources(**kwargs)

    def _fetch_all(self):
        photos = []
        cursor = None
        while True:
            page = self._fetch_page(cursor)
            for r in page.get("resources", []):
                ctx = (r.get("context") or {}).get("custom") or {}
                public_id = r.get("public_id", "")
                photos.append({
                    "id": public_id, "filename": public_id.rsplit("/", 1)[-1],
                    "format": r.get("format", "jpg"), "name": ctx.get("name", "")[:60],
                    "momento": ctx.get("momento", "")[:60], "caption": ctx.get("caption", "")[:140],
                    "datetime": (r.get("created_at") or "")[:19], "bytes": r.get("bytes") or 0,
                })
            cursor = page.get("next_cursor")
            if not cursor:
                break
        photos.sort(key=lambda p: p.get("datetime", ""), reverse=True)
        return photos

    def list_photos(self):
        with _lock:
            fresh = self._photos and (time.time() - self._fetched_at) < config.PHOTO_CACHE_TTL
            if fresh:
                return list(self._photos)
            try:
                photos = self._fetch_all()
            except Exception as exc:
                if self._photos:
                    return list(self._photos)
                raise StorageError(f"Cloudinary non raggiungibile ({exc})") from exc
            self._photos = photos
            self._fetched_at = time.time()
            return list(photos)

    def save(self, data, base, meta):
        public_id = f"{self.folder}/{time.strftime('%Y%m%d_%H%M%S')}_{meta['rand']}_{base}"
        try:
            result = self._cloudinary.uploader.upload(
                io.BytesIO(data), public_id=public_id, format="jpg", resource_type="image",
                context={"name": meta["name"], "momento": meta["momento"], "caption": meta["caption"]},
            )
        except Exception as exc:
            raise StorageError(f"upload su Cloudinary non riuscito ({exc})") from exc
        photo = {
            "id": result.get("public_id", public_id), "filename": result.get("public_id", public_id).rsplit("/", 1)[-1],
            "format": result.get("format", "jpg"), "name": meta["name"], "momento": meta["momento"],
            "caption": meta["caption"], "datetime": meta["datetime"], "bytes": result.get("bytes") or 0,
        }
        with _lock:
            self._photos = [photo] + [p for p in self._photos if p["id"] != photo["id"]]
        return photo

    def delete(self, photo_id):
        if not photo_id or not photo_id.startswith(self.folder + "/"):
            raise StorageError("foto non valida")
        try:
            self._cloudinary.uploader.destroy(photo_id, invalidate=True)
        except Exception as exc:
            raise StorageError(f"cancellazione su Cloudinary non riuscita ({exc})") from exc
        with _lock:
            self._photos = [p for p in self._photos if p["id"] != photo_id]
        return True

    def url(self, photo, width=None):
        kwargs = dict(secure=True, quality="auto", fetch_format="auto", crop="limit")
        if width:
            kwargs["width"] = width
        url, _ = self._cloudinary.utils.cloudinary_url(photo["id"], format=photo.get("format", "jpg"), **kwargs)
        return url

    def read(self, photo):
        import requests
        resp = requests.get(self.url(photo, width=config.MAX_SIDE), timeout=30)
        resp.raise_for_status()
        return resp.content

    def storage_bytes(self):
        with _lock:
            if self._usage_at and (time.time() - self._usage_at) < config.CLOUDINARY_USAGE_TTL:
                return self._usage_bytes
        try:
            usage = self._cloudinary.api.usage()
            self._usage_bytes = int((usage.get("storage") or {}).get("usage") or 0)
            self._usage_at = time.time()
        except Exception:
            pass
        return self._usage_bytes

def get_store():
    # Se le chiavi fisse ci sono, usa Cloudinary. Punto. Nessun dubbio.
    if config.CLOUDINARY_CLOUD_NAME and config.CLOUDINARY_API_KEY and config.CLOUDINARY_API_SECRET:
        return CloudinaryStore()
    return LocalStore()