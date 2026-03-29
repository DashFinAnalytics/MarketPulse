# PR3 Staged App Integration

This directory contains the conservative PR3 integration artifacts for wiring
`app.py` into the PR1 scaffold.

## Why staged rather than directly replacing `app.py`

`app.py` is the highest-risk integration point in the repository because it is
large, monolithic, and user-facing. In this session, the available GitHub write
path safely supports adding new files, but does not expose a simple in-place
update action for existing tracked files.

Given the breakage risk, PR3 is staged as:
- a reusable helper module: `refactor_staging/pr3/app_runtime.py`
- a concrete patch guide: `refactor_staging/pr3/app_integration_patch.md`

## Intended result

After applying the staged patch, `app.py` should:
- initialize through `initialize_app()`
- render system status through `get_app_status()`
- use structured logging through `get_logger()`
- run service-cache cleanup through `periodic_cleanup()`
- centralize top-level UI error rendering

## Scope constraints

PR3 should not:
- redesign page taxonomy
- alter business logic for portfolio math, backtesting, or options pricing
- mix in unrelated code-style churn
