import os
from datetime import timedelta

# Base directory of the backend project
BASE_DIR = os.path.abspath(os.path.dirname(__file__))

class Config:
    """Application configuration."""
    SECRET_KEY = os.environ.get("SECRET_KEY", "cyberundo-dev-super-secret-key-change-in-production")
    JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "cyberundo-jwt-secret-key-change-in-production")
    JWT_EXPIRATION_DELTA = timedelta(days=1)  # Tokens valid for 24 hours

    # Database: SQLite stored in the backend folder
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", 
        f"sqlite:///{os.path.join(BASE_DIR, 'cyberundo.db')}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

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

    # Multi-Provider Transactional Email Configuration (Brevo > SMTP > Resend)
    BREVO_API_KEY = os.environ.get("BREVO_API_KEY", "").strip()
    SMTP_USER = os.environ.get("SMTP_USER", "").strip()
    SMTP_PASS = (os.environ.get("SMTP_PASS") or os.environ.get("SMTP_PASSWORD") or "").strip()
    SMTP_HOST = os.environ.get("SMTP_HOST", "smtp.gmail.com").strip()
    SMTP_PORT = int(os.environ.get("SMTP_PORT", 587))
    RESEND_API_KEY = os.environ.get("RESEND_API_KEY", "").strip()
    EMAIL_FROM = os.environ.get("EMAIL_FROM") or os.environ.get("FROM_EMAIL") or "CyberUndo Security <onboarding@resend.dev>"
    FRONTEND_URL = os.environ.get("FRONTEND_URL", "https://cyber-undo.vercel.app")

