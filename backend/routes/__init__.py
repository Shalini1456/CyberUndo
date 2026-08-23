# Routes package initialization
from .auth_routes import auth_bp
from .file_routes import file_bp

__all__ = ["auth_bp", "file_bp"]
