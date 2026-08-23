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
