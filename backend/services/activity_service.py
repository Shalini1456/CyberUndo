"""
Activity Tracker Service for CyberUndo (Member 4 Integration)
--------------------------------------------------------------
Logs and retrieves file lifecycle activities and audit events in chronological order,
integrated with the application's database.
"""

from datetime import datetime
import json
from flask import has_app_context

try:
    from database import db
    from models import ActivityLog, File
except (ImportError, ModuleNotFoundError):
    from backend.database import db
    from backend.models import ActivityLog, File

# Standard permitted event types in the CyberUndo lifecycle
VALID_EVENT_TYPES = {
    "FILE_UPLOADED",
    "FILE_SHARED",
    "LINK_OPENED",
    "FILE_VIEWED",
    "FILE_DOWNLOADED",
    "ACCESS_REVOKED"
}


def log_activity(
    file_id: str,
    file_name: str = None,
    actor: str = None,
    event_type: str = "FILE_VIEWED",
    details: str = "",
    user_id: int = None,
    ip_address: str = None,
    timestamp: str = None
) -> dict:
    """
    Logs an activity event for a file to the database.
    
    Args:
        file_id (str): Unique identifier of the file.
        file_name (str, optional): Name of the file. If omitted, resolved from database.
        actor (str, optional): Email or username of actor. Defaults to user_id or 'anonymous'.
        event_type (str): Type of event ('FILE_UPLOADED', 'FILE_SHARED', 'LINK_OPENED', 'FILE_VIEWED', 'FILE_DOWNLOADED', 'ACCESS_REVOKED').
        details (str, optional): Additional context or description.
        user_id (int, optional): User ID if authenticated.
        ip_address (str, optional): Client IP address.
        timestamp (str, optional): ISO timestamp string. Defaults to UTC now.
        
    Returns:
        dict: The recorded activity log entry matching Member 4 contract.
    """
    clean_event = str(event_type).strip().upper()
    if clean_event not in VALID_EVENT_TYPES:
        raise ValueError(
            f"Invalid event_type: '{event_type}'. Must be one of: {sorted(list(VALID_EVENT_TYPES))}"
        )

    # Standardize actor
    effective_actor = str(actor or user_id or "anonymous")
    
    parsed_time = datetime.utcnow()
    if timestamp:
        try:
            parsed_time = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        except Exception:
            parsed_time = datetime.utcnow()

    # Parse numeric file_id if applicable
    numeric_file_id = None
    try:
        numeric_file_id = int(file_id)
    except (ValueError, TypeError):
        pass

    effective_file_name = file_name
    if not effective_file_name and numeric_file_id and has_app_context():
        file_obj = File.query.get(numeric_file_id)
        if file_obj:
            effective_file_name = file_obj.filename
    if not effective_file_name:
        effective_file_name = f"File_{file_id}"

    log_entry = ActivityLog(
        file_id=numeric_file_id,
        user_id=user_id,
        file_name=effective_file_name,
        actor=effective_actor,
        event_type=clean_event,
        action=clean_event,
        ip_address=ip_address,
        details=str(details or ""),
        metadata_json=json.dumps({"details": details, "actor": effective_actor}),
        timestamp=parsed_time
    )

    if has_app_context():
        db.session.add(log_entry)
        db.session.commit()
        activity_id = log_entry.id
    else:
        activity_id = 1

    return {
        "activity_id": activity_id,
        "file_id": str(file_id),
        "file_name": str(effective_file_name),
        "actor": str(effective_actor),
        "event_type": clean_event,
        "timestamp": log_entry.timestamp.isoformat() if log_entry.timestamp else datetime.utcnow().isoformat(),
        "details": str(details or "")
    }


def get_file_activity(file_id: str) -> dict:
    """
    Retrieves all logged activities for a specific file in chronological order,
    including the most recent event.
    
    Args:
        file_id (str): Unique identifier of the file.
        
    Returns:
        dict: Chronological list of events with metadata and latest event pointer.
    """
    numeric_file_id = None
    try:
        numeric_file_id = int(file_id)
    except (ValueError, TypeError):
        pass

    activities = []
    file_name = ""

    if has_app_context():
        query = ActivityLog.query
        if numeric_file_id:
            query = query.filter_by(file_id=numeric_file_id)
        else:
            query = query.filter(ActivityLog.file_name == str(file_id))

        logs = query.order_by(ActivityLog.id.asc()).all()
        for log in logs:
            event_name = log.event_type or log.action or "FILE_VIEWED"
            # Normalize legacy action names
            if event_name == "VIEW":
                event_name = "FILE_VIEWED"
            elif event_name == "DOWNLOAD":
                event_name = "FILE_DOWNLOADED"
            elif event_name == "SHARE":
                event_name = "FILE_SHARED"
            elif event_name == "REVOKE" or event_name == "REVOKE_ALL":
                event_name = "ACCESS_REVOKED"
            elif event_name == "UPLOAD":
                event_name = "FILE_UPLOADED"

            record = {
                "activity_id": log.id,
                "file_id": str(log.file_id or file_id),
                "file_name": log.file_name or (log.file.filename if log.file else f"File_{file_id}"),
                "actor": log.actor or (f"User #{log.user_id}" if log.user_id else (log.ip_address or "anonymous")),
                "event_type": event_name,
                "timestamp": log.timestamp.isoformat() if log.timestamp else datetime.utcnow().isoformat(),
                "details": log.details or (json.loads(log.metadata_json).get("details", "") if log.metadata_json and log.metadata_json.startswith("{") else (log.metadata_json or ""))
            }
            activities.append(record)
            file_name = record["file_name"]

    latest_event = activities[-1] if activities else None

    return {
        "file_id": str(file_id),
        "file_name": file_name,
        "total_events": len(activities),
        "latest_event": latest_event,
        "activities": activities
    }
