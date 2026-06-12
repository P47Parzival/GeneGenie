# BioNexus India V2 — Backend

**India's first unified bioinformatics data infrastructure platform.**

V2 adds access management, institutional onboarding, FeED protocol compliance, and notification infrastructure on top of V1's metadata warehouse.

> **V1:** Find Indian biological data (metadata warehouse + search)
> **V2:** Access Indian biological data (access management + FeED compliance)

---

## Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                        FastAPI Server                            │
│  /auth  /institutions  /access-requests  /feed-forms  /audit    │
│  /datasets  /search  /ingest  /sources  /stats                  │
└────────────────────┬──────────────────────┬──────────────────────┘
                     │                      │
              ┌──────▼──────┐        ┌──────▼──────┐
              │  PostgreSQL  │        │    Redis     │
              │  (GIN + FTS) │        │  (Celery)    │
              └──────────────┘        └──────┬──────┘
                                             │
                                      ┌──────▼──────┐
                                      │   Celery     │
                                      │   Worker     │
                                      │ Notifications│
                                      └─────────────┘
```

### User Roles

| Role | Capabilities |
|------|-------------|
| **Researcher** | Search datasets, request access, upload documents, download approved data |
| **Institution** | Manage datasets, review/approve/reject access requests, sign FeED forms |
| **Admin** | Platform oversight, verify institutions, view all audit logs |

### Access Request Lifecycle

```
DRAFT → SUBMITTED → UNDER_REVIEW → APPROVED
                                  → REJECTED
                                  → MORE_INFO_NEEDED → UNDER_REVIEW → ...
```

Every state transition is logged with timestamp, actor, and reason.

---

### Project Structure

```
backend/
├── api/
│   ├── main.py                 # FastAPI app (V2 — all routers)
│   ├── schemas.py              # Pydantic models (V1 + V2)
│   └── routes/
│       ├── datasets.py         # GET /datasets (public/auth split)
│       ├── search.py           # GET /search (public/auth split)
│       ├── ingestion.py        # POST /ingest (V1)
│       ├── stats.py            # GET /stats (V1)
│       ├── auth.py             # POST /auth/register, /login, /refresh
│       ├── institutions.py     # POST /institutions/register, /verify
│       ├── access.py           # Full access request lifecycle
│       ├── feed_forms.py       # FeED form generation and signing
│       └── audit.py            # GET /audit/{type}/{id}
├── services/
│   ├── auth_service.py         # JWT + bcrypt + RBAC dependencies
│   ├── audit_service.py        # Immutable audit trail
│   ├── notification_service.py # Async notifications (email channel)
│   └── feed_form_service.py    # FeED form generation (JSON + PDF)
├── workers/
│   ├── celery_app.py           # Celery configuration
│   └── notification_worker.py  # Async delivery tasks
├── ingestion/                  # (V1 — unchanged)
├── standardization/            # (V1 — unchanged)
├── database/
│   ├── __init__.py             # Async engine + session
│   ├── models.py               # ORM models (V1 + V2)
│   ├── seed.py                 # Seed data (V1 + V2)
│   └── migrations/versions/
│       ├── 001_initial_schema.py
│       └── 002_v2_auth_access.py
├── config.py                   # All settings (JWT, Redis, SMTP, etc.)
├── docker-compose.yml          # PostgreSQL + Redis + API + Worker
├── Dockerfile
├── entrypoint.sh
├── requirements.txt
├── alembic.ini
├── .env.example
└── README.md
```

---

## Quick Start

### Prerequisites
- [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed and running

### Run with Docker (recommended)

```bash
cd backend
copy .env.example .env
docker-compose up --build
```

This starts 4 services:
1. **PostgreSQL** — database on port 5433
2. **Redis** — task queue on port 6379
3. **API** — FastAPI server on port 8000
4. **Worker** — Celery notification worker

The entrypoint will automatically run migrations, seed the database, and start the API.

### Run without Docker (local development)

```bash
cd backend
python -m venv venv
venv\Scripts\activate

pip install -r requirements.txt

copy .env.example .env
# Edit .env with your local PostgreSQL and Redis URLs

# Run migrations
alembic upgrade head

# Seed database
python -m database.seed

# Start API
uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload

# In a separate terminal — start Celery worker
celery -A workers.celery_app worker --loglevel=info -Q notifications,celery
```

---

## Seed Accounts

| Email | Password | Role |
|-------|----------|------|
| `admin@bionexus.in` | `Admin@BioNexus2025` | Admin |
| `nodal@igib.res.in` | `IGIB@Nodal2025` | Institution (CSIR-IGIB) |
| `nodal@rcb.res.in` | `RCB@Nodal2025` | Institution (RCB/IBDC) |
| `researcher@iitd.ac.in` | `Research@IIT2025` | Researcher |
| `researcher@iisc.ac.in` | `Research@IISc2025` | Researcher |

---

## API Endpoints

### Authentication

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/auth/register` | — | Create user account |
| POST | `/auth/login` | — | Get access + refresh tokens |
| POST | `/auth/refresh` | — | Exchange refresh token |
| GET | `/auth/me` | ✓ | Get current user profile |
| PUT | `/auth/me` | ✓ | Update profile |

### Institutions

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/institutions/register` | Institution/Admin | Register institution |
| POST | `/institutions/verify` | Admin | Verify institution |
| GET | `/institutions` | — | List verified institutions |
| GET | `/institutions/{id}` | — | Institution profile |
| PUT | `/institutions/{id}` | Institution/Admin | Update profile |

### Access Requests

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/access-requests` | Researcher | Create draft |
| GET | `/access-requests` | ✓ | List (role-filtered) |
| GET | `/access-requests/{id}` | ✓ | Full details |
| PUT | `/access-requests/{id}/submit` | Researcher | Submit for review |
| PUT | `/access-requests/{id}/review` | Institution/Admin | Start review |
| PUT | `/access-requests/{id}/approve` | Institution/Admin | Approve |
| PUT | `/access-requests/{id}/reject` | Institution/Admin | Reject with reason |
| PUT | `/access-requests/{id}/info` | Institution/Admin | Request more info |
| PUT | `/access-requests/{id}/respond` | Researcher | Respond to info request |
| POST | `/access-requests/{id}/documents` | Researcher | Upload supporting doc |

### FeED Forms

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/feed-forms/generate` | ✓ | Generate all 6 form types |
| GET | `/feed-forms/{request_id}` | ✓ | Retrieve generated forms |
| POST | `/feed-forms/{request_id}/sign` | Institution/Admin | Sign/acknowledge forms |

### Audit Trail

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/audit/{resource_type}/{resource_id}` | ✓ | Full resource history |

### V1 Endpoints (preserved)

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/datasets` | Optional | List with filters (limited/full metadata) |
| GET | `/datasets/{id}` | Optional | Dataset detail |
| GET | `/search?q=` | Optional | Full-text search |
| POST | `/ingest` | — | Trigger ingestion |
| GET | `/sources` | — | List sources |
| GET | `/stats` | — | Aggregate statistics |

---

## Complete V2 Lifecycle Test

```bash
# 1. Register a researcher
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@researcher.com","password":"Test1234!","full_name":"Dr. Test","role":"researcher"}'

# Save the access_token from the response

# 2. Search datasets (authenticated — full metadata)
curl -H "Authorization: Bearer ACCESS_TOKEN" \
  "http://localhost:8000/search?q=Type+2+Diabetes"

# 3. Create access request
curl -X POST http://localhost:8000/access-requests \
  -H "Authorization: Bearer ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "dataset_id":"DATASET_UUID_FROM_SEARCH",
    "purpose_of_use":"Studying T2D genetic variants in Gujarat",
    "institution_affiliation":"IIT Delhi",
    "expected_duration_days":180,
    "will_data_be_published":true,
    "requested_access_type":"managed"
  }'

# 4. Submit the request
curl -X PUT http://localhost:8000/access-requests/REQUEST_ID/submit \
  -H "Authorization: Bearer ACCESS_TOKEN"

# 5. Login as institution
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"nodal@igib.res.in","password":"IGIB@Nodal2025"}'

# 6. Start review
curl -X PUT http://localhost:8000/access-requests/REQUEST_ID/review \
  -H "Authorization: Bearer INSTITUTION_TOKEN"

# 7. Approve
curl -X PUT http://localhost:8000/access-requests/REQUEST_ID/approve \
  -H "Authorization: Bearer INSTITUTION_TOKEN"

# 8. Generate FeED forms
curl -X POST http://localhost:8000/feed-forms/generate \
  -H "Authorization: Bearer INSTITUTION_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"access_request_id":"REQUEST_ID"}'

# 9. Sign FeED forms
curl -X POST http://localhost:8000/feed-forms/REQUEST_ID/sign \
  -H "Authorization: Bearer INSTITUTION_TOKEN"

# 10. Check audit trail
curl -H "Authorization: Bearer INSTITUTION_TOKEN" \
  http://localhost:8000/audit/access_request/REQUEST_ID
```

---

## FeED Compliance Forms

When generated, BioNexus produces 6 FeED-compliant forms:

| Form | Description |
|------|-------------|
| **Data User Agreement (DUA)** | Legal agreement with terms and conditions |
| **Data Access Request Form** | Formal request mirroring FeED protocol fields |
| **Institutional Sign-off** | Nodal officer acknowledgment section |
| **Data Management Plan** | How data will be stored, secured, and retained |
| **Publication & Attribution** | Credit and co-authorship commitments |
| **Ethics Compliance Declaration** | Ethics approval and ICMR guidelines compliance |

Each form is stored as:
- **Structured JSON** — for machine consumption and system integration
- **PDF** — for human review and institutional filing

---

## Notification Events

| Event | Recipient | Channel |
|-------|-----------|---------|
| Request submitted | Institution nodal officer | Email |
| Request approved | Researcher | Email |
| Request rejected | Researcher (with reason) | Email |
| More info needed | Researcher (with questions) | Email |
| Info response received | Institution reviewer | Email |
| Access expiring (7 days) | Researcher | Email |
| Institution verified | Nodal officer | Email |
| User registered | New user | Email |

Notifications are delivered asynchronously via Celery + Redis. If SMTP is not configured, they are logged to console (development mode).

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `postgresql+asyncpg://...` | Async DB connection |
| `SYNC_DATABASE_URL` | `postgresql://...` | Sync DB (Alembic) |
| `REDIS_URL` | `redis://localhost:6379/0` | Celery broker |
| `JWT_SECRET_KEY` | dev default | **Change in production!** |
| `JWT_ALGORITHM` | `HS256` | Token signing algo |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `30` | Access token TTL |
| `REFRESH_TOKEN_EXPIRE_DAYS` | `7` | Refresh token TTL |
| `SMTP_HOST` | (empty) | SMTP server (empty = console mode) |
| `SMTP_PORT` | `587` | SMTP port |
| `SMTP_USER` | (empty) | SMTP username |
| `SMTP_PASSWORD` | (empty) | SMTP password |
| `SMTP_FROM_EMAIL` | `noreply@bionexus.in` | From address |
| `UPLOAD_DIR` | `data/uploads` | File upload directory |
| `MAX_UPLOAD_SIZE_MB` | `10` | Max upload size |

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Runtime | Python 3.11 |
| API Framework | FastAPI |
| ORM | SQLAlchemy 2.0 (async) |
| Database | PostgreSQL 16 (full-text search) |
| Migrations | Alembic |
| Task Queue | Celery + Redis |
| Auth | JWT (python-jose) + bcrypt (passlib) |
| PDF Generation | ReportLab |
| Email | aiosmtplib |
| HTTP Client | httpx |
| Containers | Docker Compose |

---

## License

Internal use — BioNexus India project.
