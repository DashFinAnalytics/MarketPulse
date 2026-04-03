"""Test configuration and shared fixtures.

Sets up sys.path so tests can import from the project root.
Provides a mock streamlit module for tests that import code using Streamlit
decorators/UI calls.
"""
from __future__ import annotations

import sys
import types
import os
from unittest.mock import MagicMock

# Ensure project root is on sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


def _make_streamlit_mock() -> types.ModuleType:
    """Create a minimal mock streamlit module that makes decorators pass-through."""
    mock_st = MagicMock(name="streamlit")

    # Make cache decorators transparent (return the wrapped function unchanged)
    def passthrough_decorator(*args, **kwargs):
        if len(args) == 1 and callable(args[0]):
            # Called as @decorator directly
            return args[0]
        # Called as @decorator(...) with arguments
        def inner(func):
            return func
        return inner

    mock_st.cache_data = passthrough_decorator
    mock_st.cache_resource = passthrough_decorator

    # Make sidebar behave like a context manager
    sidebar_mock = MagicMock()
    sidebar_mock.expander.return_value.__enter__ = MagicMock(return_value=None)
    sidebar_mock.expander.return_value.__exit__ = MagicMock(return_value=False)
    mock_st.sidebar = sidebar_mock

    return mock_st


# Install the mock before any test module imports code that uses streamlit
if "streamlit" not in sys.modules:
    sys.modules["streamlit"] = _make_streamlit_mock()