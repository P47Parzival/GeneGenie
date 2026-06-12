# BioNexus India V1 — Backend

**India's first unified bioinformatics metadata warehouse.**

BioNexus ingests metadata from fragmented Indian biological data sources (IndiGenomes, IBDC, GenomeIndia, etc.), standardizes it into a unified schema, and exposes it through a discovery API. Think of it as the GSTN of Indian biomedical data — the infrastructure layer that makes all data interoperable.

> **V1 scope:** Metadata warehouse + discovery API. We store metadata *about* datasets — not the raw genomic files themselves.

---

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                        FastAPI Server                        │
│  /datasets  /search  /ingest  /sources  /stats              │
└────────────────────────┬─────────────────────────────────────┘
                         │
                    ┌────▼────┐
                    │ Postgres │  ← Unified metadata store
                    │  (GIN)   │    Full-text search indexes
                    └────▲────┘
                         │
              ┌──────────┼──────────┐
              │          │          │
        ┌─────▼──┐ ┌─────▼──┐ ┌────▼───┐
        │IndiGen.│ │ IBDC   │ │Genome  │   ← Source Adapters
        │Adapter │ │Adapter │ │India   │     (pluggable)
        └────────┘ └────────┘ │Adapter │
                              └────────┘
              ↓          ↓          ↓
        ┌────────────────────────────────┐
        │   Standardization Transformer  │   ← Unified schema mapping
        └────────────────────────────────┘
```

### Project Structure

```
backend/
├── api/                        # FastAPI application
│   ├── main.py                 # App setup, middleware, lifespan
│   ├── schemas.py              # Pydantic request/response models
│   └── routes/
│       ├── datasets.py         # GET /datasets, GET /datasets/{id}
│       ├── search.py           # GET /search?q=
│       ├── ingestion.py        # POST /ingest, GET /sources
│       └── stats.py            # GET /stats
├── ingestion/                  # Data ingestion layer
│   ├── base_adapter.py         # Abstract base (retry, logging, raw storage)
│   ├── indigenomes_adapter.py  # IndiGenomes (CSIR-IGIB)
│   ├── ibdc_adapter.py         # IBDC (RCB Faridabad)
│   ├── genomeindia_adapter.py  # GenomeIndia (IISc)
│   └── pipeline.py             # Orchestrator (adapter → transform → DB)
├── standardization/
│   └── transformer.py          # Raw → unified schema mapping
├── database/
│   ├── __init__.py             # Async engine + session factory
│   ├── models.py               # SQLAlchemy ORM (Dataset, IngestionLog)
│   ├── seed.py                 # 10 realistic sample records
│   └── migrations/
│       ├── env.py              # Alembic config
│       └── versions/
│           └── 001_initial_schema.py
├── config.py                   # Pydantic Settings (env vars)
├── docker-compose.yml          # PostgreSQL + API (one command)
├── Dockerfile
├── entrypoint.sh               # Migration + seed + server start
├── requirements.txt
├── alembic.ini
└── .env.example
```

---

## Quick Start

### Prerequisites
- [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed and running

### Run with Docker (recommended)

```bash
# 1. Navigate to the backend directory
cd backend

# 2. Copy environment file
copy .env.example .env

# 3. Build and start everything
docker-compose up --build
```

That's it. The entrypoint script will:
1. Wait for PostgreSQL to be ready
2. Run Alembic migrations (create tables + indexes)
3. Seed the database with 10 sample datasets
4. Start the FastAPI server on `http://localhost:8000`

### Verify it works

```bash
# Health check
curl http://localhost:8000/

# Get stats (should show 10 datasets)
curl http://localhost:8000/stats

# THE V1 MILESTONE — search for Type 2 Diabetes in Gujarat
curl "http://localhost:8000/search?q=Type+2+Diabetes&population=Gujarati&state=Gujarat"

# List all datasets
curl http://localhost:8000/datasets

# Filter by data type
curl "http://localhost:8000/datasets?data_type=genomic"

# Full-text search
curl "http://localhost:8000/search?q=cancer"
```

### Run without Docker (local development)

```bash
# 1. Create virtual environment
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # Linux/Mac

# 2. Install dependencies
pip install -r requirements.txt

# 3. Start PostgreSQL locally (ensure it's running on port 5432)

# 4. Copy and edit .env
copy .env.example .env
# Edit .env with your local PostgreSQL credentials

# 5. Run migrations
alembic upgrade head

# 6. Seed the database
python -m database.seed

# 7. Start the API
uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
```

---

## API Endpoints

### `GET /datasets`
Paginated list with filters.

| Parameter    | Type   | Description                              |
|-------------|--------|------------------------------------------|
| `disease`   | string | Filter by disease (partial match)        |
| `population`| string | Filter by population group               |
| `state`     | string | Filter by state of collection            |
| `data_type` | string | Filter: genomic, clinical, imaging, other|
| `source`    | string | Filter by source: indigenomes, ibdc, etc.|
| `access_type`| string | Filter: open, managed, controlled       |
| `page`      | int    | Page number (default: 1)                 |
| `limit`     | int    | Items per page (default: 20, max: 100)   |

### `GET /datasets/{dataset_id}`
Full metadata for a single dataset by UUID.

### `GET /search?q=`
Full-text search across name, institution, disease, population, state, and source.
Accepts all the same filter parameters as `/datasets`.
Results are ranked by relevance.

### `POST /ingest`
Trigger ingestion pipeline for a source.
```json
{ "source": "indigenomes" }
```

### `GET /sources`
List all available data sources with last ingestion timestamp and dataset count.

### `GET /stats`
Aggregate statistics: total datasets, breakdowns by source, data type, state, population, and access type.

---

## Unified Metadata Schema

Every dataset in BioNexus has exactly these fields:

| Field                   | Type      | Description                              |
|------------------------|-----------|------------------------------------------|
| `dataset_id`           | UUID      | Unique identifier (generated)            |
| `name`                 | string    | Dataset name/title                       |
| `source`               | string    | Source system identifier                 |
| `institution_name`     | string    | Originating institution                  |
| `state_of_collection`  | string    | Indian state of sample collection        |
| `population_group`     | string    | Population/ethnic group                  |
| `data_type`            | string    | genomic / clinical / imaging / other     |
| `disease_association`  | string    | Associated disease(s)                    |
| `sample_size`          | integer   | Number of samples                        |
| `collection_date`      | date      | Date of data collection                  |
| `access_type`          | string    | open / managed / controlled              |
| `source_url`           | string    | URL to original dataset                  |
| `ethics_approval_number`| string   | Ethics committee approval ID             |
| `contact_researcher`   | string    | Primary contact                          |
| `license_type`         | string    | Data license                             |
| `doi`                  | string    | Digital Object Identifier                |
| `raw_checksum`         | string    | SHA-256 of raw ingested record           |
| `date_ingested`        | datetime  | When ingested into BioNexus              |

---

## Adding a New Data Source

To add a new source (e.g., GSBTM), you only need to create **one file**:

### 1. Create the adapter

Create `ingestion/gsbtm_adapter.py`:

```python
from ingestion.base_adapter import BaseAdapter

class GSBTMAdapter(BaseAdapter):
    source_name = "gsbtm"
    base_url = "https://gsbtm.in"

    async def fetch_datasets(self) -> list[dict]:
        # Your scraping/API logic here
        response = await self._fetch_url(f"{self.base_url}/datasets")
        # Parse response...
        datasets = [...]

        # Always store raw response for debugging
        self._store_raw_response(datasets)
        return datasets
```

### 2. Register it

Add one line to `ingestion/pipeline.py`:

```python
from ingestion.gsbtm_adapter import GSBTMAdapter

ADAPTER_REGISTRY = {
    ...
    "gsbtm": GSBTMAdapter,  # ← add this
}
```

That's it. The pipeline, transformer, database, and API will handle the new source automatically.

---

## Database Indexes

Optimized for the specified query patterns:

| Index | Type | Columns | Purpose |
|-------|------|---------|---------|
| `ix_datasets_search_vector` | GIN | `search_vector` | Full-text search |
| `ix_datasets_source` | B-tree | `source` | Filter by source |
| `ix_datasets_state_of_collection` | B-tree | `state_of_collection` | Filter by state |
| `ix_datasets_population_group` | B-tree | `population_group` | Filter by population |
| `ix_datasets_data_type` | B-tree | `data_type` | Filter by data type |
| `ix_datasets_access_type` | B-tree | `access_type` | Filter by access type |
| `ix_datasets_disease_association` | B-tree | `disease_association` | Filter by disease |
| `ix_datasets_source_date_ingested` | B-tree | `source, date_ingested` | Ingestion tracking |

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `postgresql+asyncpg://...` | Async DB connection string |
| `SYNC_DATABASE_URL` | `postgresql://...` | Sync DB connection (Alembic) |
| `API_HOST` | `0.0.0.0` | Server bind host |
| `API_PORT` | `8000` | Server bind port |
| `LOG_LEVEL` | `INFO` | Logging level |
| `INGESTION_TIMEOUT` | `30` | HTTP request timeout (seconds) |
| `INGESTION_MAX_RETRIES` | `3` | Max retries for failed requests |
| `RAW_DATA_DIR` | `data/raw` | Raw response storage directory |

---

## Tech Stack

- **Python 3.11** — runtime
- **FastAPI** — API framework
- **SQLAlchemy 2.0** (async) — ORM
- **PostgreSQL 16** — database with full-text search
- **Alembic** — database migrations
- **httpx** — async HTTP client
- **tenacity** — retry with exponential backoff
- **BeautifulSoup4** — HTML parsing for scraping adapters
- **Pydantic v2** — data validation and serialization
- **Docker Compose** — container orchestration

---

## License

Internal use — BioNexus India project.
