import os
import json
import logging
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from flask import current_app

logger = logging.getLogger("cyberundo.email")

def send_share_email(recipient_email: str, owner_name: str, filename: str, share_url: str, expires_at: str = None, allow_download: bool = True) -> dict:
    """
    Send transactional notification email to the recipient using the Resend REST API.
    
    Parameters:
    - recipient_email: The target recipient's email address
    - owner_name: Display name of the file owner who shared the link
    - filename: Name of the confidential file being shared
    - share_url: Complete URL where recipient can view/download the document
    - expires_at: Expiration string or None
    - allow_download: Boolean whether download is permitted
    
    Returns dict:
    - {"success": True/False, "message": "...", "id": "...", "error": "..."}
    """
    api_key = current_app.config.get("RESEND_API_KEY", "").strip()
    from_email = current_app.config.get("EMAIL_FROM", "CyberUndo Security <onboarding@resend.dev>").strip()

    # If no API key is configured, fail with explicit configuration error
    if not api_key:
        logger.error(f"[Email Service] RESEND_API_KEY is not configured in environment.")
        return {
            "success": False,
            "error": "Email delivery failed: RESEND_API_KEY is not configured in server environment. Please configure RESEND_API_KEY in Render environment variables.",
            "code": 500
        }

    subject = f"Protected File Shared: {filename} from {owner_name}"
    
    permission_badge = "View & Download" if allow_download else "View Only (Download Restricted)"
    expiry_badge = f"Expires on {expires_at}" if expires_at else "No expiration set"

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
      <meta charset="utf-8">
      <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #060913; color: #e2e8f0; margin: 0; padding: 20px; }}
        .container {{ max-width: 560px; margin: 0 auto; background: #0b0f19; border: 1px solid #1e293b; border-radius: 16px; padding: 32px; box-shadow: 0 10px 25px rgba(0,0,0,0.5); }}
        .header {{ text-align: center; border-bottom: 1px solid #1e293b; padding-bottom: 20px; margin-bottom: 24px; }}
        .brand {{ font-size: 20px; font-weight: 800; color: #ffffff; letter-spacing: -0.5px; font-family: monospace; }}
        .brand span {{ color: #06b6d4; }}
        .card {{ background: #0f172a; border: 1px solid #1e293b; border-radius: 12px; padding: 20px; margin: 20px 0; }}
        .file-name {{ font-size: 16px; font-weight: 700; color: #ffffff; font-family: monospace; word-break: break-all; }}
        .meta-row {{ font-size: 12px; color: #94a3b8; margin-top: 6px; font-family: monospace; }}
        .btn {{ display: block; width: 100%; text-align: center; background: linear-gradient(135deg, #0891b2, #2563eb); color: #ffffff !important; text-decoration: none; padding: 14px 20px; border-radius: 10px; font-weight: 700; font-size: 14px; margin: 24px 0 16px 0; box-sizing: border-box; }}
        .security-notice {{ font-size: 11px; color: #64748b; text-align: center; line-height: 1.5; border-top: 1px solid #1e293b; padding-top: 16px; margin-top: 24px; }}
      </style>
    </head>
    <body>
      <div class="container">
        <div class="header">
          <div class="brand">Cyber<span>Undo</span></div>
          <p style="font-size: 12px; color: #06b6d4; margin: 4px 0 0 0; font-family: monospace;">Zero-Trust Secure File Access</p>
        </div>

        <p style="font-size: 14px; color: #cbd5e1; margin-top: 0;">
          <strong>{owner_name}</strong> has shared a confidential protected file with you via CyberUndo.
        </p>

        <div class="card">
          <div class="file-name">&#128196; {filename}</div>
          <div class="meta-row">Sender: {owner_name}</div>
          <div class="meta-row">Policy: {permission_badge}</div>
          <div class="meta-row">Status: {expiry_badge}</div>
        </div>

        <a href="{share_url}" class="btn" target="_blank">ACCESS PROTECTED FILE &rarr;</a>

        <div class="security-notice">
          <strong>Zero-Trust Protection Notice:</strong><br>
          This link is protected with CyberUndo Killswitch technology. The sender maintains full revocation control and can sever access at any moment. All access events are logged in real-time.
        </div>
      </div>
    </body>
    </html>
    """

    payload = {
        "from": from_email,
        "to": [recipient_email],
        "subject": subject,
        "html": html_content
    }

    try:
        req = Request(
            url="https://api.resend.com/emails",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "User-Agent": "CyberUndo-Backend/1.0"
            },
            method="POST"
        )

        with urlopen(req, timeout=10) as response:
            resp_body = response.read().decode("utf-8")
            data = json.loads(resp_body) if resp_body else {}
            msg_id = data.get("id", "resend_ok")
            logger.info(f"[Email Service] Successfully dispatched email to recipient. Message ID: {msg_id}")
            return {
                "success": True,
                "id": msg_id,
                "message": f"Notification email sent to {recipient_email}."
            }

    except HTTPError as e:
        err_body = e.read().decode("utf-8") if e.fp else ""
        logger.error(f"[Email Service] Resend API HTTP error {e.code}: {err_body}")
        try:
            parsed_err = json.loads(err_body)
            error_message = parsed_err.get("message", f"HTTP {e.code}")
        except Exception:
            error_message = f"HTTP {e.code}: {err_body or e.reason}"
        return {
            "success": False,
            "error": error_message,
            "code": e.code
        }

    except URLError as e:
        logger.error(f"[Email Service] Network connection error: {e.reason}")
        return {
            "success": False,
            "error": f"Email gateway network error: {str(e.reason)}"
        }

    except Exception as e:
        logger.error(f"[Email Service] Unexpected error during email dispatch: {str(e)}")
        return {
            "success": False,
            "error": f"Email delivery failed: {str(e)}"
        }
