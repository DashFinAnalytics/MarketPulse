# Architecture

This document describes the planned high-level architecture of the MarketPulse platform, including service boundaries, data flow, and key technology decisions.

> **Status:** Draft — details will evolve as implementation begins.

---

## Table of Contents

- [Overview](#overview)
- [Service Boundaries](#service-boundaries)
- [Technology Stack](#technology-stack)
- [Data Flow](#data-flow)
- [API Design](#api-design)
- [Security Architecture](#security-architecture)
- [Observability](#observability)
- [Deployment Model](#deployment-model)

---

## Overview

MarketPulse is built as a set of independently deployable services with a clear separation between the user-facing frontend, the core API layer, background processing, and AI-enhanced services.

```
┌─────────────────────────────────────────────────────────────┐
│                        Clients                              │
│          Browser (Next.js PWA)  ·  Mobile (PWA)             │
└────────────────────────┬────────────────────────────────────┘
                         │ HTTPS / WebSocket
┌────────────────────────▼────────────────────────────────────┐
│                    API Gateway / BFF                         │
│            (FastAPI — versioned REST + WebSocket)            │
└──────┬──────────────────────────────────────────┬───────────┘
       │                                          │
┌──────▼──────────┐                   ┌───────────▼───────────┐
│   Core Services  │                   │    AI Service Layer    │
│  (market data,   │                   │  (NLP, sentiment,      │
│   portfolio,     │                   │   macro commentary)    │
│   analytics)     │                   └───────────────────────┘
└──────┬──────────┘
       │
┌──────▼──────────────────────────────────────────────────────┐
│                     Data Layer                               │
│   PostgreSQL + TimescaleDB  ·  Redis (cache/pub-sub)         │
└──────────────────────────────────┬──────────────────────────┘
                                   │
┌──────────────────────────────────▼──────────────────────────┐
│                  Background Worker Queue                     │
│         (price refresh, calendar sync, report generation)    │
└─────────────────────────────────────────────────────────────┘
```

---

## Service Boundaries

### Frontend (`frontend/`)

- **Framework:** Next.js (React)
- **Rendering:** Server-side rendering (SSR) + static generation where applicable
- **Real-time:** WebSocket client for live price/alert updates
- **PWA:** Service worker for offline support and installability
- **Responsibilities:**
  - UI rendering and user interaction
  - Client-side state management
  - Chart rendering (OHLC, heatmaps, portfolio views)
  - Dashboard builder UI

### Backend API (`backend/`)

- **Framework:** FastAPI (Python)
- **API style:** RESTful with JSON responses; WebSocket endpoints for streaming data
- **Auth:** JWT-based authentication with refresh tokens; MFA support
- **Versioning:** URL-based versioning (`/api/v1/`, `/api/v2/`)
- **Responsibilities:**
  - All data retrieval and business logic
  - Market data aggregation and normalization
  - Portfolio calculation engine
  - Trend signal computation
  - User and workspace management

### AI Service Layer

- **Isolation:** Separate service/container to avoid coupling core API to AI model availability
- **Interface:** Internal HTTP API called by the backend
- **Responsibilities:**
  - News sentiment scoring (NLP)
  - Macro event impact commentary generation
  - Regime change detection signals

### Background Worker Queue

- **Responsibilities:**
  - Periodic market data refresh
  - Economic calendar synchronization
  - Portfolio snapshot generation
  - Scheduled report compilation and distribution
  - Alert evaluation and notification dispatch

---

## Technology Stack

| Component | Technology | Notes |
|---|---|---|
| Frontend | Next.js 14+ | App Router, TypeScript |
| Backend API | FastAPI (Python 3.12+) | Async, Pydantic v2 |
| Primary Database | PostgreSQL 16+ | Relational data, user/portfolio records |
| Time-Series Database | TimescaleDB | Price history, market data |
| Cache | Redis 7+ | API response caching, pub/sub for live updates |
| Worker Queue | ARQ / Celery | Background jobs and scheduled tasks |
| AI Services | Python (isolated) | NLP model serving |
| Observability | Structured JSON logging + monitoring | TBD: Prometheus/Grafana or hosted solution |
| Auth | JWT + refresh tokens | MFA via TOTP |
| Containerization | Docker / Docker Compose | Local dev and deployment |

---

## Data Flow

### Market Data Ingestion

```
External Data Provider(s)
        │
        ▼
Background Worker (fetch + normalize)
        │
        ▼
TimescaleDB (raw + aggregated price data)
        │
        ▼
Redis (latest price cache + pub/sub broadcast)
        │
        ▼
API → WebSocket → Frontend
```

### Request Flow (Standard REST)

```
Browser → Next.js (SSR/API route or direct)
        → FastAPI backend (/api/v1/...)
        → Redis cache check
        → PostgreSQL / TimescaleDB (on cache miss)
        → Response (JSON)
        → Next.js renders page / updates state
```

---

## API Design

- **Base path:** `/api/v1/`
- **Authentication:** `Authorization: Bearer <token>` header
- **Pagination:** Cursor-based pagination for list endpoints
- **Error format:** Consistent JSON error envelope:
  ```json
  {
    "error": {
      "code": "RESOURCE_NOT_FOUND",
      "message": "Instrument not found",
      "details": {}
    }
  }
  ```
- **WebSocket:** `/ws/v1/` — streams for price updates, alert notifications

Key resource namespaces:

| Namespace | Description |
|---|---|
| `/api/v1/market/` | Global market overview, indices, movers |
| `/api/v1/instruments/` | Instrument detail, OHLC data, fundamentals |
| `/api/v1/portfolio/` | Holdings, transactions, P&L, risk metrics |
| `/api/v1/signals/` | Trend signal engine output |
| `/api/v1/news/` | News feed, sentiment |
| `/api/v1/calendar/` | Economic calendar, earnings calendar |
| `/api/v1/filings/` | SEC filings, insider transactions |
| `/api/v1/users/` | User management, preferences |
| `/api/v1/workspaces/` | Team workspaces, shared resources |

---

## Security Architecture

- **Authentication:** JWT access tokens (short-lived) + refresh tokens (longer-lived, rotated)
- **MFA:** TOTP-based multi-factor authentication
- **Authorization:** Role-based access control (RBAC) at workspace and resource level
- **Encryption:** TLS in transit; database encryption at rest
- **Audit trail:** Immutable activity log for all user actions on sensitive resources
- **Policy tracking:** User acknowledgment of compliance policies recorded

See [docs/adr/](adr/) for specific security decisions.

---

## Observability

- **Logging:** Structured JSON logs with correlation IDs across services
- **Metrics:** Request latency, error rates, cache hit rates, queue depths
- **Alerting:** Threshold-based alerts for data freshness, API errors, worker failures
- **Data freshness indicators:** Surfaced in the UI so users know when data was last updated

---

## Deployment Model

- **Local development:** Docker Compose (all services)
- **Production:** Container-based deployment (details TBD)
- **Environment configuration:** `.env` files with secrets management (never committed to source control)

See [docs/getting-started.md](getting-started.md) for local setup instructions.
