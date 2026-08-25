import os
import re
import json
import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from flask import current_app

logger = logging.getLogger("cyberundo.email")


def _parse_sender(from_email: str) -> tuple:
    """
    Extract (display_name, email_address) from strings like
    'CyberUndo Security <security@domain.com>' or 'security@domain.com'.
    """
    cleaned = (from_email or "").strip()
    match = re.match(r"^(.*?)\s*<([^>]+)>$", cleaned)
    if match:
        name = match.group(1).strip().strip('"').strip("'")
        email_addr = match.group(2).strip()
        return (name or "CyberUndo Security", email_addr)
    return ("CyberUndo Security", cleaned or "security@cyberundo.io")


def _build_html_template(owner_name: str, filename: str, share_url: str, expires_at: str = None, allow_download: bool = True) -> str:
    """Build the responsive, dark/cyan branded CyberUndo HTML email template."""
    permission_badge = "View & Download" if allow_download else "View Only (Download Restricted)"
    expiry_badge = f"Expires on {expires_at}" if expires_at else "No expiration set"

    return f"""
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


def _send_via_brevo(api_key: str, from_email: str, recipient_email: str, subject: str, html_content: str) -> dict:
    """Dispatch transactional email via Brevo REST API (Preferred: sends to arbitrary recipients with zero domain cost)."""
    sender_name, sender_addr = _parse_sender(from_email)
    
    payload = {
        "sender": {
            "name": sender_name,
            "email": sender_addr
        },
        "to": [
            {
                "email": recipient_email,
                "name": "Protected Recipient"
            }
        ],
        "subject": subject,
        "htmlContent": html_content
    }

    try:
        req = Request(
            url="https://api.brevo.com/v3/smtp/email",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "api-key": api_key,
                "Content-Type": "application/json",
                "accept": "application/json",
                "User-Agent": "CyberUndo-Backend/1.0"
            },
            method="POST"
        )

        with urlopen(req, timeout=10) as response:
            resp_body = response.read().decode("utf-8")
            data = json.loads(resp_body) if resp_body else {}
            msg_id = data.get("messageId", "brevo_ok")
            logger.info(f"[Email Service: Brevo] Successfully dispatched email to recipient. Message ID: {msg_id}")
            return {
                "success": True,
                "provider": "Brevo",
                "id": msg_id,
                "message": f"Notification email delivered via Brevo to {recipient_email}."
            }

    except HTTPError as e:
        err_body = e.read().decode("utf-8") if e.fp else ""
        logger.error(f"[Email Service: Brevo] HTTP error {e.code}: {err_body}")
        try:
            parsed_err = json.loads(err_body)
            error_message = parsed_err.get("message", f"HTTP {e.code}")
        except Exception:
            error_message = f"HTTP {e.code}: {err_body or e.reason}"
        return {
            "success": False,
            "provider": "Brevo",
            "error": f"Brevo API error: {error_message}",
            "code": e.code
        }

    except URLError as e:
        logger.error(f"[Email Service: Brevo] Network connection error: {e.reason}")
        return {
            "success": False,
            "provider": "Brevo",
            "error": f"Brevo gateway network error: {str(e.reason)}"
        }

    except Exception as e:
        logger.error(f"[Email Service: Brevo] Unexpected dispatch error: {str(e)}")
        return {
            "success": False,
            "provider": "Brevo",
            "error": f"Brevo delivery failed: {str(e)}"
        }


def _send_via_smtp(smtp_user: str, smtp_pass: str, smtp_host: str, smtp_port: int, from_email: str, recipient_email: str, subject: str, html_content: str) -> dict:
    """Dispatch transactional email via standard SMTP / Gmail (Sends to arbitrary recipients with zero domain cost)."""
    sender_name, sender_addr = _parse_sender(from_email)
    
    # Gmail SMTP requires the From address to match the authenticated Gmail account or alias
    if "resend.dev" in sender_addr or not sender_addr:
        sender_addr = smtp_user

    from_header = f"{sender_name} <{sender_addr}>" if sender_name else sender_addr

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = from_header
    msg["To"] = recipient_email

    # Attach HTML payload
    part = MIMEText(html_content, "html", "utf-8")
    msg.attach(part)

    try:
        if smtp_port == 465:
            server = smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=12)
        else:
            server = smtplib.SMTP(smtp_host, smtp_port, timeout=12)
            server.starttls()

        server.login(smtp_user, smtp_pass)
        server.send_message(msg)
        server.quit()

        logger.info(f"[Email Service: SMTP] Successfully dispatched email to {recipient_email} via {smtp_host}")
        return {
            "success": True,
            "provider": "SMTP",
            "id": f"smtp_{os.urandom(4).hex()}",
            "message": f"Notification email delivered via SMTP to {recipient_email}."
        }

    except smtplib.SMTPAuthenticationError as e:
        logger.error(f"[Email Service: SMTP] Authentication failed: {e}")
        return {
            "success": False,
            "provider": "SMTP",
            "error": f"SMTP Authentication failed for {smtp_user}. Verify credentials / App Password.",
            "code": 401
        }
    except Exception as e:
        logger.error(f"[Email Service: SMTP] Dispatch error: {str(e)}")
        return {
            "success": False,
            "provider": "SMTP",
            "error": f"SMTP delivery failed: {str(e)}"
        }


def _send_via_resend(api_key: str, from_email: str, recipient_email: str, subject: str, html_content: str) -> dict:
    """Dispatch transactional email via Resend REST API (Fallback provider)."""
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
            logger.info(f"[Email Service: Resend] Successfully dispatched email. Message ID: {msg_id}")
            return {
                "success": True,
                "provider": "Resend",
                "id": msg_id,
                "message": f"Notification email delivered via Resend to {recipient_email}."
            }

    except HTTPError as e:
        err_body = e.read().decode("utf-8") if e.fp else ""
        logger.error(f"[Email Service: Resend] HTTP error {e.code}: {err_body}")
        try:
            parsed_err = json.loads(err_body)
            error_message = parsed_err.get("message", f"HTTP {e.code}")
        except Exception:
            error_message = f"HTTP {e.code}: {err_body or e.reason}"
        return {
            "success": False,
            "provider": "Resend",
            "error": f"Resend API error: {error_message}",
            "code": e.code
        }

    except URLError as e:
        logger.error(f"[Email Service: Resend] Network connection error: {e.reason}")
        return {
            "success": False,
            "provider": "Resend",
            "error": f"Resend network error: {str(e.reason)}"
        }

    except Exception as e:
        logger.error(f"[Email Service: Resend] Unexpected dispatch error: {str(e)}")
        return {
            "success": False,
            "provider": "Resend",
            "error": f"Resend delivery failed: {str(e)}"
        }


def send_share_email(recipient_email: str, owner_name: str, filename: str, share_url: str, expires_at: str = None, allow_download: bool = True) -> dict:
    """
    Multi-Provider Transactional Email Dispatcher for CyberUndo.
    
    Priority Order:
    1. SMTP / Gmail (SMTP_USER + SMTP_PASS) - Preferred: Free arbitrary recipient delivery with zero domain cost
    2. Brevo REST API (BREVO_API_KEY) - Free arbitrary recipient delivery without paid domain
    3. Resend REST API (RESEND_API_KEY) - Fallback provider
    
    Returns dict:
    - {"success": True/False, "message": "...", "provider": "...", "id": "...", "error": "..."}
    """
    smtp_user = current_app.config.get("SMTP_USER", "").strip()
    smtp_pass = current_app.config.get("SMTP_PASS", "").strip()
    brevo_api_key = current_app.config.get("BREVO_API_KEY", "").strip()
    resend_api_key = current_app.config.get("RESEND_API_KEY", "").strip()

    from_email = current_app.config.get("EMAIL_FROM", "CyberUndo Security <onboarding@resend.dev>").strip()
    subject = f"Protected File Shared: {filename} from {owner_name}"
    html_content = _build_html_template(owner_name, filename, share_url, expires_at, allow_download)

    # 1. Preferred Production: SMTP / Gmail
    if smtp_user and smtp_pass:
        smtp_host = current_app.config.get("SMTP_HOST", "smtp.gmail.com")
        smtp_port = current_app.config.get("SMTP_PORT", 587)
        logger.info(f"[Email Service] Dispatching via SMTP ({smtp_host}) to {recipient_email}")
        return _send_via_smtp(smtp_user, smtp_pass, smtp_host, smtp_port, from_email, recipient_email, subject, html_content)

    # 2. Priority 2: Brevo REST API (if configured)
    if brevo_api_key:
        logger.info(f"[Email Service] Dispatching via Brevo to {recipient_email}")
        return _send_via_brevo(brevo_api_key, from_email, recipient_email, subject, html_content)

    # 3. Priority 3 / Fallback: Resend REST API (if configured)
    if resend_api_key:
        logger.info(f"[Email Service] Dispatching via Resend to {recipient_email}")
        return _send_via_resend(resend_api_key, from_email, recipient_email, subject, html_content)

    # 4. No email provider credentials configured
    logger.error("[Email Service] No email provider configured (SMTP_USER/PASS, BREVO_API_KEY, or RESEND_API_KEY).")
    return {
        "success": False,
        "error": "Email delivery failed: No email provider configured on server. Please configure SMTP_USER + SMTP_PASS, BREVO_API_KEY, or RESEND_API_KEY in Render environment variables.",
        "code": 500
    }
