"""
CyberUndo Secure Sharing + Revoke Module Unit & Integration Tests (Member 2)
Tests:
1. Create share link with recipient email, expiry, allow_download
2. Open share link (public token validation)
3. Record VIEWED event and view_count increment
4. Secure file download when allow_download=True
5. Record DOWNLOADED event and download_count increment
6. Individual Revoke endpoint
7. Revoked link -> HTTP 403 Forbidden
8. Expired link -> HTTP 403 Forbidden
9. Revoke All endpoint (batch killswitch)
10. Existing auth & file vault endpoints regression check
"""

import os
import io
import unittest
from datetime import datetime, timedelta
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
            name="Alice Security",
            email="alice@cyberundo.io",
            password_hash=hash_password("Password123!")
        )
        db.session.add(self.owner)
        db.session.commit()

        # Generate JWT token
        self.owner_token = generate_jwt(self.owner.id, self.owner.email)
        self.auth_headers = {"Authorization": f"Bearer {self.owner_token}"}

        # Create sample file on disk and in database
        self.sample_filename = "Confidential_Specs.pdf"
        self.sample_stored_name = "test_uuid_Confidential_Specs.pdf"
        self.sample_file_path = os.path.join(self.app.config["UPLOAD_FOLDER"], self.sample_stored_name)
        with open(self.sample_file_path, "wb") as f:
            f.write(b"%PDF-1.4 CyberUndo Secure Test Payload Content")

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
    # 1. CREATE SHARE
    # -------------------------------------------------------------------------
    def test_01_create_share(self):
        res = self.client.post("/api/shares", headers=self.auth_headers, json={
            "file_id": self.file.id,
            "recipient_email": "alex.morgan@partnercorp.io",
            "expiry": "24h",
            "allow_download": True
        })
        self.assertEqual(res.status_code, 201)
        data = res.get_json()
        self.assertTrue(data["success"])
        self.assertIn("share_token", data["data"])
        self.assertEqual(data["data"]["share"]["recipient_email"], "alex.morgan@partnercorp.io")
        self.assertEqual(data["data"]["share"]["status"], "active")
        self.assertTrue(data["data"]["share"]["allow_download"])

    # -------------------------------------------------------------------------
    # 2. OPEN SHARE LINK (PUBLIC TOKEN GET)
    # -------------------------------------------------------------------------
    def test_02_open_share_link(self):
        # Create share first
        create_res = self.client.post("/api/shares", headers=self.auth_headers, json={
            "file_id": self.file.id,
            "recipient_email": "alex.morgan@partnercorp.io",
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

    # -------------------------------------------------------------------------
    # 3. VIEWED EVENT
    # -------------------------------------------------------------------------
    def test_03_record_viewed_event(self):
        create_res = self.client.post("/api/shares", headers=self.auth_headers, json={
            "file_id": self.file.id,
            "recipient_email": "alex.morgan@partnercorp.io",
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
    # 4 & 5. DOWNLOAD & DOWNLOADED EVENT
    # -------------------------------------------------------------------------
    def test_04_and_05_download_and_tracking(self):
        create_res = self.client.post("/api/shares", headers=self.auth_headers, json={
            "file_id": self.file.id,
            "recipient_email": "alex.morgan@partnercorp.io",
            "expiry": "24h",
            "allow_download": True
        })
        token = create_res.get_json()["data"]["share_token"]

        # Download file
        res = self.client.get(f"/api/shares/{token}/download")
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"CyberUndo Secure Test Payload Content", res.data)

        # Check increment in download count
        share = SharedAccess.query.filter_by(share_token=token).first()
        self.assertEqual(share.download_count, 1)
        self.assertIsNotNone(share.last_download_at)

    # -------------------------------------------------------------------------
    # 6 & 7. INDIVIDUAL REVOKE & HTTP 403 FORBIDDEN
    # -------------------------------------------------------------------------
    def test_06_and_07_revoke_and_403_enforcement(self):
        create_res = self.client.post("/api/shares", headers=self.auth_headers, json={
            "file_id": self.file.id,
            "recipient_email": "alex.morgan@partnercorp.io",
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
    # 8. EXPIRED LINK -> HTTP 403 FORBIDDEN
    # -------------------------------------------------------------------------
    def test_08_expired_link_403(self):
        # Manually create already-expired share
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
    # 9. REVOKE ALL SHARES
    # -------------------------------------------------------------------------
    def test_09_revoke_all_shares(self):
        # Create 3 active shares
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
    # 10. REGRESSION CHECK: EXISTING AUTH & FILE VAULT ENDPOINTS
    # -------------------------------------------------------------------------
    def test_10_existing_functionality_regression(self):
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


if __name__ == "__main__":
    unittest.main()
