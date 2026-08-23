from functools import wraps
from datetime import datetime, timezone
import jwt
from flask import request, jsonify, current_app
from werkzeug.security import generate_password_hash, check_password_hash
from models import User

def hash_password(password: str) -> str:
    """Hash password using Werkzeug's secure hashing algorithm."""
    return generate_password_hash(password)

def check_password(password_hash: str, password: str) -> bool:
    """Verify raw password against stored hash."""
    return check_password_hash(password_hash, password)

def generate_jwt(user_id: int, email: str) -> str:
    """Generate a signed JWT token valid for the configured duration."""
    payload = {
        "sub": user_id,
        "email": email,
        "iat": datetime.now(timezone.utc),
        "exp": datetime.now(timezone.utc) + current_app.config["JWT_EXPIRATION_DELTA"]
    }
    return jwt.encode(payload, current_app.config["JWT_SECRET_KEY"], algorithm="HS256")

def decode_jwt(token: str) -> dict:
    """Decode and validate a signed JWT token."""
    return jwt.decode(token, current_app.config["JWT_SECRET_KEY"], algorithms=["HS256"])

def token_required(f):
    """
    Middleware decorator protecting routes with Bearer JWT tokens.
    Extracts and attaches current_user (User instance) to the wrapped function.
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get("Authorization")

        if not auth_header:
            return jsonify({
                "success": False,
                "message": "Authorization token is missing"
            }), 401

        parts = auth_header.split(" ")
        if len(parts) != 2 or parts[0].lower() != "bearer":
            return jsonify({
                "success": False,
                "message": "Invalid Authorization header format. Expected 'Bearer <token>'"
            }), 401

        token = parts[1]

        try:
            payload = decode_jwt(token)
            user_id = payload.get("sub")
            current_user = User.query.get(user_id)

            if not current_user:
                return jsonify({
                    "success": False,
                    "message": "User associated with token no longer exists"
                }), 401

        except jwt.ExpiredSignatureError:
            return jsonify({
                "success": False,
                "message": "Token has expired. Please login again."
            }), 401
        except jwt.InvalidTokenError:
            return jsonify({
                "success": False,
                "message": "Invalid or malformed token."
            }), 401
        except Exception as e:
            return jsonify({
                "success": False,
                "message": f"Authentication failed: {str(e)}"
            }), 401

        return f(current_user, *args, **kwargs)

    return decorated
