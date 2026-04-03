# PR3 App Integration Patch Guide

This patch is intentionally conservative. It wires `app.py` into the PR1
scaffold without attempting to redesign page logic.

## 1. Replace raw logging and startup imports

At the top of `app.py`, add:

```python
from app_init import get_app_status
from config import config
from refactor_staging.pr3.app_runtime import (
    cleanup_service_cache,
    database_is_ready,
    initialize_application,
    render_system_status_sidebar,
    render_ui_error,
)
from utils.logging_config import get_logger
```

Remove:

```python
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
```

Replace with:

```python
logger = get_logger(__name__)
```

## 2. Page configuration should use centralized app config

Replace hard-coded page config with:

```python
st.set_page_config(
    page_title=config.app.title,
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)
```

## 3. Replace ad hoc startup with scaffold initialization

Remove the legacy startup block:

```python
@st.cache_resource
def initialize_database():
    ...

@st.cache_resource
def get_data_fetcher():
    return DataFetcher()

try:
    db_initialized = initialize_database()
except:
    db_initialized = False

data_fetcher = get_data_fetcher()
```

Replace it with:

```python
@st.cache_resource
def get_data_fetcher():
    return DataFetcher()

app_init_status = initialize_application()
db_initialized = database_is_ready(app_init_status)
data_fetcher = get_data_fetcher()
cleanup_service_cache()
```

## 4. Render system status in the sidebar

After sidebar header setup, add:

```python
render_system_status_sidebar()
```

## 5. Manual refresh should also clean service cache

Replace the manual refresh block:

```python
if refresh_button:
    st.cache_data.clear()
    st.rerun()
```

with:

```python
if refresh_button:
    st.cache_data.clear()
    cleanup_service_cache()
    st.rerun()
```

## 6. Centralize startup error rendering

Wrap any top-level initialization or page-entry exceptions with:

```python
try:
    ...
except Exception as exc:
    render_ui_error("Application error", exc)
```

## 7. Replace broad silent exception swallowing where safe

For patterns like:

```python
except Exception:
    pass
```

prefer:

```python
except Exception as exc:
    logger.warning("Non-critical UI block failed", error=str(exc))
```

Apply this only where the block is clearly optional, such as:
- banner rendering
- market-hours widget rendering
- ticker tape rendering
- cache-cleanup side effects

## 8. Do not mix PR3 with feature logic changes

Do not alter:
- portfolio calculations
- backtesting logic
- options calculations
- chart semantics
- page taxonomy

PR3 is only for integration into the scaffold.
