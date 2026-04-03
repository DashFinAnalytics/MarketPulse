"""Tests for DataFetcher._validate_symbol in PR2 data_fetcher modules.

Both refactor_staging/pr2/utils/data_fetcher.py and
refactor_staging/pr2/live_replacements/utils/data_fetcher.py are new files
added in this PR. Tests target the symbol validation logic which is pure /
side-effect-free and can be exercised without network access.
"""
from __future__ import annotations

import sys
from unittest.mock import MagicMock

import pytest

# ---------------------------------------------------------------------------
# Mock external dependencies before importing the module.
# conftest.py already handles sqlalchemy, streamlit, yfinance at collection
# time, so we only guard here as a belt-and-suspenders for standalone runs.
# We deliberately do NOT mock the `database` module here because
# test_database_changes.py needs to import the real database.py.
# ---------------------------------------------------------------------------
if "streamlit" not in sys.modules:
    sys.modules["streamlit"] = MagicMock()
if "yfinance" not in sys.modules:
    sys.modules["yfinance"] = MagicMock()

# ---------------------------------------------------------------------------
# Import under test
# ---------------------------------------------------------------------------
from utils.exceptions import ValidationError

import refactor_staging.pr2.live_replacements.utils.data_fetcher as live_df_mod
import refactor_staging.pr2.utils.data_fetcher as staged_df_mod


# ---------------------------------------------------------------------------
# Shared test logic, parameterised over both modules
# ---------------------------------------------------------------------------

def _make_fetcher(module):
    """Instantiate a DataFetcher from the given module."""
    fetcher = module.DataFetcher.__new__(module.DataFetcher)
    fetcher.retry_attempts = 3
    return fetcher


MODULES = [
    ("live_replacements", live_df_mod),
    ("staged", staged_df_mod),
]


# ---------------------------------------------------------------------------
# Valid symbol tests
# ---------------------------------------------------------------------------

class TestValidateSymbolValid:
    @pytest.mark.parametrize("module_name,module", MODULES)
    def test_simple_uppercase_symbol(self, module_name, module):
        fetcher = _make_fetcher(module)
        assert fetcher._validate_symbol("AAPL") == "AAPL"

    @pytest.mark.parametrize("module_name,module", MODULES)
    def test_lowercase_normalized_to_uppercase(self, module_name, module):
        fetcher = _make_fetcher(module)
        assert fetcher._validate_symbol("aapl") == "AAPL"

    @pytest.mark.parametrize("module_name,module", MODULES)
    def test_leading_trailing_whitespace_stripped(self, module_name, module):
        fetcher = _make_fetcher(module)
        assert fetcher._validate_symbol("  MSFT  ") == "MSFT"

    @pytest.mark.parametrize("module_name,module", MODULES)
    def test_caret_prefix_preserved_in_return(self, module_name, module):
        # ^GSPC: caret is removed from the cleaned version for isalnum check,
        # but the normalized value (with caret) is returned.
        fetcher = _make_fetcher(module)
        result = fetcher._validate_symbol("^GSPC")
        assert result == "^GSPC"

    @pytest.mark.parametrize("module_name,module", MODULES)
    def test_equals_suffix_preserved_in_return(self, module_name, module):
        # Forex like EURUSD=X
        fetcher = _make_fetcher(module)
        result = fetcher._validate_symbol("EURUSD=X")
        assert result == "EURUSD=X"

    @pytest.mark.parametrize("module_name,module", MODULES)
    def test_dot_in_symbol_preserved(self, module_name, module):
        fetcher = _make_fetcher(module)
        result = fetcher._validate_symbol("BRK.B")
        assert result == "BRK.B"

    @pytest.mark.parametrize("module_name,module", MODULES)
    def test_dash_in_symbol_preserved(self, module_name, module):
        fetcher = _make_fetcher(module)
        result = fetcher._validate_symbol("BF-B")
        assert result == "BF-B"

    @pytest.mark.parametrize("module_name,module", MODULES)
    def test_future_contract_format(self, module_name, module):
        # e.g. "ES=F"
        fetcher = _make_fetcher(module)
        result = fetcher._validate_symbol("ES=F")
        assert result == "ES=F"

    @pytest.mark.parametrize("module_name,module", MODULES)
    def test_numeric_symbol(self, module_name, module):
        fetcher = _make_fetcher(module)
        result = fetcher._validate_symbol("1234")
        assert result == "1234"


# ---------------------------------------------------------------------------
# Invalid symbol tests
# ---------------------------------------------------------------------------

class TestValidateSymbolInvalid:
    @pytest.mark.parametrize("module_name,module", MODULES)
    def test_empty_string_raises(self, module_name, module):
        fetcher = _make_fetcher(module)
        with pytest.raises(ValidationError):
            fetcher._validate_symbol("")

    @pytest.mark.parametrize("module_name,module", MODULES)
    def test_none_raises(self, module_name, module):
        fetcher = _make_fetcher(module)
        with pytest.raises(ValidationError):
            fetcher._validate_symbol(None)  # type: ignore[arg-type]

    @pytest.mark.parametrize("module_name,module", MODULES)
    def test_integer_raises(self, module_name, module):
        fetcher = _make_fetcher(module)
        with pytest.raises(ValidationError):
            fetcher._validate_symbol(42)  # type: ignore[arg-type]

    @pytest.mark.parametrize("module_name,module", MODULES)
    def test_special_chars_only_raises(self, module_name, module):
        fetcher = _make_fetcher(module)
        # After removing all allowed special chars, nothing remains → not isalnum
        with pytest.raises(ValidationError):
            fetcher._validate_symbol("!@#$")

    @pytest.mark.parametrize("module_name,module", MODULES)
    def test_space_only_raises(self, module_name, module):
        fetcher = _make_fetcher(module)
        with pytest.raises(ValidationError):
            fetcher._validate_symbol("   ")

    @pytest.mark.parametrize("module_name,module", MODULES)
    def test_symbol_with_brackets_raises(self, module_name, module):
        fetcher = _make_fetcher(module)
        with pytest.raises(ValidationError):
            fetcher._validate_symbol("AAPL[1]")

    @pytest.mark.parametrize("module_name,module", MODULES)
    def test_error_message_contains_symbol(self, module_name, module):
        fetcher = _make_fetcher(module)
        with pytest.raises(ValidationError) as exc_info:
            fetcher._validate_symbol("BAD!SYMBOL")
        assert "BAD!SYMBOL" in str(exc_info.value)


# ---------------------------------------------------------------------------
# _sleep_before_retry (boundary test: no actual sleep)
# ---------------------------------------------------------------------------

class TestSleepBeforeRetry:
    @pytest.mark.parametrize("module_name,module", MODULES)
    def test_does_not_exceed_four_seconds_upper_bound(self, module_name, module, monkeypatch):
        """min(2**attempt, 4) must cap at 4."""
        import time
        slept: list = []
        monkeypatch.setattr(time, "sleep", lambda s: slept.append(s))
        fetcher = _make_fetcher(module)
        fetcher._sleep_before_retry(10)  # 2**10 = 1024, but min caps at 4
        assert slept[-1] == 4

    @pytest.mark.parametrize("module_name,module", MODULES)
    def test_sleep_for_attempt_zero_is_one_second(self, module_name, module, monkeypatch):
        import time
        slept: list = []
        monkeypatch.setattr(time, "sleep", lambda s: slept.append(s))
        fetcher = _make_fetcher(module)
        fetcher._sleep_before_retry(0)
        assert slept[-1] == 1  # 2**0 = 1


# ---------------------------------------------------------------------------
# _store_data_if_possible – should not raise even if db_manager fails
# ---------------------------------------------------------------------------

class TestStoreDataIfPossible:
    @pytest.mark.parametrize("module_name,module", MODULES)
    def test_no_raise_when_db_manager_fails(self, module_name, module):
        fetcher = _make_fetcher(module)
        db_mock = MagicMock()
        db_mock.store_financial_data.side_effect = RuntimeError("db down")
        original = module.db_manager
        module.db_manager = db_mock
        try:
            # Must not raise even when the underlying db_manager raises
            fetcher._store_data_if_possible("AAPL", {"price": 100.0}, "index")
        except Exception as exc:
            pytest.fail(f"_store_data_if_possible should not raise, got: {exc}")
        finally:
            module.db_manager = original

    @pytest.mark.parametrize("module_name,module", MODULES)
    def test_no_op_when_data_is_none(self, module_name, module):
        fetcher = _make_fetcher(module)
        db_mock = MagicMock()
        original = module.db_manager
        module.db_manager = db_mock
        try:
            fetcher._store_data_if_possible("AAPL", None, "index")
        finally:
            module.db_manager = original
        db_mock.store_financial_data.assert_not_called()