import os
from pathlib import Path

# Base directories
BASE_DIR = Path(__file__).resolve().parent.parent.parent
WORKSPACE_DIR = BASE_DIR.parent
DATA_DIR = Path(os.getenv("LKG_DATA_DIR", str(BASE_DIR / "data")))
DATA_DIR.mkdir(parents=True, exist_ok=True)

DB_PATH = Path(os.getenv("LKG_DB_PATH", str(DATA_DIR / "knowledge_graph.sqlite3")))
UPLOADS_DIR = DATA_DIR / "uploads"
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
BACKUPS_DIR = DATA_DIR / "backups"
BACKUPS_DIR.mkdir(parents=True, exist_ok=True)

API_HOST = os.getenv("LKG_HOST", "127.0.0.1")
API_PORT = int(os.getenv("LKG_PORT", "8765"))
CORS_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:8765",
    "http://127.0.0.1:8765",
]

# Embedding & Search settings
DEFAULT_CHUNK_SIZE = 500
DEFAULT_CHUNK_OVERLAP = 80
MAX_UPLOAD_SIZE_BYTES = 25 * 1024 * 1024  # 25 MB limit
