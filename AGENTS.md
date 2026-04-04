# AGENTS.md

This file defines guardrails for AI-assisted contributions in this repository.

## Purpose

AI contributors are useful for scaffolding, hardening, and drafting, but they
must not become a source of architectural drift.

## Repository posture

- `DashFinAnalytics/MarketPulse` is the primary product repository.
- Donor repositories may inform patterns, but must not become competing sources
  of truth.
- Keep one canonical implementation for each workflow.

## What AI agents should optimize for

1. Precision over breadth.
2. Explicit structure over improvisation.
3. Narrow PR scope.
4. Low-risk changes at integration boundaries.
5. Preservation of existing org-repo feature breadth.

## What AI agents must avoid

- Omnibus PRs that mix unrelated concerns.
- Silent rewrites of business logic.
- Duplicate modules that overlap existing repo behavior.
- Replacing broad implementations with narrower donor versions.
- Large formatting-only churn during structural refactors.
- Hiding uncertainty behind confident language.

## Current intended code trajectory

Unless explicitly superseded, align with this order:

- **PR1**: infrastructure scaffold
- **PR2**: `database.py` and `utils/data_fetcher.py` hardening
- **PR3**: `app.py` integration into scaffold

## Change rules

### Safe AI contribution areas
- configuration centralization
- structured logging
- exception taxonomy
- cache abstractions
- session management hardening
- input validation
- retry logic
- startup/status helpers
- narrow documentation and templates

### Higher-risk areas requiring special caution
- `app.py`
- portfolio math
- backtesting logic
- options logic
- pricing assumptions
- chart semantics
- anything user-facing and stateful

In high-risk areas, prefer staged artifacts, patch guides, or small deltas over
large direct rewrites.

## Error-handling rules

- Optional services must degrade gracefully.
- Raise typed exceptions near the source.
- Translate exceptions into user-facing messages at the UI layer.
- Prefer logged warnings to `except: pass`.

## Reviewability rules

AI-generated changes should be easy to review.

That means:
- one coherent purpose per PR
- clear rationale in PR description
- explicit scope boundaries
- no hidden behavior changes
- documentation updated when rules or architecture change

## Documentation priority

If repository rules, templates, or contribution boundaries are missing, add
those early. It is easier to preserve good structure than retrofit it later.
