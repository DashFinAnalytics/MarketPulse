# Repository Rules

This document is the concise source of truth for contribution boundaries and
anti-drift rules.

## 1. Product base

`DashFinAnalytics/MarketPulse` is the product base.

Patterns from earlier prototypes may be imported, but the org repo must remain
the single canonical implementation.

## 2. Anti-drift rules

- Do not keep duplicate modules alive for the same workflow.
- Do not replace broader org-repo functionality with narrower donor code.
- Do not let infrastructure PRs become stealth feature PRs.
- Do not silently change business semantics in portfolio, options, or
  backtesting code.

## 3. Optional-service rule

Optional services must degrade gracefully.

Examples:
- missing database config should not crash startup
- unavailable AI service should disable AI-dependent features, not the app
- temporary external API failures should log and degrade, not silently corrupt
  behavior

## 4. Error-boundary rule

- Raise typed exceptions near the source.
- Log structured context near the source.
- Convert errors into user-facing messages at the UI boundary.

## 5. PR boundary rule

One PR should do one coherent thing.

Expected refactor progression:
- PR1: scaffold
- PR2: service/database hardening
- PR3: app integration

## 6. Review rule

A reviewer should be able to answer these questions quickly:
- What changed?
- Why did it change?
- What was intentionally left unchanged?
- Could this have been split further?

## 7. Documentation rule

When repository rules or architecture change, update:
- `CONTRIBUTING.md`
- `AGENTS.md`
- PR templates
- this rules document

## 8. Default bias

Bias toward small, explicit, reviewable changes.
