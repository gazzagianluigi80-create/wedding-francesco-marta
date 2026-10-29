import os

# --- Nomi degli sposi (modifica qui) ---
COUPLE_NAMES = os.getenv("COUPLE_NAMES", "Francesco e Marta")

# --- Password evento ---
REQUIRE_EVENT_PASSWORD = os.getenv("REQUIRE_EVENT_PASSWORD", "").lower() in ("1", "true", "yes", "on")
EVENT_PASSWORD = os.getenv("EVENT_PASSWORD", "26ottobre2026")

# --- Password admin (solo organizzatori) ---
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "Framart@26")

# --- Chiave sessione cookie ---
SECRET_KEY = os.getenv("SECRET_KEY", "cambia-questa-chiave-matrimonio-2026")

# --- URL pubblico dell'app ---
PUBLIC_URL = os.getenv("PUBLIC_URL", "https://wedding-francesco-marta.onrender.com")

# --- Compressione immagini ---
MAX_SIDE = int(os.getenv("MAX_SIDE", "1920"))
JPEG_QUALITY = int(os.getenv("JPEG_QUALITY", "85"))

# --- Archivio foto persistente (Cloudinary) ---
# Chiavi forzate nel codice per evitare conflitti con Render
CLOUDINARY_URL = ""
CLOUDINARY_CLOUD_NAME = "js1uvapn"
CLOUDINARY_API_KEY = "566494683377564"
CLOUDINARY_API_SECRET = "9pJjhxuUXqBkOlWn6X8UNMNyp84"
CLOUDINARY_FOLDER = "wedding"

# Secondi di cache
PHOTO_CACHE_TTL = 120
CLOUDINARY_USAGE_TTL = 600

# --- Cartelle / file ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
PHOTOS_JSON = os.path.join(BASE_DIR, "photos.json")
QR_CUSTOM_URL_FILE = os.path.join(BASE_DIR, "qr_url.txt")

MOMENTI = [
    "Viaggio (Veglie / Campi Salentina → Triggiano)",
    "Arrivo in location",
    "Cerimonia",
    "Ricevimento",
    "Taglio della torta",
    "Pista da ballo",
    "Momenti rubati",
]

ALLOWED_EXT = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
