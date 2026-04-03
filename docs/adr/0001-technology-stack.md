# ADR-0001: Technology Stack Selection

**Date:** 2026-03-15
**Status:** Accepted

---

## Context

MarketPulse v2 is being built from first principles. A technology stack must be selected for the frontend, backend API, databases, caching layer, and background processing. The stack must support:

- Real-time data streaming (WebSocket)
- High-frequency time-series data queries
- Async-first backend for concurrent I/O-bound workloads
- Rapid frontend development with server-side rendering
- A strong ecosystem for financial and data-science tooling (Python)

---

## Decision

Adopt the following technology stack:

| Layer | Technology |
|---|---|
| Frontend | Next.js 14+ (TypeScript) |
| Backend API | FastAPI (Python 3.12+) |
| Primary Database | PostgreSQL 16+ |
| Time-Series Database | TimescaleDB (PostgreSQL extension) |
| Cache | Redis 7+ |
| Worker Queue | ARQ (async Redis-based job queue) |
| Containerization | Docker / Docker Compose |

---

## Rationale

### Next.js (Frontend)

- Industry-standard React framework with SSR, static generation, and API routes
- Strong TypeScript support
- Large ecosystem and community
- Enables PWA capabilities needed for Phase 4 mobile goals

### FastAPI (Backend)

- Native async support — critical for high-concurrency market data endpoints
- Automatic OpenAPI/Swagger documentation generation
- Strong type safety via Pydantic
- Rich Python ecosystem for financial analytics (pandas, numpy, scipy)
- WebSocket support for streaming endpoints

### PostgreSQL + TimescaleDB

- PostgreSQL is the most capable open-source relational database
- TimescaleDB extends PostgreSQL natively for time-series data — no separate query language or operational overhead
- Supports continuous aggregates for pre-computed OHLC candles at multiple timeframes

### Redis

- Widely used, battle-tested in-memory data store
- Used for both API response caching and pub/sub to broadcast live price updates to WebSocket connections

### ARQ

- Lightweight async job queue built on Redis — consistent with the existing Redis dependency
- Simpler operational model than Celery for the project's scale

---

## Consequences

**Positive:**
- Consistent Python ecosystem across backend and AI services
- TimescaleDB avoids a separate time-series database (InfluxDB, etc.), reducing operational complexity
- FastAPI's auto-generated docs improve developer experience and API discoverability
- Next.js SSR supports SEO if needed for public-facing pages

**Negative / Trade-offs:**
- Python has higher memory footprint than Go/Rust for high-throughput services — may need to revisit for extreme scale
- TimescaleDB requires PostgreSQL version compatibility management
- Redis adds an additional infrastructure dependency

---

## Alternatives Considered

| Option | Reason not chosen |
|---|---|
| Django REST Framework | Sync-first; more boilerplate; slower for async I/O-heavy workloads |
| Express.js (Node) backend | Forfeits Python data science ecosystem |
| InfluxDB (time-series) | Separate query language (Flux/InfluxQL), separate operational stack |
| Celery (worker queue) | Higher complexity than ARQ for async Python; requires broker config |
| Vue.js / Nuxt | Smaller ecosystem for financial UI component libraries vs React |
