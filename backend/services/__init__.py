"""
Services package for CyberUndo.
Exports Risk Engine, Blast Radius Analysis, and Activity Tracking.
"""

try:
    from .risk_engine import (
        analyze_risk,
        get_sensitivity_score,
        get_recipient_score,
        get_download_score,
        get_expiry_score,
        get_risk_level
    )
    from .blast_radius import calculate_blast_radius
    from .activity_service import (
        log_activity,
        get_file_activity,
        VALID_EVENT_TYPES
    )
except (ImportError, ModuleNotFoundError):
    from services.risk_engine import (
        analyze_risk,
        get_sensitivity_score,
        get_recipient_score,
        get_download_score,
        get_expiry_score,
        get_risk_level
    )
    from services.blast_radius import calculate_blast_radius
    from services.activity_service import (
        log_activity,
        get_file_activity,
        VALID_EVENT_TYPES
    )

__all__ = [
    "analyze_risk",
    "calculate_blast_radius",
    "log_activity",
    "get_file_activity",
    "VALID_EVENT_TYPES",
    "get_sensitivity_score",
    "get_recipient_score",
    "get_download_score",
    "get_expiry_score",
    "get_risk_level"
]
