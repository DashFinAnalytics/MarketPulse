# Getting Started

This guide covers how to set up the MarketPulse development environment locally.

> **Note:** MarketPulse is in early development. These instructions will be updated as the project matures.

---

## Prerequisites

Ensure the following are installed on your machine:

| Tool | Version | Notes |
|---|---|---|
| Docker | 24+ | Required for all services |
| Docker Compose | 2.20+ | Included with Docker Desktop |
| Node.js | 20 LTS | Frontend development |
| Python | 3.12+ | Backend development |
| Git | 2.40+ | Source control |

---

## Repository Structure

```
MarketPulse/
├── frontend/          # Next.js frontend application
├── backend/           # FastAPI backend API
├── docs/              # Project documentation
│   ├── adr/           # Architecture Decision Records
│   ├── architecture.md
│   ├── contributing.md
│   ├── getting-started.md
│   └── roadmap.md
├── .gitignore
└── README.md
```

---

## Local Setup

### 1. Clone the repository

```bash
git clone https://github.com/DashFinAnalytics/MarketPulse.git
cd MarketPulse
```

### 2. Copy environment configuration

```bash
cp .env.example .env
```

Edit `.env` to configure your local environment (API keys, database credentials, etc.).

> **Never commit `.env` files or secrets to source control.**

### 3. Start the backend and frontend

You can run the backend and frontend directly on your machine.

> **Note:** A Docker Compose setup for all services (database, cache, backend, frontend, worker) is planned but not yet included in this repository. Until then, use the manual setup below.

In one terminal, start the backend:

```bash
cd backend
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

In a second terminal, start the frontend:

```bash
cd frontend
npm install
npm run dev
```

### 4. Access the application

| Service | URL |
|---|---|
| Frontend | <http://localhost:3000> |
| Backend API | <http://localhost:8000> |
| API docs (Swagger) | <http://localhost:8000/docs> |
| API docs (Redoc) | <http://localhost:8000/redoc> |

---

## Frontend Development

```bash
cd frontend
npm install
npm run dev
```

The frontend dev server runs on `http://localhost:3000` with hot reload.

---

## Backend Development (planned)

Backend layout and setup commands are still being finalized for this repository.
For the most up-to-date backend instructions, see the backend README:

- [`backend/README.md`](../backend/README.md)

Once the backend structure is stable, this section will be updated with concrete setup commands.

---

## Running Tests

### Frontend

```bash
cd frontend
npm run test
```

### Backend

```bash
cd backend
pytest
```

---

## Stopping Services

To stop the development servers, press `Ctrl+C` in each terminal where `uvicorn` or `npm run dev` is running.

If you created a Python virtual environment for the backend, you can deactivate it with:

```bash
deactivate
```

---

## Planned Docker Compose setup

A Docker Compose configuration for running all services (PostgreSQL + TimescaleDB, Redis, FastAPI backend, Next.js frontend, and the background worker) is planned but **not yet included** in this repository.

Once available, it will allow you to start the full stack with a single command, and these docs will be updated with exact `docker compose` instructions.

---

## Troubleshooting

- **Port conflicts:** Ensure ports 3000, 8000, 5432, and 6379 are not already in use.
- **Database migrations:** Run `alembic upgrade head` inside the backend environment if migrations are pending.
- **Environment variables:** Verify your `.env` file contains all required variables listed in `.env.example`.

---

## Next Steps

- Read [docs/architecture.md](architecture.md) to understand the system design
- Review [docs/contributing.md](contributing.md) before opening a pull request
- Check [docs/roadmap.md](roadmap.md) to see what is planned and in progress
