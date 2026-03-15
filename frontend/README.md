# Frontend

This directory will contain the MarketPulse Next.js frontend application.

## Stack

- **Framework:** Next.js 14+ (App Router)
- **Language:** TypeScript (strict)
- **Styling:** TBD (Tailwind CSS or CSS Modules)
- **State Management:** TBD (Zustand / React Query)
- **Charts:** TBD (lightweight-charts / Recharts)

## Setup

See [docs/getting-started.md](../docs/getting-started.md) for full setup instructions.

```bash
npm install
npm run dev
```

## Structure (planned)

```
frontend/
├── app/                  # Next.js App Router pages and layouts
│   ├── (dashboard)/      # Market dashboard route group
│   ├── instruments/      # Instrument detail pages
│   ├── portfolio/        # Portfolio views
│   └── layout.tsx        # Root layout
├── components/           # Shared UI components
├── lib/                  # API client, utilities, types
├── public/               # Static assets
├── styles/               # Global styles
├── next.config.ts
├── tsconfig.json
└── package.json
```
