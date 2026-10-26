from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "trusted_registry.db"

SUPPORTED_DOCUMENT_TYPES = {
    "PASSPORT",
    "VISA",
    "ID_CARD",
    "CERTIFICATE",
    "PERMIT",
    "UNKNOWN",
}
ALLOWED_UPLOAD_TYPES = ["png", "jpg", "jpeg", "webp", "tif", "tiff", "pdf"]
MAX_UPLOAD_SIZE_MB = 15