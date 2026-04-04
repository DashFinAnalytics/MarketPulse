"""Tests for app_init.py — AppInitializer and related functions."""

import pytest
from unittest.mock import patch, MagicMock


# ── _get_git_sha ──────────────────────────────────────────────────────────────

class TestGetGitSha:
    """Tests for _get_git_sha()."""

    def test_returns_string(self):
        from app_init import _get_git_sha
        result = _get_git_sha()
        assert isinstance(result, str)

    def test_returns_unknown_on_git_failure(self):
        import subprocess
        from app_init import _get_git_sha
        with patch("app_init.subprocess.run", side_effect=subprocess.SubprocessError("no git")):
            result = _get_git_sha()
        assert result == "unknown"

    def test_returns_unknown_when_git_not_found(self):
        from app_init import _get_git_sha
        with patch("app_init.subprocess.run", side_effect=FileNotFoundError("no git")):
            result = _get_git_sha()
        assert result == "unknown"

    def test_returns_unknown_on_timeout(self):
        import subprocess
        from app_init import _get_git_sha
        with patch("app_init.subprocess.run", side_effect=subprocess.TimeoutExpired(["git"], 5)):
            result = _get_git_sha()
        assert result == "unknown"

    def test_returns_sha_when_git_available(self):
        """When git runs successfully, returns the stdout (trimmed)."""
        import subprocess
        from app_init import _get_git_sha
        mock_result = MagicMock()
        mock_result.stdout = "abc1234\n"
        with patch("app_init.subprocess.run", return_value=mock_result):
            result = _get_git_sha()
        assert result == "abc1234"

    def test_returns_unknown_when_stdout_empty(self):
        import subprocess
        from app_init import _get_git_sha
        mock_result = MagicMock()
        mock_result.stdout = ""
        with patch("app_init.subprocess.run", return_value=mock_result):
            result = _get_git_sha()
        assert result == "unknown"


# ── AppInitializer ───────────────────────────────────────────────────────────

class TestAppInitializer:
    """Tests for the AppInitializer class."""

    def _make_initializer(self):
        from app_init import AppInitializer
        return AppInitializer()

    def test_instantiation(self):
        init = self._make_initializer()
        assert init is not None
        assert isinstance(init.initialization_status, dict)

    def test_initialization_status_starts_empty(self):
        init = self._make_initializer()
        assert init.initialization_status == {}

    def test_initialize_returns_dict(self):
        init = self._make_initializer()
        with patch.object(init, "_setup_logging"):
            with patch.object(init, "_validate_configuration"):
                with patch.object(init, "_setup_cache"):
                    with patch.object(init, "_initialize_database"):
                        with patch.object(init, "_perform_health_checks"):
                            result = init.initialize()
        assert isinstance(result, dict)

    def test_initialize_sets_status_ready(self):
        init = self._make_initializer()
        with patch.object(init, "_setup_logging"):
            with patch.object(init, "_validate_configuration"):
                with patch.object(init, "_setup_cache"):
                    with patch.object(init, "_initialize_database"):
                        with patch.object(init, "_perform_health_checks"):
                            result = init.initialize()
        assert result["status"] == "ready"

    def test_setup_cache_sets_status(self):
        init = self._make_initializer()
        with patch("app_init.cache") as mock_cache:
            mock_cache.clear.return_value = None
            init._setup_cache()
        assert "cache" in init.initialization_status
        assert init.initialization_status["cache"]["status"] == "initialized"

    def test_setup_cache_handles_exception(self):
        init = self._make_initializer()
        with patch("app_init.cache") as mock_cache:
            mock_cache.clear.side_effect = RuntimeError("cache broken")
            init._setup_cache()
        assert init.initialization_status["cache"]["status"] == "degraded"

    def test_validate_configuration_stores_config_info(self):
        init = self._make_initializer()
        init._validate_configuration()
        assert "configuration" in init.initialization_status
        cfg = init.initialization_status["configuration"]
        assert "environment" in cfg
        assert "debug" in cfg
        assert "warnings" in cfg

    def test_initialize_database_skipped_when_not_available(self):
        init = self._make_initializer()
        with patch("app_init.config") as mock_cfg:
            mock_cfg.database.is_available = False
            init._initialize_database()
        assert init.initialization_status["database"]["status"] == "disabled_or_unconfigured"

    def test_initialize_database_handles_exception(self):
        init = self._make_initializer()
        with patch("app_init.config") as mock_cfg:
            mock_cfg.database.is_available = True
        with patch("builtins.__import__", side_effect=ImportError("no db")):
                init._initialize_database()

        assert init.initialization_status["database"]["status"] == "degraded"
        assert "no db" in init.initialization_status["database"]["error"]    

    def test_perform_health_checks_runs_cache_check(self):
        init = self._make_initializer()
        with patch("app_init.cache") as mock_cache:
            mock_cache.set.return_value = None
            mock_cache.get.return_value = "ok"
            mock_cache.delete.return_value = None
            with patch("app_init.config") as mock_cfg:
                mock_cfg.database.is_available = False
                mock_cfg.api.ai_available = False
                mock_cfg.app.enable_ai_analysis = False
                init._perform_health_checks()
        assert "health_checks" in init.initialization_status
        assert "cache" in init.initialization_status["health_checks"]

    def test_perform_health_checks_cache_passes(self):
        init = self._make_initializer()
        with patch("app_init.cache") as mock_cache:
            mock_cache.set.return_value = None
            mock_cache.get.return_value = "ok"
            mock_cache.delete.return_value = None
            with patch("app_init.config") as mock_cfg:
                mock_cfg.database.is_available = False
                mock_cfg.api.ai_available = True
                mock_cfg.app.enable_ai_analysis = True
                init._perform_health_checks()
        assert init.initialization_status["health_checks"]["cache"] is True

    def test_perform_health_checks_cache_fails_gracefully(self):
        init = self._make_initializer()
        with patch("app_init.cache") as mock_cache:
            mock_cache.set.side_effect = Exception("cache error")
            with patch("app_init.config") as mock_cfg:
                mock_cfg.database.is_available = False
                mock_cfg.app.enable_ai_analysis = False
                init._perform_health_checks()
        assert init.initialization_status["health_checks"]["cache"] is False


# ── get_system_info ──────────────────────────────────────────────────────────

class TestGetSystemInfo:
    """Tests for AppInitializer.get_system_info()."""

    def test_returns_dict_with_required_keys(self):
        from app_init import AppInitializer
        init = AppInitializer()
        with patch("app_init.cache") as mock_cache:
            mock_cache.stats.return_value = {"active_entries": 0}
            result = init.get_system_info()
        assert "app_version" in result
        assert "environment" in result
        assert "initialization_status" in result
        assert "features" in result
        assert "cache_stats" in result

    def test_features_dict_has_expected_flags(self):
        from app_init import AppInitializer
        init = AppInitializer()
        with patch("app_init.cache") as mock_cache:
            mock_cache.stats.return_value = {}
            result = init.get_system_info()
        features = result["features"]
        assert "ai_analysis" in features
        assert "news_fetching" in features
        assert "real_time_updates" in features


# ── Module-level convenience functions ───────────────────────────────────────

class TestModuleLevelFunctions:
    """Tests for initialize_app() and get_app_status() module functions."""

    def test_initialize_app_returns_dict(self):
        from app_init import AppInitializer
        from unittest.mock import patch as _patch
        new_init = AppInitializer()
        with _patch("app_init.app_initializer", new_init):
            with _patch.object(new_init, "_setup_logging"):
                with _patch.object(new_init, "_validate_configuration"):
                    with _patch.object(new_init, "_setup_cache"):
                        with _patch.object(new_init, "_initialize_database"):
                            with _patch.object(new_init, "_perform_health_checks"):
                                from app_init import initialize_app
                                result = initialize_app()
        assert isinstance(result, dict)

    def test_get_app_status_returns_dict(self):
        from app_init import get_app_status
        with patch("app_init.cache") as mock_cache:
            mock_cache.stats.return_value = {}
            result = get_app_status()
        assert isinstance(result, dict)