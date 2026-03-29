# PR2 Staged Replacement Files

This directory contains the intended PR2 replacement files for:
- `database.py`
- `utils/data_fetcher.py`

They are staged here because the current GitHub connector path available in this
session supports creating new files safely, but not directly updating existing
tracked files through a high-level `update_file` action.

## Intended application

Replace:
- `database.py` with `refactor_staging/pr2/database.py`
- `utils/data_fetcher.py` with `refactor_staging/pr2/utils/data_fetcher.py`

## PR2 goals implemented here

- database remains optional and degrades gracefully
- database adds health checks and context-managed sessions
- fetcher adds symbol validation, retries, structured logging hooks, and safer
  persistence behavior
- broad org-repo feature coverage is preserved
