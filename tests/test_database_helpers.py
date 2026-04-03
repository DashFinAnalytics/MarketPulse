"""Tests for helper functions in refactor_staging/pr2/live_replacements/database.py.

These are pure utility functions introduced in the PR2 hardening:
  _safe_float, _normalize_symbol, _safe_json_dumps, _safe_json_loads

These functions have no external dependencies and are tested in isolation.
"""
from __future__ import annotations

import json
import sys
import os
import importlib
import pytest

# Directly import the helper functions from the staged module.
# We import the module via importlib so that sys.path manipulation is transparent.
_MODULE_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "refactor_staging", "pr2", "live_replacements",
)

# Use importlib to load the module under a unique name so it does NOT shadow
# the root database.py which is loaded by other test modules.
import importlib.util

_spec = importlib.util.spec_from_file_location(
    "pr2_live_database",
    os.path.join(_MODULE_PATH, "database.py"),
)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)

_safe_float = _mod._safe_float
_normalize_symbol = _mod._normalize_symbol
_safe_json_dumps = _mod._safe_json_dumps
_safe_json_loads = _mod._safe_json_loads


class TestSafeFloat:
    def test_integer_value(self):
        assert _safe_float(5) == 5.0

    def test_float_value(self):
        assert _safe_float(3.14) == pytest.approx(3.14)

    def test_string_number(self):
        assert _safe_float("2.5") == 2.5

    def test_none_returns_default(self):
        assert _safe_float(None) == 0.0

    def test_none_custom_default(self):
        assert _safe_float(None, default=-1.0) == -1.0

    def test_invalid_string_returns_default(self):
        assert _safe_float("abc") == 0.0

    def test_invalid_string_custom_default(self):
        assert _safe_float("xyz", default=99.0) == 99.0

    def test_zero_is_preserved(self):
        assert _safe_float(0) == 0.0

    def test_negative_value(self):
        assert _safe_float(-7.5) == -7.5

    def test_large_value(self):
        assert _safe_float(1e12) == pytest.approx(1e12)

    def test_empty_string_returns_default(self):
        assert _safe_float("") == 0.0

    def test_dict_returns_default(self):
        assert _safe_float({"a": 1}) == 0.0

    def test_list_returns_default(self):
        assert _safe_float([1, 2]) == 0.0

    def test_bool_true_coerces_to_float(self):
        # bool is a subclass of int in Python; True → 1.0
        assert _safe_float(True) == 1.0

    def test_bool_false_coerces_to_float(self):
        assert _safe_float(False) == 0.0


class TestNormalizeSymbol:
    def test_lowercase_to_uppercase(self):
        assert _normalize_symbol("aapl") == "AAPL"

    def test_already_uppercase_unchanged(self):
        assert _normalize_symbol("TSLA") == "TSLA"

    def test_strips_leading_whitespace(self):
        assert _normalize_symbol("  GOOG") == "GOOG"

    def test_strips_trailing_whitespace(self):
        assert _normalize_symbol("MSFT  ") == "MSFT"

    def test_strips_both_sides(self):
        assert _normalize_symbol("  spy  ") == "SPY"

    def test_mixed_case(self):
        assert _normalize_symbol("ApPl") == "APPL"

    def test_special_chars_preserved(self):
        # _normalize_symbol only strips/uppercases, it does NOT strip special chars
        assert _normalize_symbol("^VIX") == "^VIX"

    def test_empty_string(self):
        assert _normalize_symbol("") == ""

    def test_already_normalized(self):
        assert _normalize_symbol("SPY") == "SPY"


class TestSafeJsonDumps:
    def test_dict_serializes(self):
        result = _safe_json_dumps({"a": 1})
        assert json.loads(result) == {"a": 1}

    def test_list_serializes(self):
        result = _safe_json_dumps([1, 2, 3])
        assert json.loads(result) == [1, 2, 3]

    def test_string_serializes(self):
        result = _safe_json_dumps("hello")
        assert json.loads(result) == "hello"

    def test_none_serializes(self):
        result = _safe_json_dumps(None)
        assert result == "null"

    def test_nested_dict(self):
        data = {"outer": {"inner": [1, 2]}}
        result = _safe_json_dumps(data)
        assert json.loads(result) == data

    def test_non_serializable_uses_str_fallback(self):
        from datetime import datetime
        dt = datetime(2024, 1, 15, 10, 30)
        result = _safe_json_dumps({"ts": dt})
        # Should not raise; uses default=str
        parsed = json.loads(result)
        assert "ts" in parsed
        assert isinstance(parsed["ts"], str)

    def test_keys_sorted(self):
        data = {"z": 3, "a": 1, "m": 2}
        result = _safe_json_dumps(data)
        # sort_keys=True means keys appear in sorted order
        parsed_keys = list(json.loads(result).keys())
        assert parsed_keys == sorted(parsed_keys)

    def test_returns_string(self):
        assert isinstance(_safe_json_dumps({}), str)


class TestSafeJsonLoads:
    def test_valid_json_string(self):
        result = _safe_json_loads('{"key": "value"}', default={})
        assert result == {"key": "value"}

    def test_valid_json_list(self):
        result = _safe_json_loads('[1, 2, 3]', default=[])
        assert result == [1, 2, 3]

    def test_invalid_json_returns_default(self):
        result = _safe_json_loads("not json at all", default={"fallback": True})
        assert result == {"fallback": True}

    def test_none_input_returns_default(self):
        result = _safe_json_loads(None, default="default_val")
        assert result == "default_val"

    def test_empty_string_returns_default(self):
        result = _safe_json_loads("", default=[])
        assert result == []

    def test_partial_json_returns_default(self):
        result = _safe_json_loads('{"incomplete":', default=None)
        assert result is None

    def test_null_json_returns_none(self):
        # "null" is valid JSON
        result = _safe_json_loads("null", default="fallback")
        assert result is None

    def test_number_json(self):
        result = _safe_json_loads("42", default=0)
        assert result == 42

    def test_boolean_json(self):
        result = _safe_json_loads("true", default=False)
        assert result is True

    def test_default_not_used_when_valid(self):
        sentinel = object()
        result = _safe_json_loads('{"ok": 1}', default=sentinel)
        assert result != sentinel