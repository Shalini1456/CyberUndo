# CyberUndo — Team API & Integration Contract (Member 1 Handoff)

> **Project Concept**: *"What if cybersecurity had Ctrl + Z?"*  
> **Module Owner**: Member 1 — Backend + Database + Integration Engine  
> **Status**: Complete, Tested & Integration-Ready

---

## 1. Team Responsibility Boundaries

To maintain clean separation of concerns for our 3-day hackathon MVP:

| Team Member | Domain | Scope Status |
|---|---|---|
| **Member 1 (Current Module)** | **Backend Core + Database + Auth + Files + Integration** | **Complete** (This document) |
| **Member 2** | Secure Sharing + Revocation Engine | Downstream Module (Uses Member 1 foundation) |
| **Member 3** | Frontend Web Application (UI/UX) | Consumes Member 1 & 2 REST APIs |
| **Member 4** | Blast Radius + Risk Engine + Activity Tracking | Downstream Module (Uses Member 1 foundation) |

> [!IMPORTANT]
> **Strict Boundary**: Member 1 does **NOT** implement Secure Sharing, Revoke, Activity Logging telemetry, Blast Radius calculations, or Risk Scoring. Member 1 provides the core REST APIs, ORM models, auth middleware, and pluggable blueprint extension points.

---

## 2. Server & Environment Details

- **Local Backend URL**: `http://127.0.0.1:5000`
- **API Base URL**: `http://127.0.0.1:5000/api`
- **CORS**: Enabled for all origins (`*`) and headers (`Content-Type`, `Authorization`).
- **Standard Response Envelope**:
  ```json
  // Success Response (HTTP 200/201)
  {
    "success": true,
    "message": "Human-readable description",
    "data": { ... }
  }

  // Error Response (HTTP 400/401/403/404/409/413/500)
  {
    "success": false,
    "message": "Descriptive error message"
  }
  ```

---

## 3. Database Schema & Models Reference

All tables are defined in [`backend/models.py`](file:///C:/Users/Balakrishnan/.gemini/antigravity/scratch/CyberUndo/backend/models.py) and auto-created on application startup.

### 1. `users` Table
| Field | Type | Modifiers | Description |
|---|---|---|---|
| `id` | Integer | PK, Auto-increment | Unique user identifier |
| `name` | String(100) | Not Null | User's display name |
| `email` | String(120) | Unique, Not Null, Indexed | Login email |
| `password_hash`| String(255) | Not Null | Werkzeug scrypt/pbkdf2 hash |
| `created_at` | DateTime | Not Null, Default: UTC Now | Registration timestamp |

### 2. `files` Table
| Field | Type | Modifiers | Description |
|---|---|---|---|
| `id` | Integer | PK, Auto-increment | Unique file identifier |
| `owner_id` | Integer | FK(`users.id`), Indexed | Uploader user ID |
| `filename` | String(255) | Not Null | Original filename (e.g. `report.pdf`) |
| `stored_filename` | String(255) | Unique, Not Null | Sanitized UUID disk name |
| `file_path` | String(500) | Not Null | Absolute disk path in `backend/uploads/` |
| `status` | String(50) | Default: `'active'` | `'active'`, `'deleted'`, `'quarantined'` |
| `created_at` | DateTime | Not Null, Default: UTC Now | Upload timestamp |

### 3. `shared_access` Table *(Foundation for Member 2)*
| Field | Type | Modifiers | Description |
|---|---|---|---|
| `id` | Integer | PK, Auto-increment | Share record ID |
| `file_id` | Integer | FK(`files.id`), Indexed | Target file ID |
| `owner_id` | Integer | FK(`users.id`), Not Null | User who initiated sharing |
| `recipient_id` | Integer | FK(`users.id`), Nullable | Recipient user ID (if targeted) |
| `share_token` | String(255) | Unique, Not Null, Indexed | URL-safe token for access |
| `permission` | String(50) | Default: `'view'` | `'view'`, `'download'`, etc. |
| `status` | String(50) | Default: `'active'` | `'active'`, `'revoked'`, `'expired'` |
| `created_at` | DateTime | Default: UTC Now | Sharing creation time |
| `expires_at` | DateTime | Nullable | Optional expiry timestamp |
| `revoked_at` | DateTime | Nullable | Timestamp when revoked |

### 4. `activity_logs` Table *(Foundation for Member 4)*
| Field | Type | Modifiers | Description |
|---|---|---|---|
| `id` | Integer | PK, Auto-increment | Audit log record ID |
| `file_id` | Integer | FK(`files.id`), Nullable, Indexed | Related file ID |
| `user_id` | Integer | FK(`users.id`), Nullable, Indexed | Actor user ID |
| `action` | String(100) | Not Null | Action verb (`UPLOAD`, `SHARE`, `REVOKE`, etc.) |
| `timestamp` | DateTime | Default: UTC Now, Indexed | Event timestamp |
| `ip_address` | String(45) | Nullable | Client IP address |
| `metadata` | Text | Nullable | JSON string with telemetry context |

---

## 4. Member 1 API Endpoints Specification

### 1. Health Check
* **`GET /api/health`**
* **Auth**: None
* **Response (200 OK)**:
  ```json
  {
    "success": true,
    "message": "CyberUndo Backend is running smoothly.",
    "data": {
      "status": "healthy",
      "service": "CyberUndo Backend Core (Member 1)"
    }
  }
  ```

---

### 2. User Registration
* **`POST /api/register`**
* **Auth**: None
* **Request Body**:
  ```json
  {
    "name": "Alice Developer",
    "email": "alice@cyberundo.io",
    "password": "Password123"
  }
  ```
* **Success Response (201 Created)**:
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
* **Error Responses**:
  * `400 Bad Request`: Missing fields, invalid email format, or password < 6 characters.
  * `409 Conflict`: Email already exists.

---

### 3. User Login
* **`POST /api/login`**
* **Auth**: None
* **Request Body**:
  ```json
  {
    "email": "alice@cyberundo.io",
    "password": "Password123"
  }
  ```
* **Success Response (200 OK)**:
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
* **Error Response**:
  * `401 Unauthorized`: Invalid credentials.

---

### 4. Current User Profile
* **`GET /api/auth/me`**
* **Auth**: `Authorization: Bearer <TOKEN>`
* **Success Response (200 OK)**:
  ```json
  {
    "success": true,
    "message": "Current user retrieved successfully.",
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

### 5. File Upload
* **`POST /api/files/upload`**
* **Auth**: `Authorization: Bearer <TOKEN>`
* **Content-Type**: `multipart/form-data`
* **Form Field**: `file` (binary payload)
* **Allowed Extensions**: `txt`, `pdf`, `png`, `jpg`, `jpeg`, `gif`, `doc`, `docx`, `xls`, `xlsx`, `csv`, `zip`, `json`
* **Max Size**: 16MB
* **Success Response (201 Created)**:
  ```json
  {
    "success": true,
    "message": "File uploaded and registered successfully.",
    "data": {
      "file": {
        "id": 1,
        "owner_id": 1,
        "filename": "incident_report.pdf",
        "stored_filename": "8f3b2c1d4e5a_incident_report.pdf",
        "status": "active",
        "created_at": "2026-08-23T18:35:00"
      }
    }
  }
  ```
* **Error Responses**:
  * `400 Bad Request`: No file provided, empty filename, disallowed extension, or path traversal attempt.
  * `413 Payload Too Large`: Exceeds 16MB.

---

### 6. List User Files
* **`GET /api/files`**
* **Auth**: `Authorization: Bearer <TOKEN>`
* **Success Response (200 OK)**:
  ```json
  {
    "success": true,
    "message": "Retrieved 1 file(s).",
    "data": {
      "files": [
        {
          "id": 1,
          "owner_id": 1,
          "filename": "incident_report.pdf",
          "stored_filename": "8f3b2c1d4e5a_incident_report.pdf",
          "status": "active",
          "created_at": "2026-08-23T18:35:00"
        }
      ]
    }
  }
  ```

---

### 7. Get File Details
* **`GET /api/files/<id>`**
* **Auth**: `Authorization: Bearer <TOKEN>`
* **Success Response (200 OK)**:
  ```json
  {
    "success": true,
    "message": "File metadata retrieved successfully.",
    "data": {
      "file": {
        "id": 1,
        "owner_id": 1,
        "filename": "incident_report.pdf",
        "stored_filename": "8f3b2c1d4e5a_incident_report.pdf",
        "status": "active",
        "created_at": "2026-08-23T18:35:00"
      }
    }
  }
  ```
* **Error Responses**:
  * `404 Not Found`: File ID does not exist.
  * `403 Forbidden`: Authenticated user is not the owner of this file.

---

### 8. Download File
* **`GET /api/files/<id>/download`**
* **Auth**: `Authorization: Bearer <TOKEN>`
* **Success Response (200 OK)**: Binary file stream with `Content-Disposition: attachment; filename="..."`.
* **Error Responses**: `403 Forbidden` (not owner) or `404 Not Found`.

---

## 5. Integration Guides for Teammates

### Member 2 — Secure Sharing + Revoke Integration Guide
1. **Module Location**: Create `backend/routes/share_routes.py`.
2. **Imports**:
   ```python
   from flask import Blueprint, request, jsonify
   from database import db
   from models import File, SharedAccess, User
   from auth import token_required
   import secrets
   from datetime import datetime

   share_bp = Blueprint("share", __name__)
   ```
3. **Plugging Blueprint into `app.py`**:
   In `backend/app.py`, register:
   ```python
   from routes.share_routes import share_bp
   app.register_blueprint(share_bp, url_prefix="/api")
   ```
4. **Creating a Share Token**:
   ```python
   token = secrets.token_urlsafe(32)
   new_share = SharedAccess(
       file_id=file_id,
       owner_id=current_user.id,
       recipient_id=recipient_id, # or None for public link
       share_token=token,
       permission="view",
       status="active"
   )
   db.session.add(new_share)
   db.session.commit()
   ```
5. **Revoking Access**:
   ```python
   share = SharedAccess.query.filter_by(id=share_id, owner_id=current_user.id).first()
   share.status = "revoked"
   share.revoked_at = datetime.utcnow()
   db.session.commit()
   ```

---

### Member 3 — Frontend (UI/UX) Integration Guide
1. **Base URL**: `http://127.0.0.1:5000/api`
2. **CORS Setup**: Fully open. Any React / Vue / Vite dev server (`http://localhost:5173`, `http://localhost:3000`, etc.) can make fetch/Axios requests immediately.
3. **Auth State**:
   - On `/api/login` success, save `response.data.data.token` to `localStorage.setItem("cyberundo_token", token)`.
   - Set Axios / fetch default header:
     ```javascript
     const token = localStorage.getItem("cyberundo_token");
     const headers = { Authorization: `Bearer ${token}` };
     ```
4. **File Upload (FormData)**:
   ```javascript
   const formData = new FormData();
   formData.append("file", selectedFile);
   await axios.post("http://127.0.0.1:5000/api/files/upload", formData, {
     headers: {
       ...headers,
       "Content-Type": "multipart/form-data"
     }
   });
   ```

---

### Member 4 — Blast Radius + Risk Engine + Activity Tracking Integration Guide
1. **Module Location**: Create `backend/routes/risk_routes.py` (or `activity_routes.py`).
2. **Imports**:
   ```python
   from database import db
   from models import ActivityLog, SharedAccess, File, User
   ```
3. **Logging System Telemetry**:
   ```python
   def log_event(file_id, user_id, action, ip_address, metadata_json=None):
       log_entry = ActivityLog(
           file_id=file_id,
           user_id=user_id,
           action=action,
           ip_address=ip_address,
           metadata_json=metadata_json
       )
       db.session.add(log_entry)
       db.session.commit()
   ```
4. **Calculating Blast Radius**:
   Query active shares for a target file to see how many users/links currently have access:
   ```python
   active_shares = SharedAccess.query.filter_by(file_id=file_id, status="active").all()
   blast_radius_count = len(active_shares)
   ```
