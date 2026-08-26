"""
Comprehensive Unit & Integration Test Suite for Member 4 Integration
---------------------------------------------------------------------
Tests:
1. Risk Engine (scoring, factors, recommendations, levels)
2. Blast Radius (exposure metrics, dynamic exposure chain)
3. Activity Tracker Service (logging, validation, chronological retrieval)
4. REST API Routes (/api/risk/analyze, /api/blast-radius/analyze, /api/activity/*)
5. End-to-End integration with real CyberUndo File & Share lifecycle
"""

import os
import json
import unittest
from unittest.mock import patch

from backend.app import create_app
from backend.database import db
from backend.models import User, File, SharedAccess, ActivityLog
from backend.services.risk_engine import (
    analyze_risk,
    get_sensitivity_score,
    get_recipient_score,
    get_download_score,
    get_expiry_score,
    get_risk_level
)
from backend.services.blast_radius import calculate_blast_radius
from backend.services.activity_service import log_activity, get_file_activity


class Member4IntegrationTests(unittest.TestCase):
    def setUp(self):
        os.environ["DATABASE_URL"] = "sqlite:///:memory:"
        self.app = create_app()
        self.app.config["TESTING"] = True
        self.app.config["JWT_SECRET_KEY"] = "member4-test-jwt-secret"
        self.app.config["BREVO_API_KEY"] = "xkeysib-mock-test-key"
        self.client = self.app.test_client()

        with self.app.app_context():
            db.create_all()

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()

    # -------------------------------------------------------------------------
    # 1. RISK ENGINE TESTS
    # -------------------------------------------------------------------------
    def test_01_risk_engine_scoring_rules(self):
        # Sensitivity
        self.assertEqual(get_sensitivity_score("Public")[0], 10)
        self.assertEqual(get_sensitivity_score("Internal")[0], 25)
        self.assertEqual(get_sensitivity_score("Confidential")[0], 50)
        self.assertEqual(get_sensitivity_score("Sensitive")[0], 70)

        # Recipients
        self.assertEqual(get_recipient_score(1)[0], 5)
        self.assertEqual(get_recipient_score(3)[0], 15)
        self.assertEqual(get_recipient_score(10)[0], 25)

        # Download
        self.assertEqual(get_download_score(True)[0], 15)
        self.assertEqual(get_download_score(False)[0], 0)

        # Expiry
        self.assertEqual(get_expiry_score("1 Hour")[0], 0)
        self.assertEqual(get_expiry_score("1 Day")[0], 5)
        self.assertEqual(get_expiry_score("7 Days")[0], 10)
        self.assertEqual(get_expiry_score("Never")[0], 20)

        # Risk Levels
        self.assertEqual(get_risk_level(25), "LOW")
        self.assertEqual(get_risk_level(45), "MEDIUM")
        self.assertEqual(get_risk_level(75), "HIGH")
        self.assertEqual(get_risk_level(95), "CRITICAL")

    def test_02_risk_engine_full_analysis(self):
        report = analyze_risk(
            file_id="101",
            file_name="Q3_Financials.pdf",
            sensitivity="Confidential",  # 50
            recipient_count=3,           # 15
            download_allowed=True,       # 15
            expiry="Never"               # 20 -> Total 100
        )
        self.assertEqual(report["file_id"], "101")
        self.assertEqual(report["risk_score"], 100)
        self.assertEqual(report["risk_level"], "CRITICAL")
        self.assertEqual(len(report["risk_factors"]), 4)
        self.assertIn("Limit the number of recipients", report["recommendations"])
        self.assertIn("Disable download permission", report["recommendations"])
        self.assertIn("Set an expiry time", report["recommendations"])

    # -------------------------------------------------------------------------
    # 2. BLAST RADIUS TESTS
    # -------------------------------------------------------------------------
    def test_03_blast_radius_exposure_chain(self):
        blast = calculate_blast_radius(
            file_id="101",
            file_name="Q3_Financials.pdf",
            sensitivity="Confidential",
            recipient_count=3,
            download_allowed=True,
            expiry="Never"
        )
        self.assertEqual(blast["risk_level"], "CRITICAL")
        self.assertEqual(blast["estimated_exposure"], "CRITICAL")
        self.assertEqual(blast["download_risk"], "ENABLED")
        self.assertEqual(blast["link_expiry_risk"], "UNLIMITED")
        self.assertIn("3 Recipients", blast["exposure_chain"])
        self.assertIn("Download Enabled", blast["exposure_chain"])
        self.assertIn("Unknown Exposure", blast["exposure_chain"])

    # -------------------------------------------------------------------------
    # 3. ACTIVITY TRACKER SERVICE TESTS
    # -------------------------------------------------------------------------
    def test_04_activity_tracker_logging_and_retrieval(self):
        with self.app.app_context():
            # Log multiple events in chronological order
            log_activity(file_id="42", file_name="DocA.pdf", actor="owner@corp.io", event_type="FILE_UPLOADED", details="Uploaded to vault")
            log_activity(file_id="42", file_name="DocA.pdf", actor="owner@corp.io", event_type="FILE_SHARED", details="Shared with client")
            log_activity(file_id="42", file_name="DocA.pdf", actor="client@external.com", event_type="FILE_VIEWED", details="Viewed in browser")
            log_activity(file_id="42", file_name="DocA.pdf", actor="client@external.com", event_type="FILE_DOWNLOADED", details="Downloaded copy")

            history = get_file_activity("42")
            self.assertEqual(history["total_events"], 4)
            self.assertEqual(history["file_name"], "DocA.pdf")
            self.assertEqual(history["latest_event"]["event_type"], "FILE_DOWNLOADED")
            self.assertEqual(history["activities"][0]["event_type"], "FILE_UPLOADED")
            self.assertEqual(history["activities"][1]["event_type"], "FILE_SHARED")
            self.assertEqual(history["activities"][2]["event_type"], "FILE_VIEWED")
            self.assertEqual(history["activities"][3]["event_type"], "FILE_DOWNLOADED")

    def test_05_activity_tracker_invalid_event_rejection(self):
        with self.assertRaises(ValueError):
            log_activity(file_id="42", file_name="DocA.pdf", event_type="INVALID_HACKER_EVENT")

    # -------------------------------------------------------------------------
    # 4. REST API ROUTES TESTS
    # -------------------------------------------------------------------------
    def test_06_api_risk_analyze_endpoint(self):
        res = self.client.post("/api/risk/analyze", json={
            "file_id": "1",
            "file_name": "Strategic_Plan.pdf",
            "sensitivity": "Sensitive",
            "recipient_count": 1,
            "download_allowed": False,
            "expiry": "1 Hour"
        })
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data["file_id"], "1")
        self.assertEqual(data["risk_score"], 75)  # 70 + 5 + 0 + 0 = 75
        self.assertEqual(data["risk_level"], "HIGH")

    def test_07_api_blast_radius_analyze_endpoint(self):
        res = self.client.post("/api/blast-radius/analyze", json={
            "file_id": "1",
            "file_name": "Strategic_Plan.pdf",
            "sensitivity": "Public",
            "recipient_count": 1,
            "download_allowed": False,
            "expiry": "1 Hour"
        })
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data["risk_level"], "LOW")
        self.assertEqual(data["download_risk"], "DISABLED")
        self.assertIn("Controlled Access", data["exposure_chain"])

    def test_08_api_activity_endpoints(self):
        # Post activity
        log_res = self.client.post("/api/activity/log", json={
            "file_id": "99",
            "file_name": "Audit_Report.pdf",
            "actor": "auditor@sec.gov",
            "event_type": "FILE_VIEWED",
            "details": "Viewed audit report"
        })
        self.assertEqual(log_res.status_code, 201)
        log_data = log_res.get_json()
        self.assertEqual(log_data["file_id"], "99")
        self.assertEqual(log_data["event_type"], "FILE_VIEWED")

        # Get activity history
        get_res = self.client.get("/api/activity/99")
        self.assertEqual(get_res.status_code, 200)
        history_data = get_res.get_json()
        self.assertEqual(history_data["total_events"], 1)
        self.assertEqual(history_data["latest_event"]["actor"], "auditor@sec.gov")

    # -------------------------------------------------------------------------
    # 5. END-TO-END TELEMETRY HOOKING WITH REAL SHARES
    # -------------------------------------------------------------------------
    @patch("backend.services.activity_service.has_app_context", return_value=True)
    def test_09_real_share_lifecycle_populates_member4_activity_logs(self, mock_ctx):
        with self.app.app_context():
            # Create user & file
            user = User(name="Alice", email="alice@cyberundo.io", password_hash="hash")
            db.session.add(user)
            db.session.commit()

            file_rec = File(owner_id=user.id, filename="Confidential_Report.pdf", stored_filename="stored_1.pdf", file_path="dummy", status="active")
            db.session.add(file_rec)
            db.session.commit()

            # Create Share
            share = SharedAccess(
                file_id=file_rec.id,
                owner_id=user.id,
                recipient_email="client@partner.com",
                share_token="cu-share-test12345",
                permission="download",
                allow_download=True,
                expiry_option="24h"
            )
            db.session.add(share)

            # Record share activity
            log_activity(
                file_id=str(file_rec.id),
                file_name=file_rec.filename,
                actor=user.email,
                event_type="FILE_SHARED",
                details=f"Shared with {share.recipient_email}"
            )
            # Record view
            log_activity(
                file_id=str(file_rec.id),
                file_name=file_rec.filename,
                actor=share.recipient_email,
                event_type="FILE_VIEWED",
                details="Opened share portal"
            )
            # Record download
            log_activity(
                file_id=str(file_rec.id),
                file_name=file_rec.filename,
                actor=share.recipient_email,
                event_type="FILE_DOWNLOADED",
                details="Downloaded file"
            )
            # Record revoke
            log_activity(
                file_id=str(file_rec.id),
                file_name=file_rec.filename,
                actor=user.email,
                event_type="ACCESS_REVOKED",
                details="Revoked by owner"
            )

            # Query activity history
            history = get_file_activity(str(file_rec.id))
            self.assertEqual(history["total_events"], 4)
            events = [a["event_type"] for a in history["activities"]]
            self.assertEqual(events, ["FILE_SHARED", "FILE_VIEWED", "FILE_DOWNLOADED", "ACCESS_REVOKED"])


if __name__ == "__main__":
    unittest.main()
