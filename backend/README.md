# CyberUndo — Backend Core & Database Foundation (Member 1)

> **"What if cybersecurity had Ctrl + Z?"**  
> CyberUndo is a reversible-action cybersecurity platform. This module provides the central database, authentication engine, file management system, and integration interface for the entire hackathon project.

---

## 1. Architecture Overview

The backend is built with **Python**, **Flask**, **Flask-SQLAlchemy**, and **SQLite**. It provides:
- **Authentication**: JWT-based sessionless authentication using Werkzeug cryptographic password hashing.
- **Database Engine**: Fully configured SQLite database with normalized schema for Users, Files, SharedAccess, and ActivityLogs.
- **File Management**: Secure multipart file uploads with UUID obfuscation, path-traversal prevention, allowed-extension validation, and strict file ownership isolation.
- **CORS & Standardization**: Cross-Origin Resource Sharing enabled for frontend integration, with uniform JSON response envelopes.
- **Modular Integration**: Blueprint registration hooks and ORM models for Member 2 (Sharing/Revoke) and Member 4 (Blast Radius/Risk/Activity).

---

## 2. Folder Structure

```
CyberUndo/
├── backend/
│   ├── app.py                  # Application factory, CORS, error handlers, and blueprint registry
│   ├── config.py               # Environment configuration, file upload limits, and JWT secrets
│   ├── database.py             # SQLAlchemy instance and init_db table auto-creation
│   ├── models.py               # ORM Models: User, File, SharedAccess, ActivityLog
│   ├── auth.py                 # Password hashing & @token_required JWT decorator
│   ├── routes/
│   │   ├── __init__.py         # Route package exporter
│   │   ├── auth_routes.py      # POST /api/register, POST /api/login, GET /api/auth/me
│   │   └── file_routes.py      # POST /api/files/upload, GET /api/files, GET /api/files/<id>, GET /api/files/<id>/download
│   ├── uploads/                # Local directory for stored files (UUID-prefixed)
│   ├── requirements.txt        # Pinned lightweight dependencies
│   ├── test_api.py             # Automated unit & integration tests
│   ├── .env.example            # Sample environment variables
│   └── README.md               # Documentation and Integration Contracts
└── frontend/                   # Directory reserved for Member 3 (UI/UX)
```

---

## 3. Database Schema & Relational Foundation

```
+------------------+         +--------------------+         +-----------------------+
|      users       | 1 --- * |       files        | 1 --- * |     shared_access     |
+------------------+         +--------------------+         +-----------------------+
| id (PK)          |         | id (PK)            |         | id (PK)               |
| name             |         | owner_id (FK:users)|         | file_id (FK:files)    |
| email (Unique)   |         | filename           |         | owner_id (FK:users)   |
| password_hash    |         | stored_filename    |         | recipient_id (FK:user)|
| created_at       |         | file_path          |         | share_token (Unique)  |
+------------------+         | status             |         | permission            |
         |                   | created_at         |         | status                |
         |                   +--------------------+         | created_at            |
         |                             |                    | expires_at            |
         |                             |                    | revoked_at            |
         |                             |                    +-----------------------+
         |                             |
         +-------------+ +-------------+
                       | |
             +---------------------+
             |    activity_logs    |
             +---------------------+
             | id (PK)             |
             | file_id (FK:files)  |
             | user_id (FK:users)  |
             | action              |
             | timestamp           |
             | ip_address          |
             | metadata            |
             +---------------------+
```

### Table Details:
1. **`users`**: Contains registered user identities and hashed passwords.
2. **`files`**: Stores metadata for uploaded files, mapped to `users.id` via `owner_id`.
3. **`shared_access`** *(Foundation for Member 2)*: Maps file shares, tokens, expiration, and revocation timestamps.
4. **`activity_logs`** *(Foundation for Member 4)*: Audit trail recording system actions, timestamps, actors, and metadata.

---

## 4. Setup & Running Instructions

### Prerequisites
- Python 3.9+
- pip

### 1. Create Virtual Environment & Install Dependencies
```bash
cd backend
python -m venv venv

# Windows:
.\venv\Scripts\activate

# macOS / Linux:
source venv/bin/activate

pip install -r requirements.txt
```

### 2. Run the Server
```bash
python app.py
```
The server will start at `http://127.0.0.1:5000`. The SQLite database (`cyberundo.db`) and `uploads/` folder will be created automatically on startup.

### 3. Reset Database (During Development)
To reset the database, simply delete `cyberundo.db`:
```bash
rm cyberundo.db
# On Windows PowerShell:
Remove-Item cyberundo.db
```

### 4. Run Automated Tests
```bash
pytest test_api.py -v
```

---

## 5. API Reference & Testing (cURL Examples)

All API responses follow a uniform structure:
```json
{
  "success": true,
  "message": "Human readable description",
  "data": {}
}
```

### 1. Register User
- **Endpoint**: `POST /api/register`
- **Request**:
```bash
curl -X POST http://127.0.0.1:5000/api/register \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Alice Developer",
    "email": "alice@cyberundo.io",
    "password": "SecurePassword123"
  }'
```
- **Response** (`201 Created`):
```json
{
  "success": true,
  "message": "User registered successfully.",
  "data": {
    "user": {
      "id": 1,
      "name": "Alice Developer",
      "email": "alice@cyberundo.io",
      "created_at": "2026-08-23T18:30:00"
    }
  }
}
```

---

### 2. User Login
- **Endpoint**: `POST /api/login`
- **Request**:
```bash
curl -X POST http://127.0.0.1:5000/api/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "alice@cyberundo.io",
    "password": "SecurePassword123"
  }'
```
- **Response** (`200 OK`):
```json
{
  "success": true,
  "message": "Login successful.",
  "data": {
    "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "user": {
      "id": 1,
      "name": "Alice Developer",
      "email": "alice@cyberundo.io",
      "created_at": "2026-08-23T18:30:00"
    }
  }
}
```

---

### 3. Upload File
- **Endpoint**: `POST /api/files/upload`
- **Headers**: `Authorization: Bearer <TOKEN>`
- **Request**:
```bash
curl -X POST http://127.0.0.1:5000/api/files/upload \
  -H "Authorization: Bearer <TOKEN>" \
  -F "file=@/path/to/report.pdf"
```
- **Response** (`201 Created`):
```json
{
  "success": true,
  "message": "File uploaded and registered successfully.",
  "data": {
    "file": {
      "id": 1,
      "owner_id": 1,
      "filename": "report.pdf",
      "stored_filename": "a8f3b2c1d4e5_report.pdf",
      "status": "active",
      "created_at": "2026-08-23T18:35:00"
    }
  }
}
```

---

### 4. List User's Files
- **Endpoint**: `GET /api/files`
- **Headers**: `Authorization: Bearer <TOKEN>`
- **Request**:
```bash
curl -X GET http://127.0.0.1:5000/api/files \
  -H "Authorization: Bearer <TOKEN>"
```
- **Response** (`200 OK`):
```json
{
  "success": true,
  "message": "Retrieved 1 file(s).",
  "data": {
    "files": [
      {
        "id": 1,
        "owner_id": 1,
        "filename": "report.pdf",
        "stored_filename": "a8f3b2c1d4e5_report.pdf",
        "status": "active",
        "created_at": "2026-08-23T18:35:00"
      }
    ]
  }
}
```

---

### 5. Get File Details
- **Endpoint**: `GET /api/files/<id>`
- **Headers**: `Authorization: Bearer <TOKEN>`
- **Request**:
```bash
curl -X GET http://127.0.0.1:5000/api/files/1 \
  -H "Authorization: Bearer <TOKEN>"
```
- **Response** (`200 OK`):
```json
{
  "success": true,
  "message": "File metadata retrieved successfully.",
  "data": {
    "file": {
      "id": 1,
      "owner_id": 1,
      "filename": "report.pdf",
      "stored_filename": "a8f3b2c1d4e5_report.pdf",
      "status": "active",
      "created_at": "2026-08-23T18:35:00"
    }
  }
}
```

---

### 6. Download File
- **Endpoint**: `GET /api/files/<id>/download`
- **Headers**: `Authorization: Bearer <TOKEN>`
- **Request**:
```bash
curl -X GET http://127.0.0.1:5000/api/files/1/download \
  -H "Authorization: Bearer <TOKEN>" \
  -O -J
```

---

## 6. Integration Contracts for Teammates

### What Member 2 (Secure Sharing + Revoke) Needs:
1. **Models to Import**:
   ```python
   from models import User, File, SharedAccess
   from database import db
   from auth import token_required
   ```
2. **How to Register Blueprint**:
   - Create `backend/routes/share_routes.py`.
   - In `app.py`, uncomment or add:
     ```python
     from routes.share_routes import share_bp
     app.register_blueprint(share_bp, url_prefix="/api")
     ```
3. **Database Records**:
   - To share a file, verify ownership with `File.query.filter_by(id=file_id, owner_id=current_user.id).first()`.
   - Create a `SharedAccess` record with a unique `share_token = secrets.token_urlsafe(32)`.
   - To revoke, update `SharedAccess.status = 'revoked'` and `SharedAccess.revoked_at = datetime.utcnow()`.

---

### What Member 3 (Frontend + UI/UX) Needs:
1. **Base URL**: `http://127.0.0.1:5000/api`
2. **CORS**: Fully configured to accept requests from any origin (`origins="*"`) with Bearer auth headers.
3. **Authentication Workflow**:
   - Store `data.token` from `/api/login` in localStorage or state.
   - Send `Authorization: Bearer <token>` in subsequent requests.
4. **Error Handling**:
   - Check `response.data.success === false`. Display `response.data.message` in UI toast notifications.

---

### What Member 4 (Blast Radius + Risk Engine + Activity Tracking) Needs:
1. **Models to Import**:
   ```python
   from models import ActivityLog, File, User, SharedAccess
   from database import db
   ```
2. **Activity Logging Helper**:
   - Member 4 can create a helper in `routes/activity_routes.py`:
     ```python
     def record_activity(file_id, user_id, action, ip_address, metadata=None):
         log = ActivityLog(
             file_id=file_id,
             user_id=user_id,
             action=action,
             ip_address=ip_address,
             metadata_json=metadata
         )
         db.session.add(log)
         db.session.commit()
     ```
3. **Blast Radius Analysis**:
   - Query all `SharedAccess` records for a `file_id` where `status == 'active'` to compute affected users and compute risk scores.

---

## 7. Day 1 Implementation Checklist

- [x] Database configuration & SQLite auto-initialization (`database.py`, `config.py`)
- [x] ORM Models for Users, Files, SharedAccess, ActivityLogs (`models.py`)
- [x] Password hashing with Werkzeug & JWT token generation (`auth.py`)
- [x] `@token_required` authentication decorator (`auth.py`)
- [x] User Registration (`POST /api/register`) with validation & duplicate prevention
- [x] User Login (`POST /api/login`) returning JWT tokens
- [x] File Upload (`POST /api/files/upload`) with UUID filenames, extension checks & path-traversal safety
- [x] File Listing (`GET /api/files`) with user-isolated queries
- [x] File Retrieval & Download (`GET /api/files/<id>`, `GET /api/files/<id>/download`) with strict ownership checks
- [x] Standardized JSON error handlers (400, 401, 403, 404, 413, 500)
- [x] Cross-Origin Resource Sharing (CORS) configured for frontend
- [x] Automated test suite covering edge cases and security protections (`test_api.py`)
- [x] Clean blueprint integration points for Members 2 & 4
