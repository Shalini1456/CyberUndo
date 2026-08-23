import re
from flask import Blueprint, request, jsonify
from database import db
from models import User
from auth import hash_password, check_password, generate_jwt, token_required

auth_bp = Blueprint("auth", __name__)

EMAIL_REGEX = r"^[\w\.-]+@[\w\.-]+\.\w+$"

@auth_bp.route("/register", methods=["POST"])
def register():
    """
    Register a new user account.
    Expects JSON: { "name": "...", "email": "...", "password": "..." }
    """
    data = request.get_json(silent=True)
    if not data:
        return jsonify({
            "success": False,
            "message": "Invalid request body. JSON required."
        }), 400

    name = (data.get("name") or "").strip()
    email = (data.get("email") or "").strip().lower()
    password = data.get("password")

    # Input validations
    if not name or not email or not password:
        return jsonify({
            "success": False,
            "message": "Missing required fields: name, email, and password are required."
        }), 400

    if not re.match(EMAIL_REGEX, email):
        return jsonify({
            "success": False,
            "message": "Invalid email address format."
        }), 400

    if len(password) < 6:
        return jsonify({
            "success": False,
            "message": "Password must be at least 6 characters long."
        }), 400

    # Prevent duplicate registrations
    if User.query.filter_by(email=email).first():
        return jsonify({
            "success": False,
            "message": "An account with this email address already exists."
        }), 409

    try:
        new_user = User(
            name=name,
            email=email,
            password_hash=hash_password(password)
        )
        db.session.add(new_user)
        db.session.commit()

        return jsonify({
            "success": True,
            "message": "User registered successfully.",
            "data": {
                "user": new_user.to_dict()
            }
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({
            "success": False,
            "message": f"Registration failed due to a server error: {str(e)}"
        }), 500


@auth_bp.route("/login", methods=["POST"])
def login():
    """
    Authenticate user and return JWT token.
    Expects JSON: { "email": "...", "password": "..." }
    """
    data = request.get_json(silent=True)
    if not data:
        return jsonify({
            "success": False,
            "message": "Invalid request body. JSON required."
        }), 400

    email = (data.get("email") or "").strip().lower()
    password = data.get("password")

    if not email or not password:
        return jsonify({
            "success": False,
            "message": "Email and password are required."
        }), 400

    user = User.query.filter_by(email=email).first()

    if not user or not check_password(user.password_hash, password):
        return jsonify({
            "success": False,
            "message": "Invalid email or password."
        }), 401

    token = generate_jwt(user.id, user.email)

    return jsonify({
        "success": True,
        "message": "Login successful.",
        "data": {
            "token": token,
            "user": user.to_dict()
        }
    }), 200


@auth_bp.route("/auth/me", methods=["GET"])
@token_required
def get_current_user(current_user):
    """
    Get profile information for the currently authenticated user.
    """
    return jsonify({
        "success": True,
        "message": "Current user retrieved successfully.",
        "data": {
            "user": current_user.to_dict()
        }
    }), 200
