"""
Risk Engine Service for CyberUndo (Member 4 Integration)
---------------------------------------------------------
Calculates a rule-driven risk score, risk level, dynamic risk factors,
and actionable security recommendations before a file is shared.
"""


def get_sensitivity_score(sensitivity: str) -> tuple[int, str]:
    """
    Returns the numeric score and description for the file sensitivity level.
    
    Scoring:
      - Public: 10
      - Internal: 25
      - Confidential: 50
      - Sensitive: 70
    """
    clean_sensitivity = str(sensitivity).strip().capitalize() if sensitivity else "Public"
    
    scoring_map = {
        "Public": (10, "File is designated as Public"),
        "Internal": (25, "File contains internal organizational information"),
        "Confidential": (50, "File contains confidential information"),
        "Sensitive": (70, "File contains sensitive personal or critical business data")
    }
    
    return scoring_map.get(clean_sensitivity, (10, "File is designated as Public"))


def get_recipient_score(recipient_count: int) -> tuple[int, str]:
    """
    Returns the numeric score and risk factor description based on recipient count.
    
    Scoring:
      - 1 recipient: 5
      - 2 to 5 recipients: 15
      - More than 5 recipients: 25
    """
    try:
        count = int(recipient_count)
    except (ValueError, TypeError):
        count = 1

    if count <= 1:
        return (5, "Single recipient direct access")
    elif 2 <= count <= 5:
        return (15, "Multiple recipients increase exposure")
    else:
        return (25, "Broad sharing (>5 recipients) significantly increases exposure")


def get_download_score(download_allowed: bool) -> tuple[int, str]:
    """
    Returns the numeric score and risk factor based on download permission.
    
    Scoring:
      - Download allowed: +15
      - Download disabled: +0
    """
    is_allowed = download_allowed in [True, "true", "True", "1", 1]
    
    if is_allowed:
        return (15, "Download permission is enabled")
    else:
        return (0, "Download permission is disabled (view-only mode)")


def get_expiry_score(expiry: str) -> tuple[int, str]:
    """
    Returns the numeric score and risk factor based on link expiration window.
    
    Scoring:
      - 1 Hour: +0
      - 1 Day / 24h: +5
      - 7 Days: +10
      - Never: +20
    """
    clean_expiry = str(expiry).strip().lower() if expiry else "never"
    
    if "1 hour" in clean_expiry or "1hour" in clean_expiry or clean_expiry == "1h" or clean_expiry == "hour":
        return (0, "Link expires quickly (1 Hour)")
    elif "1 day" in clean_expiry or "1day" in clean_expiry or "24 hour" in clean_expiry or clean_expiry == "24h" or clean_expiry == "day":
        return (5, "Link expires in 1 Day")
    elif "7 day" in clean_expiry or "7day" in clean_expiry or clean_expiry == "7d" or "week" in clean_expiry:
        return (10, "Link has an extended 7-day expiration window")
    else:  # "never", None, or unrecognized
        return (20, "Link does not expire")


def get_risk_level(risk_score: int) -> str:
    """
    Maps the final risk score (0-100) to a risk level:
      - 0–30: LOW
      - 31–60: MEDIUM
      - 61–80: HIGH
      - 81–100: CRITICAL
    """
    if risk_score <= 30:
        return "LOW"
    elif risk_score <= 60:
        return "MEDIUM"
    elif risk_score <= 80:
        return "HIGH"
    else:
        return "CRITICAL"


def analyze_risk(
    file_id: str = "unknown",
    file_name: str = "unknown",
    sensitivity: str = "Public",
    recipient_count: int = 1,
    download_allowed: bool = False,
    expiry: str = "Never"
) -> dict:
    """
    Analyzes the security risk of sharing a file based on sensitivity, recipient count,
    download permissions, and expiration duration.
    
    Args:
        file_id (str): Unique identifier of the file.
        file_name (str): Name of the file being shared.
        sensitivity (str): Sensitivity tier ('Public', 'Internal', 'Confidential', 'Sensitive').
        recipient_count (int): Number of recipients receiving access.
        download_allowed (bool): Whether recipients can download the file.
        expiry (str): Expiration window ('1 Hour', '1 Day', '7 Days', 'Never').
        
    Returns:
        dict: Risk analysis report including score, level, factors, and recommendations.
    """
    # 1. Calculate individual component scores & factor descriptions
    sens_score, sens_factor = get_sensitivity_score(sensitivity)
    recip_score, recip_factor = get_recipient_score(recipient_count)
    down_score, down_factor = get_download_score(download_allowed)
    exp_score, exp_factor = get_expiry_score(expiry)
    
    # 2. Compute final risk score capped at 100
    raw_score = sens_score + recip_score + down_score + exp_score
    risk_score = min(raw_score, 100)
    
    # 3. Determine overall risk level
    risk_level = get_risk_level(risk_score)
    
    # 4. Assemble dynamic risk factors
    risk_factors = [
        sens_factor,
        recip_factor,
        down_factor,
        exp_factor
    ]
    
    # 5. Generate tailored recommendations to reduce risk
    recommendations = []
    
    try:
        count = int(recipient_count)
    except (ValueError, TypeError):
        count = 1
        
    is_download_allowed = download_allowed in [True, "true", "True", "1", 1]
    clean_expiry = str(expiry).strip().lower() if expiry else "never"
    clean_sens = str(sensitivity).strip().capitalize() if sensitivity else "Public"

    if count > 1:
        recommendations.append("Limit the number of recipients")
        
    if is_download_allowed:
        recommendations.append("Disable download permission")
        
    if "never" in clean_expiry or "7 day" in clean_expiry or clean_expiry == "7d":
        recommendations.append("Set an expiry time")
        
    if clean_sens in ["Confidential", "Sensitive"]:
        recommendations.append("Verify recipient identities before sharing")
        
    if not recommendations:
        recommendations.append("Current settings provide minimal risk exposure")

    return {
        "file_id": str(file_id),
        "file_name": str(file_name),
        "risk_score": risk_score,
        "risk_level": risk_level,
        "risk_factors": risk_factors,
        "recommendations": recommendations
    }
