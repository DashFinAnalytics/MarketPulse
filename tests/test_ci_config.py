"""Tests for .circleci/config.yml structure and correctness.

These tests validate the CircleCI pipeline configuration introduced in this PR,
covering job definitions, workflow structure, dependency chains, caching keys,
and Docker image specifications.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

CIRCLECI_CONFIG_PATH = Path(__file__).parent.parent / ".circleci" / "config.yml"

# ---------------------------------------------------------------------------
# Fixture
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def ci_config() -> dict:
    """Load and return the parsed CircleCI config as a dict."""
    raw = CIRCLECI_CONFIG_PATH.read_text(encoding="utf-8")
    return yaml.safe_load(raw)


# ---------------------------------------------------------------------------
# File-level tests
# ---------------------------------------------------------------------------


class TestCiConfigFileExists:
    def test_config_file_exists(self) -> None:
        assert CIRCLECI_CONFIG_PATH.exists(), (
            f"CircleCI config not found at {CIRCLECI_CONFIG_PATH}"
        )

    def test_config_file_is_valid_yaml(self) -> None:
        raw = CIRCLECI_CONFIG_PATH.read_text(encoding="utf-8")
        result = yaml.safe_load(raw)
        assert result is not None
        assert isinstance(result, dict)

    def test_config_version_is_2_1(self, ci_config: dict) -> None:
        assert ci_config.get("version") == 2.1


# ---------------------------------------------------------------------------
# Orbs
# ---------------------------------------------------------------------------


class TestOrbs:
    def test_orbs_section_present(self, ci_config: dict) -> None:
        assert "orbs" in ci_config

    def test_python_orb_pinned(self, ci_config: dict) -> None:
        orbs = ci_config["orbs"]
        assert "python" in orbs, "Expected 'python' orb to be declared"
        assert orbs["python"] == "circleci/python@2.1.1"


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------


class TestCommands:
    EXPECTED_COMMANDS = {"install_uv", "restore_dep_cache", "save_dep_cache", "install_deps"}

    def test_commands_section_present(self, ci_config: dict) -> None:
        assert "commands" in ci_config

    @pytest.mark.parametrize("cmd", list(EXPECTED_COMMANDS))
    def test_command_defined(self, ci_config: dict, cmd: str) -> None:
        assert cmd in ci_config["commands"], f"Command '{cmd}' not found in commands"

    def test_install_uv_has_steps(self, ci_config: dict) -> None:
        cmd = ci_config["commands"]["install_uv"]
        assert "steps" in cmd
        assert len(cmd["steps"]) > 0

    def test_restore_dep_cache_has_cache_keys(self, ci_config: dict) -> None:
        cmd = ci_config["commands"]["restore_dep_cache"]
        steps = cmd["steps"]
        restore_step = next(
            (s for s in steps if isinstance(s, dict) and "restore_cache" in s), None
        )
        assert restore_step is not None
        keys = restore_step["restore_cache"]["keys"]
        assert len(keys) >= 2, "restore_dep_cache should have multiple fallback cache keys"

    def test_restore_cache_primary_key_includes_uv_lock_checksum(
        self, ci_config: dict
    ) -> None:
        cmd = ci_config["commands"]["restore_dep_cache"]
        steps = cmd["steps"]
        restore_step = next(s for s in steps if isinstance(s, dict) and "restore_cache" in s)
        primary_key = restore_step["restore_cache"]["keys"][0]
        assert 'checksum "uv.lock"' in primary_key

    def test_restore_cache_primary_key_includes_pyproject_checksum(
        self, ci_config: dict
    ) -> None:
        cmd = ci_config["commands"]["restore_dep_cache"]
        steps = cmd["steps"]
        restore_step = next(s for s in steps if isinstance(s, dict) and "restore_cache" in s)
        primary_key = restore_step["restore_cache"]["keys"][0]
        assert 'checksum "pyproject.toml"' in primary_key

    def test_save_dep_cache_key_matches_restore_primary_key(
        self, ci_config: dict
    ) -> None:
        """The save cache key must match the restore cache primary key exactly."""
        restore_steps = ci_config["commands"]["restore_dep_cache"]["steps"]
        restore_step = next(
            s for s in restore_steps if isinstance(s, dict) and "restore_cache" in s
        )
        primary_restore_key = restore_step["restore_cache"]["keys"][0]

        save_steps = ci_config["commands"]["save_dep_cache"]["steps"]
        save_step = next(
            s for s in save_steps if isinstance(s, dict) and "save_cache" in s
        )
        save_key = save_step["save_cache"]["key"]

        assert save_key == primary_restore_key, (
            f"save_cache key '{save_key}' does not match "
            f"restore_cache primary key '{primary_restore_key}'"
        )

    def test_save_dep_cache_paths_includes_venv(self, ci_config: dict) -> None:
        steps = ci_config["commands"]["save_dep_cache"]["steps"]
        save_step = next(s for s in steps if isinstance(s, dict) and "save_cache" in s)
        paths = save_step["save_cache"]["paths"]
        assert ".venv" in paths

    def test_install_deps_uses_frozen_sync(self, ci_config: dict) -> None:
        """install_deps must use 'uv sync --frozen' to ensure reproducible installs."""
        cmd = ci_config["commands"]["install_deps"]
        # Collect all 'command' values from run steps (YAML duplicate key: last wins)
        run_steps = [
            s["run"] for s in cmd["steps"] if isinstance(s, dict) and "run" in s
        ]
        commands_text = " ".join(
            step.get("command", "") for step in run_steps if isinstance(step, dict)
        )
        assert "--frozen" in commands_text, (
            "install_deps must pass --frozen to uv sync for reproducible installs"
        )

    def test_install_deps_installs_extra_dev(self, ci_config: dict) -> None:
        cmd = ci_config["commands"]["install_deps"]
        run_steps = [
            s["run"] for s in cmd["steps"] if isinstance(s, dict) and "run" in s
        ]
        commands_text = " ".join(
            step.get("command", "") for step in run_steps if isinstance(step, dict)
        )
        assert "--extra dev" in commands_text


# ---------------------------------------------------------------------------
# Jobs
# ---------------------------------------------------------------------------


EXPECTED_JOBS = {"lint", "type_check", "test", "security_scan", "smoke_test"}


class TestJobs:
    def test_jobs_section_present(self, ci_config: dict) -> None:
        assert "jobs" in ci_config

    @pytest.mark.parametrize("job", list(EXPECTED_JOBS))
    def test_job_defined(self, ci_config: dict, job: str) -> None:
        assert job in ci_config["jobs"], f"Job '{job}' not found"

    @pytest.mark.parametrize("job", list(EXPECTED_JOBS))
    def test_job_has_steps(self, ci_config: dict, job: str) -> None:
        assert "steps" in ci_config["jobs"][job], f"Job '{job}' missing steps"
        assert len(ci_config["jobs"][job]["steps"]) > 0

    @pytest.mark.parametrize("job", list(EXPECTED_JOBS))
    def test_job_has_checkout_step(self, ci_config: dict, job: str) -> None:
        steps = ci_config["jobs"][job]["steps"]
        assert "checkout" in steps, f"Job '{job}' missing checkout step"

    @pytest.mark.parametrize("job", list(EXPECTED_JOBS))
    def test_job_uses_python_3_12_image(self, ci_config: dict, job: str) -> None:
        """All jobs should use cimg/python:3.12 Docker image."""
        job_def = ci_config["jobs"][job]
        docker = job_def.get("docker", [])
        images = [entry.get("image", "") for entry in docker if isinstance(entry, dict)]
        assert any("python:3.12" in img for img in images), (
            f"Job '{job}' does not use a Python 3.12 image; found: {images}"
        )

    def test_lint_job_runs_ruff(self, ci_config: dict) -> None:
        steps = ci_config["jobs"]["lint"]["steps"]
        run_cmds = [
            s["run"].get("command", "")
            for s in steps
            if isinstance(s, dict) and "run" in s and isinstance(s["run"], dict)
        ]
        all_cmds = " ".join(run_cmds)
        assert "ruff" in all_cmds

    def test_lint_job_stores_artifacts(self, ci_config: dict) -> None:
        steps = ci_config["jobs"]["lint"]["steps"]
        artifact_steps = [s for s in steps if isinstance(s, dict) and "store_artifacts" in s]
        assert len(artifact_steps) > 0

    def test_type_check_job_runs_mypy(self, ci_config: dict) -> None:
        steps = ci_config["jobs"]["type_check"]["steps"]
        run_cmds = [
            s["run"].get("command", "")
            for s in steps
            if isinstance(s, dict) and "run" in s and isinstance(s["run"], dict)
        ]
        all_cmds = " ".join(run_cmds)
        assert "mypy" in all_cmds

    def test_test_job_runs_pytest(self, ci_config: dict) -> None:
        steps = ci_config["jobs"]["test"]["steps"]
        run_cmds = [
            s["run"].get("command", "")
            for s in steps
            if isinstance(s, dict) and "run" in s and isinstance(s["run"], dict)
        ]
        all_cmds = " ".join(run_cmds)
        assert "pytest" in all_cmds

    def test_test_job_stores_coverage_artifact(self, ci_config: dict) -> None:
        steps = ci_config["jobs"]["test"]["steps"]
        artifact_steps = [s for s in steps if isinstance(s, dict) and "store_artifacts" in s]
        paths = [s["store_artifacts"].get("path", "") for s in artifact_steps]
        assert "coverage.xml" in paths

    def test_test_job_stores_test_results(self, ci_config: dict) -> None:
        steps = ci_config["jobs"]["test"]["steps"]
        result_steps = [s for s in steps if isinstance(s, dict) and "store_test_results" in s]
        assert len(result_steps) > 0

    def test_security_scan_job_runs_pip_audit(self, ci_config: dict) -> None:
        steps = ci_config["jobs"]["security_scan"]["steps"]
        run_cmds = [
            s["run"].get("command", "")
            for s in steps
            if isinstance(s, dict) and "run" in s and isinstance(s["run"], dict)
        ]
        all_cmds = " ".join(run_cmds)
        assert "pip-audit" in all_cmds

    def test_security_scan_always_stores_artifact(self, ci_config: dict) -> None:
        steps = ci_config["jobs"]["security_scan"]["steps"]
        artifact_steps = [
            s["store_artifacts"]
            for s in steps
            if isinstance(s, dict) and "store_artifacts" in s
        ]
        always_steps = [a for a in artifact_steps if a.get("when") == "always"]
        assert len(always_steps) > 0, (
            "security_scan artifacts must use when: always so reports are preserved on failure"
        )

    def test_smoke_test_validates_key_modules(self, ci_config: dict) -> None:
        steps = ci_config["jobs"]["smoke_test"]["steps"]
        run_cmds = [
            s["run"].get("command", "")
            for s in steps
            if isinstance(s, dict) and "run" in s and isinstance(s["run"], dict)
        ]
        all_cmds = " ".join(run_cmds)
        for module in ("config", "database", "app_init"):
            assert f"import {module}" in all_cmds, (
                f"smoke_test does not validate import of '{module}'"
            )
        assert "utils" in all_cmds, (
            "smoke_test does not validate utils imports"
        )

    def test_all_jobs_use_small_resource_class(self, ci_config: dict) -> None:
        for job_name in EXPECTED_JOBS:
            job = ci_config["jobs"][job_name]
            assert job.get("resource_class") == "small", (
                f"Job '{job_name}' should use resource_class: small"
            )


# ---------------------------------------------------------------------------
# Workflows
# ---------------------------------------------------------------------------


class TestWorkflows:
    EXPECTED_WORKFLOWS = {"ci", "main_branch"}

    def test_workflows_section_present(self, ci_config: dict) -> None:
        assert "workflows" in ci_config

    @pytest.mark.parametrize("workflow", list(EXPECTED_WORKFLOWS))
    def test_workflow_defined(self, ci_config: dict, workflow: str) -> None:
        assert workflow in ci_config["workflows"], f"Workflow '{workflow}' not found"

    def test_ci_workflow_includes_all_jobs(self, ci_config: dict) -> None:
        jobs_in_ci = {
            list(j.keys())[0] if isinstance(j, dict) else j
            for j in ci_config["workflows"]["ci"]["jobs"]
        }
        for expected in EXPECTED_JOBS:
            assert expected in jobs_in_ci, f"Job '{expected}' missing from ci workflow"

    def test_main_branch_workflow_includes_all_jobs(self, ci_config: dict) -> None:
        jobs_in_main = {
            list(j.keys())[0] if isinstance(j, dict) else j
            for j in ci_config["workflows"]["main_branch"]["jobs"]
        }
        for expected in EXPECTED_JOBS:
            assert expected in jobs_in_main, (
                f"Job '{expected}' missing from main_branch workflow"
            )

    def test_ci_workflow_test_requires_lint(self, ci_config: dict) -> None:
        """test job in ci workflow must require lint to pass first."""
        jobs = ci_config["workflows"]["ci"]["jobs"]
        test_entry = next(
            (j for j in jobs if isinstance(j, dict) and "test" in j), None
        )
        assert test_entry is not None
        requires = test_entry["test"].get("requires", [])
        assert "lint" in requires

    def test_ci_workflow_smoke_test_requires_lint(self, ci_config: dict) -> None:
        jobs = ci_config["workflows"]["ci"]["jobs"]
        smoke_entry = next(
            (j for j in jobs if isinstance(j, dict) and "smoke_test" in j), None
        )
        assert smoke_entry is not None
        requires = smoke_entry["smoke_test"].get("requires", [])
        assert "lint" in requires

    def test_main_branch_workflow_test_requires_lint(self, ci_config: dict) -> None:
        jobs = ci_config["workflows"]["main_branch"]["jobs"]
        test_entry = next(
            (j for j in jobs if isinstance(j, dict) and "test" in j), None
        )
        assert test_entry is not None
        requires = test_entry["test"].get("requires", [])
        assert "lint" in requires

    def test_main_branch_workflow_filters_only_main(self, ci_config: dict) -> None:
        """Every job in main_branch workflow must filter to branch: main only."""
        jobs = ci_config["workflows"]["main_branch"]["jobs"]
        for entry in jobs:
            if isinstance(entry, dict):
                job_name, job_cfg = next(iter(entry.items()))
                if isinstance(job_cfg, dict) and "filters" in job_cfg:
                    branches = job_cfg["filters"].get("branches", {})
                    only = branches.get("only")
                    if only is not None:
                        assert only == "main", (
                            f"Job '{job_name}' in main_branch filters to '{only}', expected 'main'"
                        )

    def test_main_branch_workflow_lint_only_main(self, ci_config: dict) -> None:
        jobs = ci_config["workflows"]["main_branch"]["jobs"]
        lint_entry = next(
            (j for j in jobs if isinstance(j, dict) and "lint" in j), None
        )
        assert lint_entry is not None
        filters = lint_entry["lint"].get("filters", {})
        assert filters.get("branches", {}).get("only") == "main"

    def test_ci_workflow_independent_jobs_have_no_lint_dependency(
        self, ci_config: dict
    ) -> None:
        """lint, type_check, security_scan should run independently in ci (no requires)."""
        independent_jobs = {"lint", "type_check", "security_scan"}
        jobs = ci_config["workflows"]["ci"]["jobs"]
        for entry in jobs:
            if isinstance(entry, dict):
                job_name, job_cfg = next(iter(entry.items()))
                if job_name in independent_jobs:
                    requires = job_cfg.get("requires", []) if isinstance(job_cfg, dict) else []
                    assert "lint" not in requires, (
                        f"Job '{job_name}' should not require lint in ci workflow"
                    )


# ---------------------------------------------------------------------------
# Regression / boundary tests
# ---------------------------------------------------------------------------


class TestCiConfigRegression:
    def test_duplicate_command_key_last_value_wins(self) -> None:
        """YAML silently discards duplicate mapping keys, keeping only the last.
        The install_deps run step has two 'command:' keys; ensure the effective
        command (last one) includes '--frozen'.
        """
        raw = CIRCLECI_CONFIG_PATH.read_text(encoding="utf-8")
        config = yaml.safe_load(raw)
        cmd = config["commands"]["install_deps"]
        run_steps = [
            s["run"] for s in cmd["steps"] if isinstance(s, dict) and "run" in s
        ]
        effective_commands = [
            step.get("command", "")
            for step in run_steps
            if isinstance(step, dict)
        ]
        # The first (overridden) command should NOT be present; only the last survives
        full = " ".join(effective_commands)
        assert "UV_SKIP_WHEEL_FILENAME_CHECK=1 uv sync --extra dev" not in full, (
            "The duplicate (first) command key should have been overridden by YAML parser"
        )
        assert "uv sync --extra dev --frozen" in full

    def test_working_directory_is_project(self, ci_config: dict) -> None:
        """Verify defaults anchor sets working_directory to ~/project."""
        # Defaults are merged via YAML anchors; check a representative job
        for job_name in EXPECTED_JOBS:
            job = ci_config["jobs"][job_name]
            assert job.get("working_directory") == "~/project", (
                f"Job '{job_name}' working_directory should be '~/project'"
            )

    def test_no_unexpected_top_level_keys(self, ci_config: dict) -> None:
        allowed_top_level = {
            "version",
            "orbs",
            "defaults",
            "python_image",
            "commands",
            "jobs",
            "workflows",
        }
        for key in ci_config:
            assert key in allowed_top_level, f"Unexpected top-level key: '{key}'"

    def test_cache_key_prefix_is_versioned(self, ci_config: dict) -> None:
        """Cache keys should start with a version prefix (e.g. v1-) to allow easy invalidation."""
        restore_steps = ci_config["commands"]["restore_dep_cache"]["steps"]
        restore_step = next(
            s for s in restore_steps if isinstance(s, dict) and "restore_cache" in s
        )
        for key in restore_step["restore_cache"]["keys"]:
            assert re.match(r"v\d+-", key), (
                f"Cache key '{key}' should start with a version prefix like 'v1-'"
            )

    def test_smoke_test_imports_utils_submodules(self, ci_config: dict) -> None:
        """Smoke test should verify utils submodule imports."""
        steps = ci_config["jobs"]["smoke_test"]["steps"]
        run_cmds = [
            s["run"].get("command", "")
            for s in steps
            if isinstance(s, dict) and "run" in s and isinstance(s["run"], dict)
        ]
        all_cmds = " ".join(run_cmds)
        assert "utils" in all_cmds, "smoke_test should test utils imports"
