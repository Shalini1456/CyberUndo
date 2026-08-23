# CyberUndo — Project Overview & Backend Foundation

> **"What if cybersecurity had Ctrl + Z?"**  
> CyberUndo is a reversible-action cybersecurity platform. This repository contains the complete backend core, database foundation, authentication engine, file management system, and integration contracts for the team.

---

## 1. Team Responsibilities & Boundaries

| Member | Focus Area | Status |
|---|---|---|
| **Member 1 (Current Module)** | **Backend + Database + Auth + File System + Integration** | **Complete** |
| **Member 2** | Secure Sharing + Revoke Engine | Downstream Module (Plugs into `SharedAccess`) |
| **Member 3** | Frontend + UI/UX | Consumes REST APIs at `/api/*` |
| **Member 4** | Blast Radius + Risk Engine + Activity Tracking | Downstream Module (Plugs into `ActivityLogs`) |

> **Scope Clarification**: Member 1 provides the infrastructure, data schema, secure file storage, JWT auth, and blueprint hooks. Member 1 does **NOT** implement sharing/revocation logic, frontend views, or risk/activity telemetry engines.

---

## 2. Quickstart & Setup Guide

### 1. Prerequisites
- Python 3.9+ installed
- pip

### 2. Environment Setup & Dependency Installation
```bash
# Navigate to backend directory
cd backend

# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
.\venv\Scripts\activate
# On macOS / Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Start the Flask Backend
```bash
python app.py
```

* **Backend Base URL**: `http://127.0.0.1:5000`
* **API Base URL**: `http://127.0.0.1:5000/api`
* **Health Check**: `GET http://127.0.0.1:5000/api/health`

### 4. Run Automated Test Suite
```bash
pytest test_api.py -v
```

---

## 3. Implemented API Endpoints (Member 1)

| HTTP Method | Endpoint | Auth | Purpose |
|---|---|:---:|---|
| `GET` | `/api/health` | None | Verify backend service health |
| `POST` | `/api/register` | None | Register new user account with hashed password |
| `POST` | `/api/login` | None | Authenticate user and receive signed JWT |
| `GET` | `/api/auth/me` | Bearer | Get authenticated user profile |
| `POST` | `/api/files/upload` | Bearer | Upload file (multipart/form-data, 16MB max) |
| `GET` | `/api/files` | Bearer | List files owned by authenticated user |
| `GET` | `/api/files/<id>` | Bearer | Get metadata for specific file (ownership verified) |
| `GET` | `/api/files/<id>/download` | Bearer | Download physical file (ownership verified) |

For complete payload formats, schema definitions, and cURL examples, see [API_CONTRACT.md](./API_CONTRACT.md).

---

## 4. Integration Blueprint for Teammates

- **Member 2 (Sharing/Revoke)**: Import `SharedAccess`, `File`, `User` from `models.py` and register routes in `routes/share_routes.py`.
- **Member 3 (Frontend)**: Connect frontend app to `http://127.0.0.1:5000/api`. CORS is enabled for all origins.
- **Member 4 (Risk/Activity)**: Import `ActivityLog`, `SharedAccess`, and `File` from `models.py` to write logs and calculate blast radius metrics.
