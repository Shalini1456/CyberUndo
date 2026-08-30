import os
from datetime import timedelta

# Base directory of the backend project
BASE_DIR = os.path.abspath(os.path.dirname(__file__))

def get_database_uri() -> str:
    """
    Resolve and normalize database URI for PostgreSQL/Supabase or local SQLite.
    Handles legacy 'postgres://' prefixes and converts to 'postgresql://'.
    """
    raw_url = os.environ.get("DATABASE_URL", "").strip()
    if not raw_url:
        return f"sqlite:///{os.path.join(BASE_DIR, 'cyberundo.db')}"
    if raw_url.startswith("postgres://"):
        raw_url = raw_url.replace("postgres://", "postgresql://", 1)
    return raw_url


def get_database_engine_options(db_uri: str) -> dict:
    """
    Configure resilient connection pooling options for PostgreSQL / Supabase poolers.
    Omits pooling arguments for SQLite to prevent driver warnings.
    """
    if db_uri.startswith("sqlite"):
        return {}
    return {
        "pool_pre_ping": True,
        "pool_recycle": 300
    }


class Config:
    """Application configuration."""
    SECRET_KEY = os.environ.get("SECRET_KEY", "cyberundo-dev-super-secret-key-change-in-production")
    JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "cyberundo-jwt-secret-key-change-in-production")
    JWT_EXPIRATION_DELTA = timedelta(days=1)  # Tokens valid for 24 hours
    ADMIN_SECRET = os.environ.get("ADMIN_SECRET", "").strip()

    # Database: Supabase PostgreSQL (via DATABASE_URL) or local SQLite fallback
    SQLALCHEMY_DATABASE_URI = get_database_uri()
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = get_database_engine_options(SQLALCHEMY_DATABASE_URI)

    # Uploads configuration
    UPLOAD_FOLDER = os.environ.get(
        "UPLOAD_FOLDER", 
        os.path.join(BASE_DIR, "uploads")
    )
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # Max 16MB file upload limit
    ALLOWED_EXTENSIONS = {
        "txt", "pdf", "png", "jpg", "jpeg", "gif", 
        "doc", "docx", "xls", "xlsx", "csv", "zip", "json"
    }

    # Transactional Email REST API Configuration (Google Apps Script > Brevo > Resend)
    GOOGLE_APPS_SCRIPT_URL = os.environ.get(
        "GOOGLE_APPS_SCRIPT_URL",
        "https://script.google.com/macros/s/AKfycbwNjvytHT16e9rIhfF7LB5soSL8UMwZRH6YiPbl3YJ5gECTJsx0qNS8xSn-V-kCfSzUWg/exec"
    ).strip()
    BREVO_API_KEY = os.environ.get("BREVO_API_KEY", "").strip()
    RESEND_API_KEY = os.environ.get("RESEND_API_KEY", "").strip()
    EMAIL_FROM = os.environ.get("EMAIL_FROM") or os.environ.get("FROM_EMAIL") or "CyberUndo Security <onboarding@resend.dev>"
    FRONTEND_URL = os.environ.get("FRONTEND_URL", "https://cyber-undo.vercel.app")

