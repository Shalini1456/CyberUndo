"""
CyberUndo Secure Sharing + Revoke Module Unit & Integration Tests (Member 2)
Tests:
1. Create share link with recipient email, expiry, allow_download & server-side token generation
2. Email service formatting & recipient delivery handling
3. Email delivery failure error handling
4. Open share link (public token validation & real metadata)
5. Record VIEWED event and view_count increment
6. Real file download streaming
7. Record DOWNLOADED event and download_count increment
8. Individual Revoke endpoint
9. Revoked link -> HTTP 403 Forbidden
10. Expired link -> HTTP 403 Forbidden
11. Revoke All endpoint (batch killswitch)
12. Security checks (unauthorized revocation blocked, private paths hidden)
13. Existing auth & file vault endpoints regression check
"""

import os
import io
import json
import unittest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
from app import create_app
from database import db
from models import User, File, SharedAccess, ActivityLog
from auth import hash_password, generate_jwt
from config import Config

class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), "test_uploads")
    JWT_SECRET_KEY = "test-secret-key-12345"
    RESEND_API_KEY = "re_test_dummy_key_123"
    EMAIL_FROM = "CyberUndo Security <onboarding@resend.dev>"
    FRONTEND_URL = "https://cyber-undo.vercel.app"

class TestSecureSharingRevoke(unittest.TestCase):

    def setUp(self):
        self.app = create_app(TestConfig)
        self.client = self.app.test_client()
        self.ctx = self.app.app_context()
        self.ctx.push()

        db.create_all()
        os.makedirs(self.app.config["UPLOAD_FOLDER"], exist_ok=True)

        # Create owner user
        self.owner = User(
            name="Alice Security Lead",
            email="alice@cyberundo.io",
            password_hash=hash_password("Password123!")
        )
        db.session.add(self.owner)

        # Create secondary unauthorized user
        self.other_user = User(
            name="Bob Attacker",
            email="bob@external.io",
            password_hash=hash_password("Password123!")
        )
        db.session.add(self.other_user)
        db.session.commit()

        # Generate JWT tokens
        self.owner_token = generate_jwt(self.owner.id, self.owner.email)
        self.auth_headers = {"Authorization": f"Bearer {self.owner_token}"}

        self.other_token = generate_jwt(self.other_user.id, self.other_user.email)
        self.other_headers = {"Authorization": f"Bearer {self.other_token}"}

        # Create sample file on disk and in database
        self.sample_filename = "Confidential_Q3_Financials.pdf"
        self.sample_stored_name = "test_uuid_Confidential_Q3_Financials.pdf"
        self.sample_file_path = os.path.join(self.app.config["UPLOAD_FOLDER"], self.sample_stored_name)
        with open(self.sample_file_path, "wb") as f:
            f.write(b"%PDF-1.4 CyberUndo Secure Real File Binary Stream Payload")

        self.file = File(
            owner_id=self.owner.id,
            filename=self.sample_filename,
            stored_filename=self.sample_stored_name,
            file_path=self.sample_file_path,
            status="active"
        )
        db.session.add(self.file)
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()
        if os.path.exists(self.sample_file_path):
            try:
                os.remove(self.sample_file_path)
            except OSError:
                pass

    # -------------------------------------------------------------------------
    # 1. CREATE SHARE & SERVER-SIDE TOKEN GENERATION
    # -------------------------------------------------------------------------
    @patch("email_service.send_share_email")
    def test_01_create_share_server_token(self, mock_email):
        mock_email.return_value = {"success": True, "id": "resend_123", "message": "Email sent"}
        
        res = self.client.post("/api/shares", headers=self.auth_headers, json={
            "file_id": self.file.id,
            "recipient_email": "recipient@partnercorp.io",
            "expiry": "24h",
            "allow_download": True
        })
        self.assertEqual(res.status_code, 201)
        data = res.get_json()
        self.assertTrue(data["success"])
        token = data["data"]["share_token"]
        self.assertTrue(token.startswith("cu-share-"))
        self.assertEqual(len(token), 25)  # "cu-share-" + 16 chars
        self.assertEqual(data["data"]["share"]["recipient_email"], "recipient@partnercorp.io")
        self.assertEqual(data["data"]["share"]["status"], "active")
        self.assertTrue(data["data"]["share"]["allow_download"])

        # Check mock email call
        mock_email.assert_called_once()
        args, kwargs = mock_email.call_args
        self.assertEqual(kwargs["recipient_email"], "recipient@partnercorp.io")
        self.assertIn(token, kwargs["share_url"])

    # -------------------------------------------------------------------------
    # 2. EMAIL DELIVERY FAILURE HANDLING
    # -------------------------------------------------------------------------
    @patch("email_service.send_share_email")
    def test_02_email_delivery_failure_reported(self, mock_email):
        mock_email.return_value = {
            "success": False,
            "error": "Resend API key rejected",
            "code": 401
        }

        res = self.client.post("/api/shares", headers=self.auth_headers, json={
            "file_id": self.file.id,
            "recipient_email": "recipient@partnercorp.io",
            "expiry": "24h"
        })
        self.assertEqual(res.status_code, 502)
        data = res.get_json()
        self.assertFalse(data["success"])
        self.assertIn("Failed to deliver secure email", data["message"])

        # DB share must have been rolled back
        shares = SharedAccess.query.filter_by(file_id=self.file.id).all()
        self.assertEqual(len(shares), 0)

    def test_02b_missing_api_key_reports_failure(self):
        self.app.config["RESEND_API_KEY"] = ""
        res = self.client.post("/api/shares", headers=self.auth_headers, json={
            "file_id": self.file.id,
            "recipient_email": "recipient@partnercorp.io",
            "expiry": "24h"
        })
        self.assertEqual(res.status_code, 502)
        data = res.get_json()
        self.assertFalse(data["success"])
        self.assertIn("RESEND_API_KEY is not configured", data["message"])
        self.app.config["RESEND_API_KEY"] = "re_test_dummy_key_123"

    # -------------------------------------------------------------------------
    # 3. OPEN SHARE LINK (PUBLIC TOKEN GET)
    # -------------------------------------------------------------------------
    @patch("email_service.send_share_email")
    def test_03_open_share_link(self, mock_email):
        mock_email.return_value = {"success": True}
        create_res = self.client.post("/api/shares", headers=self.auth_headers, json={
            "file_id": self.file.id,
            "recipient_email": "recipient@partnercorp.io",
            "expiry": "24h",
            "allow_download": True
        })
        token = create_res.get_json()["data"]["share_token"]

        # Public access without auth header
        res = self.client.get(f"/api/shares/{token}")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data["success"])
        self.assertEqual(data["data"]["share"]["share_token"], token)
        self.assertEqual(data["data"]["share"]["file"]["filename"], self.sample_filename)
        self.assertEqual(data["data"]["share"]["recipient_email"], "recipient@partnercorp.io")

    # -------------------------------------------------------------------------
    # 4. VIEWED EVENT
    # -------------------------------------------------------------------------
    @patch("email_service.send_share_email")
    def test_04_record_viewed_event(self, mock_email):
        mock_email.return_value = {"success": True}
        create_res = self.client.post("/api/shares", headers=self.auth_headers, json={
            "file_id": self.file.id,
            "recipient_email": "recipient@partnercorp.io",
            "expiry": "24h"
        })
        token = create_res.get_json()["data"]["share_token"]

        # Record view
        res = self.client.post(f"/api/shares/{token}/view")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data["success"])
        self.assertEqual(data["data"]["view_count"], 1)

        # Check DB audit entry
        share = SharedAccess.query.filter_by(share_token=token).first()
        self.assertEqual(share.view_count, 1)
        self.assertIsNotNone(share.first_viewed_at)

    # -------------------------------------------------------------------------
    # 5 & 6. REAL DOWNLOAD & DOWNLOADED EVENT TRACKING
    # -------------------------------------------------------------------------
    @patch("email_service.send_share_email")
    def test_05_and_06_real_download_and_tracking(self, mock_email):
        mock_email.return_value = {"success": True}
        create_res = self.client.post("/api/shares", headers=self.auth_headers, json={
            "file_id": self.file.id,
            "recipient_email": "recipient@partnercorp.io",
            "expiry": "24h",
            "allow_download": True
        })
        token = create_res.get_json()["data"]["share_token"]

        # Download real physical file
        res = self.client.get(f"/api/shares/{token}/download")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data, b"%PDF-1.4 CyberUndo Secure Real File Binary Stream Payload")

        # Check increment in download count
        share = SharedAccess.query.filter_by(share_token=token).first()
        self.assertEqual(share.download_count, 1)
        self.assertIsNotNone(share.last_download_at)

    # -------------------------------------------------------------------------
    # 7. DOWNLOAD PERMISSION POLICY (allow_download=False -> 403)
    # -------------------------------------------------------------------------
    @patch("email_service.send_share_email")
    def test_07_download_restricted_policy(self, mock_email):
        mock_email.return_value = {"success": True}
        create_res = self.client.post("/api/shares", headers=self.auth_headers, json={
            "file_id": self.file.id,
            "recipient_email": "recipient@partnercorp.io",
            "expiry": "24h",
            "allow_download": False
        })
        token = create_res.get_json()["data"]["share_token"]

        # Attempt download on view-only share
        res = self.client.get(f"/api/shares/{token}/download")
        self.assertEqual(res.status_code, 403)

    # -------------------------------------------------------------------------
    # 8. INDIVIDUAL REVOKE & HTTP 403 ENFORCEMENT
    # -------------------------------------------------------------------------
    @patch("email_service.send_share_email")
    def test_08_revoke_and_403_enforcement(self, mock_email):
        mock_email.return_value = {"success": True}
        create_res = self.client.post("/api/shares", headers=self.auth_headers, json={
            "file_id": self.file.id,
            "recipient_email": "recipient@partnercorp.io",
            "expiry": "24h",
            "allow_download": True
        })
        token = create_res.get_json()["data"]["share_token"]

        # Revoke share link
        revoke_res = self.client.post(f"/api/shares/{token}/revoke", headers=self.auth_headers)
        self.assertEqual(revoke_res.status_code, 200)
        self.assertEqual(revoke_res.get_json()["data"]["share"]["status"], "revoked")

        # GET info must return 403
        get_res = self.client.get(f"/api/shares/{token}")
        self.assertEqual(get_res.status_code, 403)
        self.assertEqual(get_res.get_json()["status"], "revoked")

        # View must return 403
        view_res = self.client.post(f"/api/shares/{token}/view")
        self.assertEqual(view_res.status_code, 403)

        # Download must return 403
        dl_res = self.client.get(f"/api/shares/{token}/download")
        self.assertEqual(dl_res.status_code, 403)

    # -------------------------------------------------------------------------
    # 9. EXPIRED LINK -> HTTP 403 FORBIDDEN
    # -------------------------------------------------------------------------
    def test_09_expired_link_403(self):
        expired_token = "cu-share-expired-token-123"
        expired_share = SharedAccess(
            file_id=self.file.id,
            owner_id=self.owner.id,
            recipient_email="expired@partner.com",
            share_token=expired_token,
            status="active",
            created_at=datetime.utcnow() - timedelta(days=2),
            expires_at=datetime.utcnow() - timedelta(days=1)
        )
        db.session.add(expired_share)
        db.session.commit()

        # GET info must return 403
        res = self.client.get(f"/api/shares/{expired_token}")
        self.assertEqual(res.status_code, 403)
        self.assertEqual(res.get_json()["status"], "expired")

        # Download must return 403
        dl_res = self.client.get(f"/api/shares/{expired_token}/download")
        self.assertEqual(dl_res.status_code, 403)

    # -------------------------------------------------------------------------
    # 10. REVOKE ALL SHARES (BATCH KILLSWITCH)
    # -------------------------------------------------------------------------
    @patch("email_service.send_share_email")
    def test_10_revoke_all_shares(self, mock_email):
        mock_email.return_value = {"success": True}
        tokens = []
        for i in range(3):
            r = self.client.post("/api/shares", headers=self.auth_headers, json={
                "file_id": self.file.id,
                "recipient_email": f"partner_{i}@corp.io",
                "expiry": "24h"
            })
            tokens.append(r.get_json()["data"]["share_token"])

        # Revoke All
        revoke_all_res = self.client.post("/api/shares/revoke-all", headers=self.auth_headers, json={
            "file_id": self.file.id
        })
        self.assertEqual(revoke_all_res.status_code, 200)
        self.assertEqual(revoke_all_res.get_json()["data"]["revoked_count"], 3)

        # Confirm all 3 return 403
        for t in tokens:
            check_res = self.client.get(f"/api/shares/{t}")
            self.assertEqual(check_res.status_code, 403)

    # -------------------------------------------------------------------------
    # 11. SECURITY: UNAUTHORIZED USER CANNOT REVOKE OWNER SHARE
    # -------------------------------------------------------------------------
    @patch("email_service.send_share_email")
    def test_11_unauthorized_user_cannot_revoke(self, mock_email):
        mock_email.return_value = {"success": True}
        create_res = self.client.post("/api/shares", headers=self.auth_headers, json={
            "file_id": self.file.id,
            "recipient_email": "recipient@partnercorp.io",
            "expiry": "24h"
        })
        token = create_res.get_json()["data"]["share_token"]

        # Attempt revoke by another user
        res = self.client.post(f"/api/shares/{token}/revoke", headers=self.other_headers)
        self.assertEqual(res.status_code, 404)

        # Share must still be active
        share = SharedAccess.query.filter_by(share_token=token).first()
        self.assertEqual(share.status, "active")

    # -------------------------------------------------------------------------
    # 12. REGRESSION CHECK: EXISTING AUTH & FILE VAULT ENDPOINTS
    # -------------------------------------------------------------------------
    def test_12_existing_functionality_regression(self):
        # 1. Health
        r_health = self.client.get("/api/health")
        self.assertEqual(r_health.status_code, 200)

        # 2. Auth me
        r_me = self.client.get("/api/auth/me", headers=self.auth_headers)
        self.assertEqual(r_me.status_code, 200)
        self.assertEqual(r_me.get_json()["data"]["user"]["email"], "alice@cyberundo.io")

        # 3. File upload
        upload_data = {
            "file": (io.BytesIO(b"Regression Upload Content"), "new_doc.txt")
        }
        r_up = self.client.post("/api/files/upload", headers=self.auth_headers, data=upload_data, content_type="multipart/form-data")
        self.assertEqual(r_up.status_code, 201)
        new_file_id = r_up.get_json()["data"]["file"]["id"]

        # 4. List files
        r_list = self.client.get("/api/files", headers=self.auth_headers)
        self.assertEqual(r_list.status_code, 200)
        self.assertGreaterEqual(len(r_list.get_json()["data"]["files"]), 2)

        # 5. Get file
        r_get = self.client.get(f"/api/files/{new_file_id}", headers=self.auth_headers)
        self.assertEqual(r_get.status_code, 200)

        # 6. Download file
        r_dl = self.client.get(f"/api/files/{new_file_id}/download", headers=self.auth_headers)
        self.assertEqual(r_dl.status_code, 200)
        self.assertEqual(r_dl.data, b"Regression Upload Content")

    # -------------------------------------------------------------------------
    # 13. FRONTEND UI & STATIC ASSET DELIVERY ON RENDER
    # -------------------------------------------------------------------------
    def test_13_frontend_static_serving(self):
        # Root route GET / must return 200 and serve HTML
        r_root = self.client.get("/")
        self.assertEqual(r_root.status_code, 200)
        self.assertIn(b"CyberUndo", r_root.data)

        # Recipient route GET /share must return 200 and serve share.html
        r_share = self.client.get("/share")
        self.assertEqual(r_share.status_code, 200)
        self.assertIn(b"CyberUndo", r_share.data)

        # Static assets GET /css/style.css
        r_css = self.client.get("/css/style.css")
        self.assertEqual(r_css.status_code, 200)


if __name__ == "__main__":
    unittest.main()

