# Implementation Plan: Connect Backend and Frontend & Install All Requirement Files

Connect the FastAPI AI/ML backend and the React / TanStack Start frontend for the SIH 26129 Inter-Governmental Mesh project, verify all dependencies, and establish live end-to-end communication.

## User Review Required

> [!NOTE]
> All Python dependencies (FastAPI, Uvicorn, PyTorch, Transformers, EasyOCR, spaCy, XGBoost, LightGBM, Scikit-Learn) and Node.js dependencies (Vite, React 19, Radix UI, TanStack Start, Tailwind CSS) are already fully installed on your system.
> The backend SQLite database (`backend/sih26129.db`) is initialized with tables but had 0 rows. We will seed it with realistic Indian Inter-Governmental Mesh records (Departments, DigiLocker/PFMS/SAMARTH platforms, Citizen Applications, Consents, Audit Logs, and sample users).

## Proposed Changes

### 1. Backend REST API Endpoints

Currently, [router.py](file:///d:/Downloads/SIH_Proj.%20129/backend/app/api/v1/router.py) only exposes `/ml/*` endpoints. We will implement complete, production-ready REST API endpoints matching the database models and frontend expectations:

#### [NEW] [auth.py](file:///d:/Downloads/SIH_Proj.%20129/backend/app/api/v1/auth.py)
- `POST /api/v1/auth/login`: Authenticate with email/password, return JWT token & user profile
- `POST /api/v1/auth/signup`: Register new citizen or officer account
- `GET /api/v1/auth/me`: Get current authenticated user details

#### [NEW] [applications.py](file:///d:/Downloads/SIH_Proj.%20129/backend/app/api/v1/applications.py)
- `GET /api/v1/applications`: List applications with filtering by status, search, and department
- `POST /api/v1/applications`: Submit a new service application
- `GET /api/v1/applications/{id}`: Get application details and associated documents
- `PATCH /api/v1/applications/{id}/status`: Update status (e.g. Under Review, Approved, Flagged)
- `GET /api/v1/applications/track/{reference_id}`: Public tracking endpoint by reference number

#### [NEW] [platforms.py](file:///d:/Downloads/SIH_Proj.%20129/backend/app/api/v1/platforms.py)
- `GET /api/v1/platforms`: List mesh nodes / digital platforms (DigiLocker, SAMARTH, PFMS, GSTN, UIDAI)
- `POST /api/v1/platforms`: Register a new digital platform mesh node
- `GET /api/v1/platforms/{id}`: Platform details
- `POST /api/v1/platforms/{id}/ping`: Real-time health and latency check

#### [NEW] [departments.py](file:///d:/Downloads/SIH_Proj.%20129/backend/app/api/v1/departments.py) & [services.py](file:///d:/Downloads/SIH_Proj.%20129/backend/app/api/v1/services.py)
- List departments and government services with SLA, document requirements, and volume

#### [NEW] [consents.py](file:///d:/Downloads/SIH_Proj.%20129/backend/app/api/v1/consents.py) & [audit.py](file:///d:/Downloads/SIH_Proj.%20129/backend/app/api/v1/audit.py)
- `GET /api/v1/consents`: List citizen data share consents
- `POST /api/v1/consents`: Create new consent record
- `POST /api/v1/consents/{id}/revoke`: Revoke consent with instant audit logging
- `GET /api/v1/audit-logs`: Inter-governmental audit trail

#### [NEW] [stats.py](file:///d:/Downloads/SIH_Proj.%20129/backend/app/api/v1/stats.py)
- `GET /api/v1/stats/dashboard`: Real aggregated dashboard stats (total transactions, success rate %, active mesh nodes, anomaly detection alerts, latency breakdown)

#### [NEW] [documents.py](file:///d:/Downloads/SIH_Proj.%20129/backend/app/api/v1/documents.py)
- `POST /api/v1/documents/upload-and-verify`: Accepts document upload/base64, invokes the multi-model AI pipeline (EasyOCR + LayoutLMv3 + spaCy + Anomaly detection) and stores results in the DB

#### [MODIFY] [router.py](file:///d:/Downloads/SIH_Proj.%20129/backend/app/api/v1/router.py)
- Mount all routers under `/api/v1`

---

### 2. Database Seeding

#### [NEW] [seed_db.py](file:///d:/Downloads/SIH_Proj.%20129/backend/seed_db.py)
- Populate `backend/sih26129.db` with realistic government data:
  - Users: Admin (`admin@govflow.in`), Officer (`officer@revenue.gov.in`), Citizen (`citizen@example.com`)
  - Departments: Revenue, Transport, Education, Food & Civil Supplies, Public Health
  - Platforms: UIDAI eKYC, DigiLocker Mesh, SAMARTH Education, PFMS Banking, GSTN Taxpayer
  - Services: Post-Matric Scholarship, Farmer DBT, Ration Card Transfer, Trade License Renewal
  - Sample Applications, Consents, and Audit Trail events

---

### 3. Frontend API Client & Integration

#### [NEW] [api.ts](file:///d:/Downloads/SIH_Proj.%20129/frontend/govflow-connect-main/govflow-connect-main/src/lib/api.ts)
- Strongly typed TypeScript API client supporting:
  - `auth`: `login`, `signup`, `getMe`, `logout`
  - `stats`: `getDashboardStats`, `getSystemHealth`
  - `applications`: `list`, `get`, `create`, `updateStatus`, `track`
  - `platforms`: `list`, `ping`
  - `services`: `list`
  - `consents`: `list`, `create`, `revoke`
  - `audit`: `list`
  - `ml`: `getStatus`, `verifyDocument`, `runOCR`, `detectAnomaly`

#### [MODIFY] [store.tsx](file:///d:/Downloads/SIH_Proj.%20129/frontend/govflow-connect-main/govflow-connect-main/src/lib/govflow/store.tsx)
- Connect store to backend API:
  - Fetch live backend data on initial load
  - Provide fallback to local state if backend is booting
  - Real-time login/signup authentication persistence

#### [MODIFY] [vite.config.ts](file:///d:/Downloads/SIH_Proj.%20129/frontend/govflow-connect-main/govflow-connect-main/vite.config.ts)
- Configure dev server proxy `/api` -> `http://127.0.0.1:8000`

#### [NEW] [BackendStatusBadge.tsx](file:///d:/Downloads/SIH_Proj.%20129/frontend/govflow-connect-main/govflow-connect-main/src/components/govflow/backend-status-badge.tsx)
- Live header badge displaying backend health, response latency, and active AI engine status (EasyOCR, LayoutLMv3, spaCy, DistilBERT, XGBoost, One-Class SVM).

#### [NEW] [AIDocumentVerifier.tsx](file:///d:/Downloads/SIH_Proj.%20129/frontend/govflow-connect-main/govflow-connect-main/src/components/govflow/ai-document-verifier.tsx)
- Interactive AI Document Verification widget in the UI allowing users to test document verification, OCR text extraction, entity recognition, and fraud risk scoring against the live backend!

---

### 4. Convenient Startup & Installation Scripts

#### [NEW] [start_all.bat](file:///d:/Downloads/SIH_Proj.%20129/start_all.bat) & [start_all.ps1](file:///d:/Downloads/SIH_Proj.%20129/start_all.ps1)
- Starts backend on port 8000 and frontend on port 3000/dev with one click
#### [NEW] [start_backend.bat](file:///d:/Downloads/SIH_Proj.%20129/start_backend.bat) & [start_frontend.bat](file:///d:/Downloads/SIH_Proj.%20129/start_frontend.bat)
- Individual one-click runners
#### [NEW] [install_all.bat](file:///d:/Downloads/SIH_Proj.%20129/install_all.bat)
- One-click installer for any missing pip/npm requirements

---

## Verification Plan

### Automated Verification
1. Run backend tests / seed script to ensure DB population and schema validity.
2. Run backend FastAPI server via Python and make curl/HTTP requests:
   - `GET http://127.0.0.1:8000/health` -> 200 OK
   - `GET http://127.0.0.1:8000/api/v1/info` -> 200 OK
   - `GET http://127.0.0.1:8000/api/v1/ml/status` -> 200 OK
   - `POST http://127.0.0.1:8000/api/v1/auth/login` -> 200 OK with token
   - `GET http://127.0.0.1:8000/api/v1/applications` -> 200 OK with seeded data
   - `GET http://127.0.0.1:8000/api/v1/stats/dashboard` -> 200 OK
3. Run `npm run typecheck` and `npm run build` in frontend to verify 0 TypeScript/build errors.

### Manual / Browser Verification
1. Open frontend in browser, verify live connection indicator shows "Backend Connected (FastAPI v1.0.0)".
2. Verify dashboard graphs and counts load from backend.
3. Test AI Document Verification widget live in browser.
