import os
from pathlib import Path


class Config:
    BASE_DIR = Path(__file__).resolve().parent
    STATIC_DIR = BASE_DIR / "app" / "static"
    UPLOAD_DIR = STATIC_DIR / "uploads"
    DATABASE_PATH = Path(os.getenv("KAAJD_DB_PATH", BASE_DIR / "kaajd.sqlite3"))
    AUTH_ENABLED = os.getenv("KAAJD_AUTH_ENABLED", "false").lower() in {
        "1",
        "true",
        "yes",
    }
    BASIC_AUTH_USERNAME = os.getenv("KAAJD_BASIC_AUTH_USERNAME", "")
    BASIC_AUTH_PASSWORD = os.getenv("KAAJD_BASIC_AUTH_PASSWORD", "")
    LLM_ENDPOINT_URL = os.getenv("KAAJD_LLM_ENDPOINT_URL", "")
    LLM_MODEL = os.getenv("KAAJD_LLM_MODEL", "")
    LLM_API_KEY = os.getenv("KAAJD_LLM_API_KEY", "")
    MAX_CONTENT_LENGTH = int(os.getenv("KAAJD_MAX_UPLOAD_BYTES", 25 * 1024 * 1024))
