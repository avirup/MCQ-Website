# config.py
import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from the project root (where you run `flask run`)
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent

class Config:
    """Application configuration (reads from .env when available)."""

    # ---- Flask basics ----
    SECRET_KEY = os.getenv("SESSION_SECRET_KEY", "dev-secret-change-me")
    WTF_CSRF_TIME_LIMIT = None

    # ---- SQLAlchemy / Database ----
    # IMPORTANT: We default to a non-root user so we never silently fall back to root.
    # Example .env:
    #   DB_URL=mysql+pymysql://mcq_user:password@127.0.0.1:3306/mcq_platform
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DB_URL",
        "mysql+pymysql://mcq_user:password@127.0.0.1:3306/mcq_platform",
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    # Toggle verbose SQL logs by setting SQLALCHEMY_ECHO=1 in .env
    SQLALCHEMY_ECHO = os.getenv("SQLALCHEMY_ECHO", "0") in ("1", "true", "True")

    # ---- Sessions (Flask-Session) ----
    SESSION_TYPE = os.getenv("SESSION_TYPE", "filesystem")
    SESSION_PERMANENT = os.getenv("SESSION_PERMANENT", "0") in ("1", "true", "True")
    # Where filesystem sessions are stored (only used when SESSION_TYPE=filesystem)
    SESSION_FILE_DIR = os.getenv(
        "SESSION_FILE_DIR",
        str(BASE_DIR / ".flask_session"),
    )

    # ---- Uploads ----
    # All question/option images will be stored under this path
    UPLOAD_DIR = os.getenv(
        "UPLOAD_DIR",
        str(BASE_DIR / "uploads" / "questions"),
    )
    # Limit uploaded file size (e.g., 8 MB)
    MAX_CONTENT_LENGTH = int(os.getenv("MAX_CONTENT_LENGTH", 8 * 1024 * 1024))

    # ---- Admin password file (for file-based admin auth) ----
    ADMIN_SECRET_FILE = os.getenv(
        "ADMIN_SECRET_FILE",
        str(BASE_DIR / "config" / "admin_secret.txt"),
    )

    # ---- Misc ----
    # If you deploy behind a proxy, you may want to trust headers:
    # PREFERRED_URL_SCHEME = os.getenv("PREFERRED_URL_SCHEME", "http")


# Optional: ensure directories exist (safe no-op if they already do)
Path(Config.SESSION_FILE_DIR).mkdir(parents=True, exist_ok=True)
Path(Config.UPLOAD_DIR).mkdir(parents=True, exist_ok=True)
Path(Config.ADMIN_SECRET_FILE).parent.mkdir(parents=True, exist_ok=True)
