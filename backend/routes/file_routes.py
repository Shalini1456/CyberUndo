import os
import uuid
from flask import Blueprint, request, jsonify, current_app, send_from_directory
from werkzeug.utils import secure_filename
from database import db
from models import File
from auth import token_required

file_bp = Blueprint("files", __name__)

def allowed_file(filename: str) -> bool:
    """Check if file extension is allowed."""
    if "." not in filename:
        return False
    ext = filename.rsplit(".", 1)[1].lower()
    return ext in current_app.config["ALLOWED_EXTENSIONS"]


@file_bp.route("/files/upload", methods=["POST"])
@token_required
def upload_file(current_user):
    """
    Upload a file, generate unique stored filename, save locally, and record metadata.
    Accepts: multipart/form-data with 'file' field.
    """
    if "file" not in request.files:
        return jsonify({
            "success": False,
            "message": "No file field found in request."
        }), 400

    file_obj = request.files["file"]

    if file_obj.filename == "":
        return jsonify({
            "success": False,
            "message": "No file selected for uploading."
        }), 400

    original_filename = secure_filename(file_obj.filename)
    if not original_filename:
        # Fallback if filename was stripped of invalid characters
        original_filename = "unnamed_file"

    if not allowed_file(original_filename):
        allowed_list = ", ".join(sorted(current_app.config["ALLOWED_EXTENSIONS"]))
        return jsonify({
            "success": False,
            "message": f"File type not permitted. Allowed extensions: {allowed_list}"
        }), 400

    # Ensure upload directory exists
    upload_dir = current_app.config["UPLOAD_FOLDER"]
    os.makedirs(upload_dir, exist_ok=True)

    # Generate unique stored filename to prevent collisions and path traversal
    unique_prefix = uuid.uuid4().hex
    stored_filename = f"{unique_prefix}_{original_filename}"
    full_file_path = os.path.abspath(os.path.join(upload_dir, stored_filename))

    # Security check: Ensure file path remains strictly inside upload_dir
    if not full_file_path.startswith(os.path.abspath(upload_dir)):
        return jsonify({
            "success": False,
            "message": "Invalid file path traversal detected."
        }), 400

    try:
        # Save file to disk
        file_obj.save(full_file_path)

        # Record metadata in SQLite database
        new_file = File(
            owner_id=current_user.id,
            filename=original_filename,
            stored_filename=stored_filename,
            file_path=full_file_path,
            status="active"
        )
        db.session.add(new_file)
        db.session.commit()

        return jsonify({
            "success": True,
            "message": "File uploaded and registered successfully.",
            "data": {
                "file": new_file.to_dict()
            }
        }), 201

    except Exception as e:
        db.session.rollback()
        # Clean up orphaned physical file if database commit failed
        if os.path.exists(full_file_path):
            try:
                os.remove(full_file_path)
            except OSError:
                pass

        return jsonify({
            "success": False,
            "message": f"Failed to save file: {str(e)}"
        }), 500


@file_bp.route("/files", methods=["GET"])
@token_required
def list_files(current_user):
    """
    List all active files owned by the authenticated user.
    """
    user_files = File.query.filter_by(
        owner_id=current_user.id
    ).order_by(File.created_at.desc()).all()

    return jsonify({
        "success": True,
        "message": f"Retrieved {len(user_files)} file(s).",
        "data": {
            "files": [f.to_dict() for f in user_files]
        }
    }), 200


@file_bp.route("/files/<int:file_id>", methods=["GET"])
@token_required
def get_file(current_user, file_id):
    """
    Retrieve metadata for a specific file owned by the authenticated user.
    """
    file_record = File.query.get(file_id)

    if not file_record:
        return jsonify({
            "success": False,
            "message": f"File with ID {file_id} not found."
        }), 404

    # Ownership check: Prevent users from accessing another user's private file metadata
    if file_record.owner_id != current_user.id:
        return jsonify({
            "success": False,
            "message": "Access denied. You do not have permission to view this file."
        }), 403

    return jsonify({
        "success": True,
        "message": "File metadata retrieved successfully.",
        "data": {
            "file": file_record.to_dict()
        }
    }), 200


@file_bp.route("/files/<int:file_id>/download", methods=["GET"])
@token_required
def download_file(current_user, file_id):
    """
    Download a file owned by the authenticated user.
    """
    file_record = File.query.get(file_id)

    if not file_record:
        return jsonify({
            "success": False,
            "message": f"File with ID {file_id} not found."
        }), 404

    if file_record.owner_id != current_user.id:
        return jsonify({
            "success": False,
            "message": "Access denied. You do not have permission to download this file."
        }), 403

    upload_dir = current_app.config["UPLOAD_FOLDER"]
    return send_from_directory(
        upload_dir,
        file_record.stored_filename,
        as_attachment=True,
        download_name=file_record.filename
    )
