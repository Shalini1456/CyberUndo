from datetime import datetime
from database import db

class User(db.Model):
    """
    Users table representing system accounts.
    """
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    files = db.relationship("File", backref="owner", lazy=True, cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


class File(db.Model):
    """
    Files table storing uploaded file metadata and ownership.
    """
    __tablename__ = "files"

    id = db.Column(db.Integer, primary_key=True)
    owner_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    filename = db.Column(db.String(255), nullable=False)           # Original uploaded filename
    stored_filename = db.Column(db.String(255), unique=True, nullable=False) # Sanitized UUID name on disk
    file_path = db.Column(db.String(500), nullable=False)          # Full path on local disk
    status = db.Column(db.String(50), default="active", nullable=False) # 'active', 'deleted', 'quarantined'
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # Relationships for other team modules
    shares = db.relationship("SharedAccess", backref="file", lazy=True, cascade="all, delete-orphan")
    activity_logs = db.relationship("ActivityLog", backref="file", lazy=True)

    def to_dict(self):
        return {
            "id": self.id,
            "owner_id": self.owner_id,
            "filename": self.filename,
            "stored_filename": self.stored_filename,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


class SharedAccess(db.Model):
    """
    Foundation table for Member 2 (Secure Sharing + Revoke).
    Stores access tokens, recipient rules, permission levels, and revocation timestamps.
    """
    __tablename__ = "shared_access"

    id = db.Column(db.Integer, primary_key=True)
    file_id = db.Column(db.Integer, db.ForeignKey("files.id"), nullable=False, index=True)
    owner_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    recipient_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True) # None if shared via public token
    share_token = db.Column(db.String(255), unique=True, nullable=False, index=True)
    permission = db.Column(db.String(50), default="view", nullable=False)          # e.g., 'view', 'download'
    status = db.Column(db.String(50), default="active", nullable=False)            # 'active', 'revoked', 'expired'
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    expires_at = db.Column(db.DateTime, nullable=True)
    revoked_at = db.Column(db.DateTime, nullable=True)

    def to_dict(self):
        return {
            "id": self.id,
            "file_id": self.file_id,
            "owner_id": self.owner_id,
            "recipient_id": self.recipient_id,
            "share_token": self.share_token,
            "permission": self.permission,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "revoked_at": self.revoked_at.isoformat() if self.revoked_at else None
        }


class ActivityLog(db.Model):
    """
    Foundation table for Member 4 (Blast Radius + Risk Engine + Activity Tracking).
    Stores audit trails for file actions, user sessions, and security telemetry.
    """
    __tablename__ = "activity_logs"

    id = db.Column(db.Integer, primary_key=True)
    file_id = db.Column(db.Integer, db.ForeignKey("files.id"), nullable=True, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True, index=True)
    action = db.Column(db.String(100), nullable=False)                            # e.g., 'UPLOAD', 'SHARE', 'ACCESS', 'REVOKE'
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    ip_address = db.Column(db.String(45), nullable=True)
    metadata_json = db.Column("metadata", db.Text, nullable=True)                 # JSON string containing telemetry context

    def to_dict(self):
        return {
            "id": self.id,
            "file_id": self.file_id,
            "user_id": self.user_id,
            "action": self.action,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "ip_address": self.ip_address,
            "metadata": self.metadata_json
        }
