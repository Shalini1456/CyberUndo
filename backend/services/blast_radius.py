"""
Blast Radius Service for CyberUndo (Member 4 Integration)
----------------------------------------------------------
Calculates the potential exposure chain, forwarding risk, and blast radius summary
before a file is shared with recipients.
"""

from backend.services.risk_engine import analyze_risk


def calculate_blast_radius(
    file_id: str = "unknown",
    file_name: str = "unknown",
    sensitivity: str = "Internal",
    recipient_count: int = 1,
    download_allowed: bool = False,
    expiry: str = "Never",
    risk_score: int = None,
    risk_level: str = None
) -> dict:
    """
    Computes the blast radius analysis and exposure chain for a shared file.
    
    Args:
        file_id (str): ID of the file.
        file_name (str): Name of the file.
        sensitivity (str): Sensitivity tier ('Public', 'Internal', 'Confidential', 'Sensitive').
        recipient_count (int): Number of direct recipients.
        download_allowed (bool): Whether download permission is enabled.
        expiry (str): Expiration window string.
        risk_score (int, optional): Pre-calculated risk score if available.
        risk_level (str, optional): Pre-calculated risk level if available.
        
    Returns:
        dict: Structured Blast Radius report containing exposure metrics and the exposure chain.
    """
    try:
        count = int(recipient_count)
    except (ValueError, TypeError):
        count = 1
        
    is_download_allowed = download_allowed in [True, "true", "True", "1", 1]
    clean_expiry = str(expiry).strip().lower() if expiry else "never"

    # If risk score/level were not provided, compute them using the Risk Engine
    if risk_score is None or risk_level is None:
        risk_analysis = analyze_risk(
            file_id=file_id,
            file_name=file_name,
            sensitivity=sensitivity,
            recipient_count=count,
            download_allowed=is_download_allowed,
            expiry=expiry
        )
        risk_score = risk_analysis["risk_score"]
        risk_level = risk_analysis["risk_level"]

    # 1. Download risk status
    download_risk = "ENABLED" if is_download_allowed else "DISABLED"

    # 2. Forwarding risk estimation
    if count > 5 and is_download_allowed:
        forwarding_risk = "LIKELY"
    elif count > 1 or is_download_allowed:
        forwarding_risk = "POSSIBLE"
    else:
        forwarding_risk = "LOW"

    # 3. Link Expiry risk classification
    if "never" in clean_expiry or clean_expiry == "":
        link_expiry_risk = "UNLIMITED"
    elif "7 day" in clean_expiry or "7day" in clean_expiry or clean_expiry == "7d":
        link_expiry_risk = "HIGH"
    elif "1 day" in clean_expiry or "1day" in clean_expiry or clean_expiry == "24h":
        link_expiry_risk = "MODERATE"
    else:
        link_expiry_risk = "LOW"

    # 4. Estimated overall exposure
    if risk_score >= 81 or (count > 5 and is_download_allowed):
        estimated_exposure = "CRITICAL"
    elif risk_score >= 61 or (count > 1 and is_download_allowed):
        estimated_exposure = "HIGH"
    elif risk_score >= 31 or count > 1:
        estimated_exposure = "MEDIUM"
    else:
        estimated_exposure = "LOW"

    # 5. Blast radius human-readable summary
    if is_download_allowed and count > 1:
        blast_radius_summary = (
            "This file may be accessed by multiple recipients and downloaded copies "
            "may remain outside the owner's control."
        )
    elif is_download_allowed and count <= 1:
        blast_radius_summary = (
            "The recipient can download and retain offline copies of this file, "
            "increasing secondary exposure risks."
        )
    elif not is_download_allowed and count > 1:
        blast_radius_summary = (
            "Multiple recipients can view the file online, but offline downloads "
            "are restricted."
        )
    else:
        blast_radius_summary = (
            "This file has minimal blast radius with restricted view-only access "
            "and limited exposure."
        )

    # 6. Dynamic Exposure Chain generation
    recipient_label = f"{count} Recipient" if count == 1 else f"{count} Recipients"
    download_label = "Download Enabled" if is_download_allowed else "View Only"
    forwarding_label = "Potential Forwarding" if forwarding_risk in ["POSSIBLE", "LIKELY"] else "Restricted Viewing"
    
    if is_download_allowed or link_expiry_risk == "UNLIMITED" or risk_level in ["HIGH", "CRITICAL"]:
        final_exposure_label = "Unknown Exposure"
    else:
        final_exposure_label = "Controlled Access"

    exposure_chain = [
        "Owner",
        recipient_label,
        "File Access",
        download_label,
        forwarding_label,
        final_exposure_label
    ]

    return {
        "risk_level": risk_level,
        "estimated_exposure": estimated_exposure,
        "direct_recipients": count,
        "download_risk": download_risk,
        "forwarding_risk": forwarding_risk,
        "link_expiry_risk": link_expiry_risk,
        "blast_radius_summary": blast_radius_summary,
        "exposure_chain": exposure_chain
    }
