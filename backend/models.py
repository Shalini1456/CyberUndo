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
    Table for Member 2 (Secure Sharing + Revoke).
    Stores access tokens, recipient rules, permission levels, download flags,
    and revocation / expiration / telemetry timestamps.
    """
    __tablename__ = "shared_access"

    id = db.Column(db.Integer, primary_key=True)
    file_id = db.Column(db.Integer, db.ForeignKey("files.id"), nullable=False, index=True)
    owner_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    recipient_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True) # Optional if registered user
    recipient_email = db.Column(db.String(120), nullable=True)                     # Recipient email target
    share_token = db.Column(db.String(255), unique=True, nullable=False, index=True)
    permission = db.Column(db.String(50), default="view", nullable=False)          # 'view', 'download'
    allow_download = db.Column(db.Boolean, default=True, nullable=False)           # Allow download flag
    expiry_option = db.Column(db.String(20), default="never", nullable=False)      # '1h', '24h', '7d', 'never'
    status = db.Column(db.String(50), default="active", nullable=False)            # 'active', 'revoked', 'expired'
    view_count = db.Column(db.Integer, default=0, nullable=False)
    download_count = db.Column(db.Integer, default=0, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    expires_at = db.Column(db.DateTime, nullable=True)
    revoked_at = db.Column(db.DateTime, nullable=True)
    first_viewed_at = db.Column(db.DateTime, nullable=True)
    last_download_at = db.Column(db.DateTime, nullable=True)

    # Relationships
    owner_user = db.relationship("User", foreign_keys=[owner_id], backref="created_shares", lazy=True)

    def is_expired(self):
        if self.expires_at and datetime.utcnow() > self.expires_at:
            return True
        return False

    def is_accessible(self):
        if self.status == "revoked":
            return False
        if self.is_expired():
            return False
        return self.status == "active"

    def to_dict(self):
        # Dynamically check expiry on representation
        effective_status = "expired" if (self.status == "active" and self.is_expired()) else self.status
        return {
            "id": self.id,
            "file_id": self.file_id,
            "owner_id": self.owner_id,
            "owner_name": self.owner_user.name if self.owner_user else (self.file.owner.name if self.file and self.file.owner else None),
            "owner_email": self.owner_user.email if self.owner_user else (self.file.owner.email if self.file and self.file.owner else None),
            "recipient_id": self.recipient_id,
            "recipient_email": self.recipient_email,
            "share_token": self.share_token,
            "permission": self.permission,
            "allow_download": self.allow_download,
            "expiry_option": self.expiry_option,
            "status": effective_status,
            "view_count": self.view_count,
            "download_count": self.download_count,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "revoked_at": self.revoked_at.isoformat() if self.revoked_at else None,
            "first_viewed_at": self.first_viewed_at.isoformat() if self.first_viewed_at else None,
            "last_download_at": self.last_download_at.isoformat() if self.last_download_at else None,
            "file": self.file.to_dict() if self.file else None
        }


class ActivityLog(db.Model):
    """
    ActivityLog table supporting Member 4 Risk Engine, Blast Radius, and Activity Tracking.
    Stores audit trails for file actions, user sessions, and security telemetry.
    """
    __tablename__ = "activity_logs"

    id = db.Column(db.Integer, primary_key=True)
    file_id = db.Column(db.Integer, db.ForeignKey("files.id"), nullable=True, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True, index=True)
    file_name = db.Column(db.String(255), nullable=True)
    actor = db.Column(db.String(120), nullable=True)
    event_type = db.Column(db.String(50), nullable=True, index=True)              # e.g., 'FILE_SHARED', 'FILE_VIEWED', 'FILE_DOWNLOADED', 'ACCESS_REVOKED'
    action = db.Column(db.String(100), nullable=False)                            # e.g., 'UPLOAD', 'SHARE', 'VIEW', 'DOWNLOAD', 'REVOKE'
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    ip_address = db.Column(db.String(45), nullable=True)
    details = db.Column(db.Text, nullable=True)
    metadata_json = db.Column("metadata", db.Text, nullable=True)                 # JSON string containing telemetry context

    def to_dict(self):
        return {
            "id": self.id,
            "activity_id": self.id,
            "file_id": self.file_id,
            "user_id": self.user_id,
            "file_name": self.file_name or (self.file.filename if self.file else None),
            "actor": self.actor or (f"User #{self.user_id}" if self.user_id else (self.ip_address or "anonymous")),
            "event_type": self.event_type or self.action,
            "action": self.action,
            "details": self.details or self.metadata_json,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "ip_address": self.ip_address,
            "metadata": self.metadata_json
        }

