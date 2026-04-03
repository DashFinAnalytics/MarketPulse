# Contributing to MarketPulse

This repository is being evolved in controlled stages. Contributions should aim
to reduce ambiguity, preserve feature breadth, and avoid architectural drift.

## Core principles

1. Keep changes narrow in scope.
2. Prefer explicit structure over implicit behavior.
3. Optional services must degrade gracefully.
4. Do not reduce the current breadth of the org repo in the name of cleanup.
5. Do not introduce duplicate sources of truth for the same workflow.
6. Avoid mixing infrastructure, service hardening, and feature work in one PR.

## Current refactor structure

The current intended trajectory is:

- **PR1**: infrastructure scaffold
  - config
  - app initialization
  - structured logging
  - exception taxonomy
  - service-layer cache
- **PR2**: service and database hardening
  - `database.py`
  - `utils/data_fetcher.py`
- **PR3**: application integration
  - `app.py`
  - startup/status/error-boundary integration

Contributors should align with this structure unless the repository direction is
explicitly updated in writing.

## Scope rules for pull requests

A pull request should do one coherent thing.

Good examples:
- add a config layer
- harden database session handling
- refactor data fetch retries and validation
- integrate app startup with centralized initialization

Bad examples:
- add config layer + redesign dashboard pages
- refactor database + change portfolio math outputs
- add logging + rewrite options logic + reformat unrelated files

## Runtime behavior rules

- Database support should remain optional unless the project direction changes.
- External services should fail in a controlled, observable way.
- Use typed exceptions near the source of failure.
- Convert exceptions into user-facing messages at the UI boundary.
- Prefer warning logs to silent failure swallowing.

## Source-of-truth rules

The org repo is the product base.

If code or patterns are imported from another prototype or donor repository:
- keep one canonical implementation in this repo
- do not keep near-duplicate modules alive in parallel
- document why a donor pattern was adopted

## Review expectations

Before requesting review, contributors should verify:
- scope is narrow and intentional
- no unrelated churn is included
- degraded-service behavior is preserved
- changes do not silently alter portfolio, options, or backtesting semantics
- docs and templates remain consistent with the actual code trajectory

## Documentation expectations

Update documentation when changing:
- architectural boundaries
- startup behavior
- error handling patterns
- contribution expectations
- review workflow

## When in doubt

Prefer a smaller PR with explicit rationale over a larger PR that mixes cleanup,
architecture, and feature behavior.
