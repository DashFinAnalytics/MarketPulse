# Refactor Guardrails: PR1 to PR3

This document defines the intended structure and merge constraints for the
MarketPulse salvage plan.

## Primary rule

`DashFinAnalytics/MarketPulse` is the product base.
`mohavro/MarketPulse` is a donor repo for infrastructure patterns, not a second
source of truth.

## PR1 scope: infrastructure scaffold

Allowed:
- Add `config.py`
- Add `app_init.py`
- Add `utils/logging_config.py`
- Add `utils/exceptions.py`
- Add `utils/cache.py`
- Minimal, low-risk application wiring only

Not allowed:
- Large feature rewrites
- UI redesign
- Business-logic rewrites hidden inside infra PR
- Replacing broad org-repo functionality with narrower donor-repo modules

## PR2 scope: hardening and service-layer consistency

Allowed:
- Refactor `database.py` toward context-managed sessions and health checks
- Refactor `utils/data_fetcher.py` to use validation, retries, typed exceptions,
  and structured logging
- Standardize degraded-service behavior

Not allowed:
- New product features unrelated to hardening
- Large page-level UI changes unless required for error handling

## PR3 scope: application integration

Allowed:
- Wire `app.py` into config/init/logging/cache patterns
- Add system-status display
- Normalize top-level error handling
- Replace ad hoc initialization paths with app initializer usage

Not allowed:
- Mixing PR3 with major feature additions
- Hidden behavioral changes to portfolio, backtesting, or options logic

## Structural guardrails

1. Optional services must degrade gracefully.
2. External service calls should raise typed exceptions near the source.
3. UI should convert exceptions into user-facing messages.
4. Streamlit cache and service cache should not be conflated.
5. Avoid duplicating modules that already exist in the org repo.
6. Prefer narrow PRs with explicit scope over omnibus refactors.

## Donor-repo salvage map

Retain from donor repo:
- config structure
- app initialization pattern
- structured logging
- exception taxonomy
- cache abstraction
- data-fetcher robustness patterns

Do not retain as separate modules:
- duplicate news fetcher
- duplicate fundamentals page
- duplicate product README direction

## Review checklist

- Does this PR reduce ambiguity?
- Does this PR centralize behavior rather than scatter it?
- Does this PR preserve org-repo feature breadth?
- Does this PR improve guardrails without creating hidden coupling?
- Can this PR be explained as one coherent unit of work?
