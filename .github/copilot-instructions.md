# Copilot Instructions for MarketPulse

MarketPulse is a multi-asset market intelligence and portfolio analytics platform. It is being built as a set of independently deployable services: a **Next.js frontend**, a **FastAPI (Python) backend API**, a **background worker queue**, and an **isolated AI service layer**, all backed by **PostgreSQL + TimescaleDB** and **Redis**.

---

## Repository Layout

```
MarketPulse/
├── frontend/          # Next.js (TypeScript) frontend
├── backend/           # FastAPI (Python 3.12+) backend API
├── page_modules/      # Streamlit page modules (current prototype)
├── utils/             # Shared Python utilities
├── docs/
│   ├── adr/           # Architecture Decision Records
│   ├── architecture.md
│   ├── contributing.md
│   ├── getting-started.md
│   └── roadmap.md
├── app.py             # Streamlit entry point (current prototype)
├── database.py        # Database helpers
├── pyproject.toml     # Python project & dependency config (uv)
├── .env.example       # Environment variable template
└── README.md
```

> The repository is in early development. The production architecture targets FastAPI + Next.js; the current prototype uses Streamlit.

---

## Technology Stack

| Layer | Technology |
|---|---|
| Frontend (target) | Next.js 14+ (TypeScript, App Router) |
| Backend API (target) | FastAPI, Python 3.12+, Pydantic v2 |
| Prototype UI | Streamlit |
| Primary Database | PostgreSQL 16+ |
| Time-Series Database | TimescaleDB |
| Cache | Redis 7+ |
| Worker Queue | ARQ |
| AI Services | Isolated Python service |
| Package Manager | `uv` (see `pyproject.toml` / `uv.lock`) |

---

## Coding Standards

### Python (backend, utils, page_modules)

- **Style:** PEP 8
- **Formatter:** `black` (line length 88)
- **Linter:** `ruff`
- **Type hints:** Required for all public functions and methods
- **Docstrings:** Google-style for modules, classes, and public functions
- **Error handling:** No bare `except`; always handle or re-raise with context
- **External inputs:** Validate all external inputs before use

### TypeScript / JavaScript (frontend)

- **Language:** TypeScript in strict mode
- **Linter/formatter:** ESLint + Prettier (project config)
- **Naming:** camelCase for variables/functions; PascalCase for components and types
- **Components:** Functional components with hooks only; no class components
- **Error handling:** No unhandled promise rejections

### General

- No dead code or commented-out code in PRs
- Prefer explicit over implicit
- Update `.env.example` when adding new environment variables (never commit `.env` or secrets)
- Add an ADR in `docs/adr/` for significant architectural decisions

---

## Branching Strategy

MarketPulse uses **trunk-based development** against `main`.

| Prefix | Purpose |
|---|---|
| `feature/<short-description>` | New features |
| `fix/<short-description>` | Bug fixes |
| `docs/<short-description>` | Documentation only |
| `chore/<short-description>` | Dependencies, tooling, CI config |
| `copilot/<description>` | AI-assisted development branches |

`main` is protected — direct pushes are blocked. All changes go through a PR.

---

## Commit Message Convention

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <short summary>

[optional body]

[optional footer]
```

| Type | Description |
|---|---|
| `feat` | New feature |
| `fix` | Bug fix |
| `docs` | Documentation only |
| `style` | Formatting/whitespace (no logic change) |
| `refactor` | Code restructuring without behavior change |
| `test` | Adding or updating tests |
| `chore` | Build tooling, dependencies, CI config |
| `perf` | Performance improvement |

Examples:
```
feat(market): add global market dashboard endpoint
fix(portfolio): correct unrealized P&L calculation for multi-currency holdings
chore(deps): upgrade fastapi to 0.111.0
```

---

## Pull Request Guidelines

- One PR per logical unit of work
- Title must follow the commit convention above
- Description must include what changed, why, and `Closes #<issue-number>`
- At least one team member review required before merging
- Squash and merge to keep `main` history clean

**PR checklist:**
- [ ] Tests pass
- [ ] No new linting errors
- [ ] Documentation updated (if behavior changed)
- [ ] `.env.example` updated (if new env vars added)
- [ ] No secrets committed

---

## Environment Setup

```bash
# Copy and configure environment variables
cp .env.example .env

# Install Python dependencies (using uv)
uv sync

# Run the Streamlit prototype
uv run streamlit run app.py
```

Key environment variables (see `.env.example`):

| Variable | Description |
|---|---|
| `DATABASE_URL` | PostgreSQL connection string |
| `REDIS_URL` | Redis connection string |
| `MARKET_DATA_API_KEY` | External market data provider API key |
| `AI_SERVICE_URL` | Internal AI service base URL |
| `AI_SERVICE_API_KEY` | Internal AI service API key |

---

## Testing

### Backend

```bash
cd backend
pytest
```

### Frontend

```bash
cd frontend
npm run test
```

---

## API Design Conventions

- **Base path:** `/api/v1/`
- **Auth header:** `Authorization: Bearer <token>`
- **Pagination:** Cursor-based for list endpoints
- **Error envelope:**
  ```json
  {
    "error": {
      "code": "RESOURCE_NOT_FOUND",
      "message": "Instrument not found",
      "details": {}
    }
  }
  ```
- **WebSocket base:** `/ws/v1/`

Key resource namespaces: `/api/v1/market/`, `/api/v1/instruments/`, `/api/v1/portfolio/`, `/api/v1/signals/`, `/api/v1/news/`, `/api/v1/calendar/`, `/api/v1/filings/`, `/api/v1/users/`, `/api/v1/workspaces/`

---

## Documentation

- Update `docs/` when making architectural or behavioral changes
- All documentation in Markdown
- Add an ADR in `docs/adr/` for significant architectural choices (use `docs/adr/0000-adr-template.md` as a template)
