"""
Analytics, Risk Engine, Blast Radius and Activity Tracking Routes for CyberUndo (Member 4)
-----------------------------------------------------------------------------------------
Exposes REST API endpoints for:
1. Risk Analysis (/api/risk/analyze)
2. Blast Radius Calculation (/api/blast-radius/analyze)
3. Activity Event Logging (/api/activity/log)
4. Chronological Activity Retrieval (/api/activity/<file_id>)
"""

from flask import Blueprint, request, jsonify
from backend.services.risk_engine import analyze_risk
from backend.services.blast_radius import calculate_blast_radius
from backend.services.activity_service import log_activity, get_file_activity

analytics_bp = Blueprint("analytics", __name__)


# --------------------------------------------------------------------------
# MODULE 1: Risk Engine Endpoint
# --------------------------------------------------------------------------
@analytics_bp.route("/risk/analyze", methods=["POST"])
@analytics_bp.route("/api/risk/analyze", methods=["POST"])
def api_analyze_risk():
    """
    POST /api/risk/analyze
    Calculates the risk score, level, factors, and recommendations.
    
    Expected JSON Body:
    {
        "file_id": "123",
        "file_name": "Project_Final.pdf",
        "sensitivity": "Confidential",
        "recipient_count": 3,
        "download_allowed": true,
        "expiry": "Never"
    }
    """
    data = request.get_json(silent=True) or {}
    
    file_id = data.get("file_id", "unknown")
    file_name = data.get("file_name", "unknown")
    sensitivity = data.get("sensitivity", "Public")
    recipient_count = data.get("recipient_count", 1)
    download_allowed = data.get("download_allowed", False)
    expiry = data.get("expiry", "Never")
    
    result = analyze_risk(
        file_id=file_id,
        file_name=file_name,
        sensitivity=sensitivity,
        recipient_count=recipient_count,
        download_allowed=download_allowed,
        expiry=expiry
    )
    
    return jsonify(result), 200


# --------------------------------------------------------------------------
# MODULE 2: Blast Radius Endpoint
# --------------------------------------------------------------------------
@analytics_bp.route("/blast-radius/analyze", methods=["POST"])
@analytics_bp.route("/api/blast-radius/analyze", methods=["POST"])
def api_calculate_blast_radius():
    """
    POST /api/blast-radius/analyze
    Computes exposure metrics and dynamic exposure chain.
    
    Expected JSON Body:
    {
        "file_id": "123",
        "file_name": "Project_Final.pdf",
        "sensitivity": "Confidential",
        "recipient_count": 3,
        "download_allowed": true,
        "expiry": "Never",
        "risk_score": 80,       (optional)
        "risk_level": "HIGH"    (optional)
    }
    """
    data = request.get_json(silent=True) or {}
    
    result = calculate_blast_radius(
        file_id=data.get("file_id", "unknown"),
        file_name=data.get("file_name", "unknown"),
        sensitivity=data.get("sensitivity", "Internal"),
        recipient_count=data.get("recipient_count", 1),
        download_allowed=data.get("download_allowed", False),
        expiry=data.get("expiry", "Never"),
        risk_score=data.get("risk_score"),
        risk_level=data.get("risk_level")
    )
    
    return jsonify(result), 200


# --------------------------------------------------------------------------
# MODULE 3: Activity Tracking Endpoints
# --------------------------------------------------------------------------
@analytics_bp.route("/activity/log", methods=["POST"])
@analytics_bp.route("/api/activity/log", methods=["POST"])
def api_log_activity():
    """
    POST /api/activity/log
    Logs a lifecycle event for a file.
    
    Expected JSON Body:
    {
        "file_id": "123",
        "file_name": "Project_Final.pdf",
        "actor": "recipient@example.com",
        "event_type": "FILE_VIEWED",
        "details": "Recipient viewed the shared file"
    }
    """
    data = request.get_json(silent=True) or {}
    
    file_id = data.get("file_id")
    file_name = data.get("file_name")
    actor = data.get("actor") or data.get("user_id")
    event_type = data.get("event_type")
    details = data.get("details", "")
    timestamp = data.get("timestamp")
    
    # Validate required parameters
    if not file_id or not file_name or not event_type:
        return jsonify({
            "error": "Missing required fields. 'file_id', 'file_name', and 'event_type' are mandatory."
        }), 400
        
    try:
        activity_record = log_activity(
            file_id=file_id,
            file_name=file_name,
            actor=actor,
            event_type=event_type,
            details=details,
            ip_address=request.remote_addr,
            timestamp=timestamp
        )
        return jsonify(activity_record), 201
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": f"Failed to log activity: {str(e)}"}), 500


@analytics_bp.route("/activity/<file_id>", methods=["GET"])
@analytics_bp.route("/api/activity/<file_id>", methods=["GET"])
def api_get_activity(file_id):
    """
    GET /api/activity/<file_id>
    Retrieves chronological activity history for a specific file.
    """
    if not file_id:
        return jsonify({"error": "file_id is required"}), 400
        
    try:
        history = get_file_activity(file_id=file_id)
        return jsonify(history), 200
    except Exception as e:
        return jsonify({"error": f"Failed to retrieve activity history: {str(e)}"}), 500
