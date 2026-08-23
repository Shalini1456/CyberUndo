import io
import os
import tempfile
import pytest
from app import create_app
from database import db
from models import User, File

class TestConfig:
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECRET_KEY = "test-secret-key"
    JWT_SECRET_KEY = "test-jwt-secret-key"
    ALLOWED_EXTENSIONS = {"txt", "pdf", "png", "jpg"}
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024

@pytest.fixture
def client():
    # Setup temporary directory for test uploads
    test_upload_dir = tempfile.mkdtemp()
    TestConfig.UPLOAD_FOLDER = test_upload_dir

    app = create_app(TestConfig)

    with app.test_client() as client:
        with app.app_context():
            db.create_all()
        yield client
        with app.app_context():
            db.drop_all()

    # Cleanup temp directory
    for root, dirs, files in os.walk(test_upload_dir, topdown=False):
        for f in files:
            os.remove(os.path.join(root, f))
        for d in dirs:
            os.rmdir(os.path.join(root, d))
    os.rmdir(test_upload_dir)


def test_health_check(client):
    """Verify health check endpoint."""
    res = client.get("/api/health")
    assert res.status_code == 200
    json_data = res.get_json()
    assert json_data["success"] is True
    assert json_data["data"]["status"] == "healthy"


def test_registration_and_validation(client):
    """Test user registration edge cases and duplicate prevention."""
    # 1. Missing fields
    res = client.post("/api/register", json={"email": "alice@test.com"})
    assert res.status_code == 400
    assert res.get_json()["success"] is False

    # 2. Invalid email format
    res = client.post("/api/register", json={"name": "Alice", "email": "invalid-email", "password": "password123"})
    assert res.status_code == 400

    # 3. Short password
    res = client.post("/api/register", json={"name": "Alice", "email": "alice@test.com", "password": "123"})
    assert res.status_code == 400

    # 4. Successful registration
    res = client.post("/api/register", json={"name": "Alice", "email": "alice@test.com", "password": "password123"})
    assert res.status_code == 201
    json_data = res.get_json()
    assert json_data["success"] is True
    assert json_data["data"]["user"]["email"] == "alice@test.com"

    # 5. Prevent duplicate email registration
    res_dup = client.post("/api/register", json={"name": "Alice 2", "email": "alice@test.com", "password": "password456"})
    assert res_dup.status_code == 409
    assert res_dup.get_json()["success"] is False


def test_login_and_jwt_generation(client):
    """Test login and JWT token generation."""
    # Register user
    client.post("/api/register", json={"name": "Bob", "email": "bob@test.com", "password": "securepassword"})

    # Wrong password
    res_wrong = client.post("/api/login", json={"email": "bob@test.com", "password": "wrongpassword"})
    assert res_wrong.status_code == 401
    assert res_wrong.get_json()["success"] is False

    # Non-existent user
    res_nonexist = client.post("/api/login", json={"email": "nobody@test.com", "password": "password"})
    assert res_nonexist.status_code == 401

    # Correct login
    res = client.post("/api/login", json={"email": "bob@test.com", "password": "securepassword"})
    assert res.status_code == 200
    json_data = res.get_json()
    assert json_data["success"] is True
    assert "token" in json_data["data"]

    token = json_data["data"]["token"]

    # Verify protected /auth/me route
    res_me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert res_me.status_code == 200
    assert res_me.get_json()["data"]["user"]["email"] == "bob@test.com"


def test_jwt_auth_protection(client):
    """Test missing or invalid JWT tokens."""
    # Missing token
    res_no_token = client.get("/api/files")
    assert res_no_token.status_code == 401

    # Invalid header format
    res_bad_header = client.get("/api/files", headers={"Authorization": "InvalidHeaderFormat"})
    assert res_bad_header.status_code == 401

    # Invalid token string
    res_bad_token = client.get("/api/files", headers={"Authorization": "Bearer not-a-valid-token"})
    assert res_bad_token.status_code == 401


def test_file_upload_and_security(client):
    """Test file upload validation and storage."""
    # Register & Login
    client.post("/api/register", json={"name": "Charlie", "email": "charlie@test.com", "password": "password123"})
    login_res = client.post("/api/login", json={"email": "charlie@test.com", "password": "password123"})
    token = login_res.get_json()["data"]["token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Missing file in request
    res_missing = client.post("/api/files/upload", headers=headers, data={})
    assert res_missing.status_code == 400

    # 2. Disallowed extension (e.g., .exe)
    bad_file = (io.BytesIO(b"malicious executable payload"), "exploit.exe")
    res_bad_ext = client.post("/api/files/upload", headers=headers, data={"file": bad_file}, content_type="multipart/form-data")
    assert res_bad_ext.status_code == 400
    assert res_bad_ext.get_json()["success"] is False

    # 3. Valid file upload
    good_file = (io.BytesIO(b"Hello CyberUndo Security Platform!"), "incident_report.txt")
    res_upload = client.post("/api/files/upload", headers=headers, data={"file": good_file}, content_type="multipart/form-data")
    assert res_upload.status_code == 201
    file_data = res_upload.get_json()["data"]["file"]
    assert file_data["filename"] == "incident_report.txt"
    assert file_data["status"] == "active"
    file_id = file_data["id"]

    # 4. List files
    res_list = client.get("/api/files", headers=headers)
    assert res_list.status_code == 200
    assert len(res_list.get_json()["data"]["files"]) == 1

    # 5. Get file metadata
    res_detail = client.get(f"/api/files/{file_id}", headers=headers)
    assert res_detail.status_code == 200
    assert res_detail.get_json()["data"]["file"]["filename"] == "incident_report.txt"

    # 6. Download file
    res_download = client.get(f"/api/files/{file_id}/download", headers=headers)
    assert res_download.status_code == 200
    assert res_download.data == b"Hello CyberUndo Security Platform!"


def test_file_ownership_isolation(client):
    """Ensure User B cannot access or download User A's private file."""
    # Register User A and upload a file
    client.post("/api/register", json={"name": "User A", "email": "usera@test.com", "password": "passwordA"})
    login_a = client.post("/api/login", json={"email": "usera@test.com", "password": "passwordA"})
    token_a = login_a.get_json()["data"]["token"]

    file_a = (io.BytesIO(b"Confidential User A data"), "secret.pdf")
    res_a = client.post("/api/files/upload", headers={"Authorization": f"Bearer {token_a}"}, data={"file": file_a}, content_type="multipart/form-data")
    file_id = res_a.get_json()["data"]["file"]["id"]

    # Register User B
    client.post("/api/register", json={"name": "User B", "email": "userb@test.com", "password": "passwordB"})
    login_b = client.post("/api/login", json={"email": "userb@test.com", "password": "passwordB"})
    token_b = login_b.get_json()["data"]["token"]
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # User B lists files -> should see 0 files
    res_list_b = client.get("/api/files", headers=headers_b)
    assert res_list_b.status_code == 200
    assert len(res_list_b.get_json()["data"]["files"]) == 0

    # User B attempts to access User A's file metadata -> 403 Forbidden
    res_b_meta = client.get(f"/api/files/{file_id}", headers=headers_b)
    assert res_b_meta.status_code == 403
    assert res_b_meta.get_json()["success"] is False

    # User B attempts to download User A's file -> 403 Forbidden
    res_b_dl = client.get(f"/api/files/{file_id}/download", headers=headers_b)
    assert res_b_dl.status_code == 403
