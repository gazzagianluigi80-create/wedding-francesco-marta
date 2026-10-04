import os

# --- Nomi degli sposi (modifica qui) ---
COUPLE_NAMES = os.getenv("COUPLE_NAMES", "Francesco e Marta")

# --- Password evento condivisa via WhatsApp ---
EVENT_PASSWORD = os.getenv("EVENT_PASSWORD", "26ottobre2026")

# --- Password admin (solo organizzatori) ---
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "Framart26")

# --- Chiave sessione cookie (cambiala in produzione via env SECRET_KEY) ---
SECRET_KEY = os.getenv("SECRET_KEY", "cambia-questa-chiave-matrimonio-2026")

# --- URL pubblico dell'app (usato per il QR code). Cambiabile da /admin ---
PUBLIC_URL = os.getenv("PUBLIC_URL", "https://wedding-Francesco&Marta.onrender.com")

# --- Compressione immagini ---
MAX_SIDE = int(os.getenv("MAX_SIDE", "1920"))
JPEG_QUALITY = int(os.getenv("JPEG_QUALITY", "85"))

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
