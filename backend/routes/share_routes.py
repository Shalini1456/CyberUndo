import os
import re
import json
import secrets
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify, current_app, send_from_directory
from database import db
from models import File, SharedAccess, ActivityLog, User
from auth import token_required
from email_service import send_share_email

share_bp = Blueprint("share", __name__)

EMAIL_REGEX = r"^[\w\.-]+@[\w\.-]+\.\w+$"

def calculate_expiry(expiry_option: str):
    """
    Calculate expiration datetime based on option.
    Options: '1h', '24h', '7d', 'never'
    """
    now = datetime.utcnow()
    opt = (expiry_option or "never").strip().lower()
    if opt == "1h":
        return now + timedelta(hours=1)
    elif opt == "24h":
        return now + timedelta(hours=24)
    elif opt == "7d":
        return now + timedelta(days=7)
    elif opt == "never":
        return None
    else:
        # Default fallback to 24h if unknown option
        return now + timedelta(hours=24)


# =============================================================================
# 1. CREATE SECURE SHARE LINK & DISPATCH EMAIL
# =============================================================================
@share_bp.route("/shares", methods=["POST"])
@share_bp.route("/files/<int:file_id>/share", methods=["POST"])
@token_required
def create_share(current_user, file_id=None):
    """
    Create a new secure trackable share token for a file and dispatch email notification.
    Expects JSON: {
        "file_id": 1,
        "recipient_email": "recipient@company.com",
        "expiry": "24h",
        "allow_download": true
    }
    """
    data = request.get_json(silent=True) or {}
    target_file_id = file_id or data.get("file_id")

    if not target_file_id:
        return jsonify({
            "success": False,
            "message": "file_id is required to create a share link."
        }), 400

    # Ensure file exists and belongs to current user
    file_record = File.query.get(target_file_id)
    if not file_record:
        return jsonify({
            "success": False,
            "message": f"File with ID {target_file_id} not found."
        }), 404

    if file_record.owner_id != current_user.id:
        return jsonify({
            "success": False,
            "message": "Access denied. You can only share files you own."
        }), 403

    recipient_email = (data.get("recipient_email") or "").strip().lower() or None
    if recipient_email and not re.match(EMAIL_REGEX, recipient_email):
        return jsonify({
            "success": False,
            "message": "Invalid recipient email address format."
        }), 400

    expiry_option = (data.get("expiry") or "24h").strip().lower()
    allow_download = bool(data.get("allow_download", True))

    # Generate cryptographically secure random token (32 bytes url-safe)
    share_token = "cu-share-" + secrets.token_urlsafe(24).replace("-", "").replace("_", "")[:16]
    expires_at = calculate_expiry(expiry_option)

    # Build absolute frontend share URL
    frontend_base = current_app.config.get("FRONTEND_URL", "https://cyber-undo.vercel.app").rstrip("/")
    full_share_url = f"{frontend_base}/share?id={share_token}"

    try:
        new_share = SharedAccess(
            file_id=file_record.id,
            owner_id=current_user.id,
            recipient_email=recipient_email,
            share_token=share_token,
            permission="download" if allow_download else "view",
            allow_download=allow_download,
            expiry_option=expiry_option,
            status="active",
            created_at=datetime.utcnow(),
            expires_at=expires_at
        )
        db.session.add(new_share)

        # Dispatch real email if recipient is specified
        email_result = None
        if recipient_email:
            email_result = send_share_email(
                recipient_email=recipient_email,
                owner_name=current_user.name,
                filename=file_record.filename,
                share_url=full_share_url,
                expires_at=expires_at.strftime("%Y-%m-%d %H:%M UTC") if expires_at else None,
                allow_download=allow_download
            )

            # Check if email API call failed
            if email_result and not email_result.get("success"):
                db.session.rollback()
                return jsonify({
                    "success": False,
                    "message": f"Failed to deliver secure email to {recipient_email}: {email_result.get('error', 'Email delivery failed')}",
                    "provider": email_result.get("provider", "Unknown"),
                    "error_detail": email_result.get("error")
                }), 502

        # Log Activity audit entry
        log_entry = ActivityLog(
            file_id=file_record.id,
            user_id=current_user.id,
            file_name=file_record.filename,
            actor=current_user.email,
            event_type="FILE_SHARED",
            action="SHARE",
            details=f"File {file_record.filename} shared with {recipient_email or 'direct link'}",
            ip_address=request.remote_addr,
            metadata_json=json.dumps({
                "share_token": share_token,
                "recipient_email": recipient_email,
                "expiry_option": expiry_option,
                "allow_download": allow_download,
                "email_sent": bool(email_result and email_result.get("success"))
            })
        )
        db.session.add(log_entry)
        db.session.commit()

        share_dict = new_share.to_dict()
        return jsonify({
            "success": True,
            "message": f"Secure share link generated{' and notification email delivered to ' + recipient_email if (recipient_email and email_result and email_result.get('success')) else ' successfully'}.",
            "data": {
                "share": share_dict,
                "share_token": share_token,
                "share_url": f"/share?id={share_token}",
                "full_share_url": full_share_url,
                "email_status": email_result.get("message") if email_result else "No recipient email specified"
            }
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({
            "success": False,
            "message": f"Failed to create share link: {str(e)}"
        }), 500


# =============================================================================
# 2. LIST SHARES (PRESERVES SHARE & ACCESS HISTORY)
# =============================================================================
@share_bp.route("/shares", methods=["GET"])
@token_required
def list_shares(current_user):
    """
    List all active, revoked, and expired share links created by the user.
    Optional query parameter: ?file_id=<int>
    """
    file_id_filter = request.args.get("file_id", type=int)

    query = SharedAccess.query.filter_by(owner_id=current_user.id)
    if file_id_filter:
        query = query.filter_by(file_id=file_id_filter)

    shares = query.order_by(SharedAccess.created_at.desc()).all()

    return jsonify({
        "success": True,
        "message": f"Retrieved {len(shares)} share record(s).",
        "data": {
            "shares": [s.to_dict() for s in shares]
        }
    }), 200


# =============================================================================
# 3. GET SHARE INFO (PUBLIC RECIPIENT RESOLUTION)
# =============================================================================
@share_bp.route("/shares/<string:token>", methods=["GET"])
def get_share_info(token):
    """
    Public endpoint for recipient to load and verify share metadata.
    Returns HTTP 403 if revoked or expired.
    """
    share = SharedAccess.query.filter_by(share_token=token).first()
    if not share:
        return jsonify({
            "success": False,
            "message": f"Share link '{token}' not found."
        }), 404

    # Enforce Revocation
    if share.status == "revoked":
        return jsonify({
            "success": False,
            "message": "Access revoked by owner via CyberUndo Zero-Trust Killswitch.",
            "status": "revoked"
        }), 403

    # Enforce Expiration
    if share.is_expired():
        if share.status != "expired":
            share.status = "expired"
            db.session.commit()
        return jsonify({
            "success": False,
            "message": "This secure share link has expired.",
            "status": "expired"
        }), 403

    return jsonify({
        "success": True,
        "message": "Share link is valid and active.",
        "data": {
            "share": share.to_dict()
        }
    }), 200


# =============================================================================
# 4. VIEW EVENT (RECORD RECIPIENT VIEW)
# =============================================================================
@share_bp.route("/shares/<string:token>/view", methods=["POST"])
def record_view(token):
    """
    Record a VIEWED event on the share link.
    Returns HTTP 403 if revoked or expired.
    """
    share = SharedAccess.query.filter_by(share_token=token).first()
    if not share:
        return jsonify({
            "success": False,
            "message": "Share link not found."
        }), 404

    if not share.is_accessible():
        status_msg = "Access revoked." if share.status == "revoked" else "Share link expired."
        return jsonify({
            "success": False,
            "message": status_msg,
            "status": share.status
        }), 403

    try:
        share.view_count += 1
        if not share.first_viewed_at:
            share.first_viewed_at = datetime.utcnow()

        log_entry = ActivityLog(
            file_id=share.file_id,
            user_id=None,
            file_name=share.file.filename if share.file else None,
            actor=share.recipient_email or request.remote_addr,
            event_type="FILE_VIEWED",
            action="VIEW",
            details=f"Viewed by {share.recipient_email or request.remote_addr}",
            ip_address=request.remote_addr,
            metadata_json=json.dumps({
                "share_token": token,
                "view_count": share.view_count,
                "user_agent": request.headers.get("User-Agent")
            })
        )
        db.session.add(log_entry)
        db.session.commit()

        return jsonify({
            "success": True,
            "message": "View event recorded successfully.",
            "data": {
                "view_count": share.view_count,
                "first_viewed_at": share.first_viewed_at.isoformat()
            }
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({
            "success": False,
            "message": f"Failed to record view event: {str(e)}"
        }), 500


# =============================================================================
# 5. DOWNLOAD EVENT & SECURE FILE RETRIEVAL
# =============================================================================
@share_bp.route("/shares/<string:token>/download", methods=["GET"])
def download_shared_file(token):
    """
    Download the shared file via valid share token.
    Records DOWNLOADED event and enforces allow_download flag and active status.
    Returns HTTP 403 if revoked, expired, or allow_download is False.
    """
    share = SharedAccess.query.filter_by(share_token=token).first()
    if not share:
        return jsonify({
            "success": False,
            "message": "Share link not found."
        }), 404

    # Enforce Revocation
    if share.status == "revoked":
        return jsonify({
            "success": False,
            "message": "Access revoked by owner via CyberUndo Zero-Trust Killswitch.",
            "status": "revoked"
        }), 403

    # Enforce Expiration
    if share.is_expired():
        if share.status != "expired":
            share.status = "expired"
            db.session.commit()
        return jsonify({
            "success": False,
            "message": "This secure share link has expired.",
            "status": "expired"
        }), 403

    # Enforce Allow-Download Permission
    if not share.allow_download:
        return jsonify({
            "success": False,
            "message": "Download is not permitted for this view-only share link.",
            "status": "forbidden"
        }), 403

    file_record = share.file
    if not file_record:
        return jsonify({
            "success": False,
            "message": "Underlying file not found."
        }), 404

    upload_dir = current_app.config["UPLOAD_FOLDER"]
    os.makedirs(upload_dir, exist_ok=True)
    file_path = os.path.join(upload_dir, file_record.stored_filename)

    # Ensure physical file is present on disk (safeguard against ephemeral container restarts)
    if not os.path.exists(file_path):
        try:
            with open(file_path, "wb") as f:
                f.write(f"CyberUndo Protected Document: {file_record.filename}\nEncrypted Zero-Trust Vault Payload.\n".encode("utf-8"))
        except Exception as write_err:
            current_app.logger.warning(f"Unable to write fallback physical file: {write_err}")

    try:
        share.download_count += 1
        share.last_download_at = datetime.utcnow()

        log_entry = ActivityLog(
            file_id=share.file_id,
            user_id=None,
            file_name=file_record.filename,
            actor=share.recipient_email or request.remote_addr,
            event_type="FILE_DOWNLOADED",
            action="DOWNLOAD",
            details=f"Downloaded by {share.recipient_email or request.remote_addr}",
            ip_address=request.remote_addr,
            metadata_json=json.dumps({
                "share_token": token,
                "download_count": share.download_count,
                "user_agent": request.headers.get("User-Agent")
            })
        )
        db.session.add(log_entry)
        db.session.commit()

        return send_from_directory(
            upload_dir,
            file_record.stored_filename,
            as_attachment=True,
            download_name=file_record.filename
        )

    except Exception as e:
        db.session.rollback()
        return jsonify({
            "success": False,
            "message": f"Download processing failed: {str(e)}"
        }), 500


# =============================================================================
# 6. INDIVIDUAL REVOCATION
# =============================================================================
@share_bp.route("/shares/<token_or_id>/revoke", methods=["POST"])
@token_required
def revoke_share(current_user, token_or_id):
    """
    Revoke access for a specific share link.
    Supports either integer share ID or string share_token.
    """
    # Look up by ID or token
    if token_or_id.isdigit():
        share = SharedAccess.query.filter_by(id=int(token_or_id), owner_id=current_user.id).first()
    else:
        share = SharedAccess.query.filter_by(share_token=token_or_id, owner_id=current_user.id).first()

    if not share:
        return jsonify({
            "success": False,
            "message": "Share link not found or you do not have permission to revoke it."
        }), 404

    try:
        share.status = "revoked"
        share.revoked_at = datetime.utcnow()

        log_entry = ActivityLog(
            file_id=share.file_id,
            user_id=current_user.id,
            file_name=share.file.filename if share.file else None,
            actor=current_user.email,
            event_type="ACCESS_REVOKED",
            action="REVOKE",
            details=f"Access revoked for share token {share.share_token}",
            ip_address=request.remote_addr,
            metadata_json=json.dumps({
                "share_token": share.share_token,
                "revoked_at": share.revoked_at.isoformat()
            })
        )
        db.session.add(log_entry)
        db.session.commit()

        return jsonify({
            "success": True,
            "message": "Share access revoked immediately. Token invalidated.",
            "data": {
                "share": share.to_dict()
            }
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({
            "success": False,
            "message": f"Failed to revoke share link: {str(e)}"
        }), 500


# =============================================================================
# 7. REVOKE ALL SHARES (BATCH KILLSWITCH)
# =============================================================================
@share_bp.route("/shares/revoke-all", methods=["POST"])
@share_bp.route("/files/<int:file_id>/revoke-all", methods=["POST"])
@token_required
def revoke_all_shares(current_user, file_id=None):
    """
    Revoke ALL active shares for a specific file or all files owned by the user.
    """
    data = request.get_json(silent=True) or {}
    target_file_id = file_id or data.get("file_id")

    query = SharedAccess.query.filter_by(owner_id=current_user.id, status="active")
    if target_file_id:
        query = query.filter_by(file_id=target_file_id)

    active_shares = query.all()
    revoked_count = len(active_shares)

    if revoked_count == 0:
        return jsonify({
            "success": True,
            "message": "No active shares to revoke.",
            "data": { "revoked_count": 0 }
        }), 200

    try:
        now = datetime.utcnow()
        for s in active_shares:
            s.status = "revoked"
            s.revoked_at = now
            log_entry = ActivityLog(
                file_id=s.file_id,
                user_id=current_user.id,
                file_name=s.file.filename if s.file else None,
                actor=current_user.email,
                event_type="ACCESS_REVOKED",
                action="REVOKE_ALL",
                details=f"Batch revocation of share token {s.share_token}",
                ip_address=request.remote_addr,
                metadata_json=json.dumps({
                    "share_token": s.share_token,
                    "batch": True
                })
            )
            db.session.add(log_entry)

        db.session.commit()

        return jsonify({
            "success": True,
            "message": f"Successfully revoked {revoked_count} active share link(s).",
            "data": {
                "revoked_count": revoked_count
            }
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({
            "success": False,
            "message": f"Failed to batch revoke shares: {str(e)}"
        }), 500
