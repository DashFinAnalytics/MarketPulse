# PR2 and PR3 Integration Targets

This document turns the salvage plan into concrete file targets.

## PR2: hardening targets

### 1. `database.py`

Target outcomes:
- Add `health_check()` method
- Add context-managed session helper
- Standardize rollback/close behavior
- Keep database optional
- Avoid import-time hard failure if `DATABASE_URL` is missing

Specific merge intent:
- Keep org-repo schema and permissive startup behavior
- Import smaller-repo session/health patterns selectively

### 2. `utils/data_fetcher.py`

Target outcomes:
- Add `_validate_symbol()`
- Add retry logic around remote calls
- Add structured logging decorators around fetch methods
- Use typed exceptions near the source
- Preserve current broad feature set:
  - forex
  - futures
  - options
  - risk metrics
  - earnings/dividends
  - crypto
  - macro indicators
  - optimization

Specific merge intent:
- Keep org-repo breadth
- Import donor-repo guardrails only

## PR3: application integration targets

### 1. `app.py`

Target outcomes:
- Centralize application initialization through `initialize_app()`
- Add sidebar system-status display through `get_app_status()`
- Replace raw logging with `get_logger()`
- Use `periodic_cleanup()` for service cache maintenance
- Introduce centralized top-level error rendering for predictable behavior

### 2. Page-level behavior

Target outcomes:
- Optional-service features should show informative degraded-state messages
- Avoid silent `except: pass` unless there is a clearly documented reason
- Prefer logging warnings over swallowing failures

## Proposed file order of operations

1. PR2: `database.py`
2. PR2: `utils/data_fetcher.py`
3. PR3: `app.py`
4. PR3: selective page and module call-site cleanup

## Change boundaries

### Safe to change in PR2
- Session management internals
- logging/error patterns in fetchers
- configuration lookups

### Not safe to change in PR2
- visible portfolio math outputs
- backtesting model logic
- options calculations
- chart semantics

### Safe to change in PR3
- startup flow
- sidebar status
- centralized error wrappers
- cache cleanup cadence

### Not safe to change in PR3
- major feature additions
- page taxonomy redesign
- unrelated code-style churn
