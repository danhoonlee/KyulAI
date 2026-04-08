# Backend Team

## Mission
Build the API layer, business logic, database, and integrations that power the CAE-AI platform.

## Agents & Model Assignments
- **API Architect** (Sonnet): Designs REST API endpoints and data models
- **Backend Developer** (Sonnet): Implements FastAPI services and business logic
- **Database Engineer** (Sonnet): PostgreSQL schema, migrations, query optimization
- **Integration Engineer** (Sonnet): CAE tool connectors, file handling, cloud storage

## Tech Stack
- FastAPI (Python)
- SQLAlchemy + Alembic (ORM + migrations)
- PostgreSQL (metadata, experiments, users)
- Celery + Redis (async task queue)
- MinIO / S3 (large file storage)

## Key API Domains
- `/api/v1/data/` — Dataset upload, browse, parsing
- `/api/v1/models/` — Training, experiments, predictions
- `/api/v1/visualization/` — Mesh and field data for rendering
- `/api/v1/research/` — Paper database

## Code Location
- `src/backend/api/` — FastAPI routes
- `src/backend/services/` — Business logic
- `src/backend/models/` — Database models
- `src/backend/db/` — Database config and migrations
- `src/backend/workers/` — Celery async workers
