# Backend

This directory will contain the MarketPulse FastAPI backend application.

## Stack

- **Framework:** FastAPI (Python 3.12+)
- **ORM:** SQLAlchemy (async) + Alembic (migrations)
- **Validation:** Pydantic v2
- **Database:** PostgreSQL + TimescaleDB
- **Cache:** Redis
- **Worker:** ARQ (async job queue)

## Setup

See [docs/getting-started.md](../docs/getting-started.md) for full setup instructions.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

## Structure (planned)

```
backend/
├── app/
│   ├── api/              # Route handlers organized by domain
│   │   ├── v1/
│   │   │   ├── market.py
│   │   │   ├── instruments.py
│   │   │   ├── portfolio.py
│   │   │   ├── signals.py
│   │   │   ├── news.py
│   │   │   ├── calendar.py
│   │   │   ├── filings.py
│   │   │   └── users.py
│   ├── core/             # Config, security, dependencies
│   ├── db/               # Database engine, session, base models
│   ├── models/           # SQLAlchemy ORM models
│   ├── schemas/          # Pydantic request/response schemas
│   ├── services/         # Business logic layer
│   ├── workers/          # ARQ background job definitions
│   └── main.py           # FastAPI app entrypoint
├── alembic/              # Database migration scripts
├── tests/                # pytest test suite
├── requirements.txt
├── requirements-dev.txt
└── pyproject.toml
```

## API Documentation

When running locally, interactive API docs are available at:

- Swagger UI: <http://localhost:8000/docs>
- Redoc: http://localhost:8000/redoc
