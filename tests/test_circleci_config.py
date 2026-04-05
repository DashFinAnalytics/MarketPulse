"""
Tests for .circleci/config.yml introduced in this PR.

Validates the structure and content of the CircleCI configuration:
- Required jobs exist (lint, type_check, test, security_scan, smoke_test)
- Required workflows exist (ci, main_branch)
- Commands are correctly defined
- Docker image and Python version are correct
- Workflow dependencies are correctly declared
"""

from pathlib import Path

import pytest
import yaml

CIRCLECI_CONFIG_PATH = Path(__file__).parent.parent / ".circleci" / "config.yml"


@pytest.fixture(scope="module")
def circleci_config() -> dict:
    """Parse and return .circleci/config.yml as a dict."""
    with open(CIRCLECI_CONFIG_PATH) as f:
        return yaml.safe_load(f)


@pytest.fixture(scope="module")
def circleci_raw() -> str:
    """Return raw text content of .circleci/config.yml."""
    return CIRCLECI_CONFIG_PATH.read_text()


class TestCircleCIConfigValidity:
    def test_config_file_exists(self):
        assert CIRCLECI_CONFIG_PATH.exists(), ".circleci/config.yml must exist"

    def test_parses_as_valid_yaml(self, circleci_config):
        assert isinstance(circleci_config, dict), "config.yml must parse as a YAML mapping"

    def test_circleci_version(self, circleci_config):
        assert circleci_config.get("version") == 2.1, (
            "CircleCI config version must be 2.1"
        )

    def test_has_orbs_section(self, circleci_config):
        assert "orbs" in circleci_config

    def test_python_orb_declared(self, circleci_config):
        orbs = circleci_config.get("orbs", {})
        assert "python" in orbs, "circleci/python orb must be declared"
        assert orbs["python"] == "circleci/python@2.1.1"

    def test_has_jobs_section(self, circleci_config):
        assert "jobs" in circleci_config, "config.yml must have a 'jobs' section"

    def test_has_workflows_section(self, circleci_config):
        assert "workflows" in circleci_config, "config.yml must have a 'workflows' section"

    def test_has_commands_section(self, circleci_config):
        assert "commands" in circleci_config, "config.yml must have a 'commands' section"


class TestDockerImage:
    def test_python_image_anchor_uses_correct_image(self, circleci_raw):
        """The docker image must be cimg/python:3.12."""
        assert "cimg/python:3.12" in circleci_raw, (
            "Docker image cimg/python:3.12 must be referenced in config"
        )


class TestCommands:
    EXPECTED_COMMANDS = ["install_uv", "restore_dep_cache", "save_dep_cache", "install_deps"]

    def test_all_expected_commands_exist(self, circleci_config):
        commands = circleci_config.get("commands", {})
        for cmd in self.EXPECTED_COMMANDS:
            assert cmd in commands, f"Command '{cmd}' must be defined in commands section"

    def test_install_uv_has_description(self, circleci_config):
        cmd = circleci_config["commands"]["install_uv"]
        assert "description" in cmd
        assert cmd["description"]

    def test_install_uv_has_steps(self, circleci_config):
        cmd = circleci_config["commands"]["install_uv"]
        assert "steps" in cmd
        assert len(cmd["steps"]) > 0

    def test_restore_dep_cache_uses_uv_lock_checksum(self, circleci_config):
        """Cache key must include uv.lock checksum for proper invalidation."""
        restore_steps = circleci_config["commands"]["restore_dep_cache"]["steps"]
        restore_step = next(
            (s for s in restore_steps if isinstance(s, dict) and "restore_cache" in s),
            None,
        )
        assert restore_step is not None, "restore_dep_cache must define a restore_cache step"
        keys = restore_step["restore_cache"].get("keys", [])
        assert any('checksum "uv.lock"' in key for key in keys), (
            "restore_dep_cache keys should include checksum of uv.lock"
        )

    def test_restore_dep_cache_uses_pyproject_checksum(self, circleci_raw):
        """Cache key must include pyproject.toml checksum for proper invalidation."""
        assert 'checksum "pyproject.toml"' in circleci_raw, (
            "Cache key should include checksum of pyproject.toml"
        )

    def test_save_dep_cache_saves_venv(self, circleci_raw):
        """The .venv directory must be saved to cache."""
        assert ".venv" in circleci_raw, "Cache must save .venv directory"

    def test_install_deps_uses_frozen_flag(self, circleci_raw):
        """uv sync must use --frozen to ensure reproducible installs."""
        assert "--frozen" in circleci_raw, (
            "uv sync must use --frozen flag for reproducible installs"
        )

    def test_install_deps_installs_dev_extra(self, circleci_raw):
        """Dependencies must be installed with the dev extra."""
        assert "--extra dev" in circleci_raw, (
            "uv sync must include --extra dev to install dev dependencies"
        )


class TestJobs:
    EXPECTED_JOBS = ["lint", "type_check", "test", "security_scan", "smoke_test"]

    def test_all_expected_jobs_exist(self, circleci_config):
        jobs = circleci_config.get("jobs", {})
        for job in self.EXPECTED_JOBS:
            assert job in jobs, f"Job '{job}' must be defined"

    def test_lint_job_runs_ruff(self, circleci_raw):
        assert "ruff check" in circleci_raw, "lint job must run ruff check"

    def test_lint_job_runs_ruff_format_check(self, circleci_raw):
        assert "ruff format --check" in circleci_raw, "lint job must run ruff format --check"

    def test_type_check_job_runs_mypy(self, circleci_config):
        steps = circleci_config["jobs"]["type_check"].get("steps", [])
        run_cmds = [
            step["run"].get("command", "")
            for step in steps
            if isinstance(step, dict) and "run" in step and isinstance(step["run"], dict)
        ]
        assert any("mypy" in cmd for cmd in run_cmds), "type_check job must run mypy"

    def test_test_job_runs_pytest(self, circleci_config):
        steps = circleci_config["jobs"]["test"].get("steps", [])
        run_cmds = [
            step["run"].get("command", "")
            for step in steps
            if isinstance(step, dict) and "run" in step and isinstance(step["run"], dict)
        ]
        assert any("pytest" in cmd for cmd in run_cmds), "test job must invoke pytest"

    def test_test_job_generates_coverage_xml(self, circleci_raw):
        assert "coverage.xml" in circleci_raw, (
            "test job must produce a coverage.xml report"
        )

    def test_test_job_uses_junit_xml(self, circleci_raw):
        assert "--junit-xml" in circleci_raw, (
            "test job must output JUnit XML results for CircleCI test reporting"
        )

    def test_security_scan_job_runs_pip_audit(self, circleci_raw):
        assert "pip-audit" in circleci_raw, "security_scan job must run pip-audit"

    def test_security_scan_produces_json_report(self, circleci_raw):
        assert "pip-audit-report.json" in circleci_raw, (
            "security_scan must produce pip-audit-report.json"
        )

    def test_smoke_test_validates_config_import(self, circleci_raw):
        assert "import config" in circleci_raw, (
            "smoke_test must validate 'import config'"
        )

    def test_smoke_test_validates_database_import(self, circleci_raw):
        assert "import database" in circleci_raw, (
            "smoke_test must validate 'import database'"
        )

    def test_smoke_test_validates_utils_import(self, circleci_raw):
        assert "from utils import" in circleci_raw, (
            "smoke_test must validate utils imports"
        )

    def test_smoke_test_validates_app_init_import(self, circleci_raw):
        assert "import app_init" in circleci_raw, (
            "smoke_test must validate 'import app_init'"
        )

    def test_test_job_stores_test_results(self, circleci_config):
        test_job = circleci_config["jobs"]["test"]
        steps = test_job.get("steps", [])
        step_types = []
        for step in steps:
            if isinstance(step, dict):
                step_types.extend(step.keys())
        assert "store_test_results" in step_types, (
            "test job must store test results with store_test_results"
        )

    def test_test_job_stores_coverage_artifact(self, circleci_config):
        test_job = circleci_config["jobs"]["test"]
        steps = test_job.get("steps", [])
        artifact_paths = []
        for step in steps:
            if isinstance(step, dict) and "store_artifacts" in step:
                artifact_paths.append(step["store_artifacts"].get("path", ""))
        assert any("coverage" in p for p in artifact_paths), (
            "test job must store coverage artifact"
        )


class TestWorkflows:
    EXPECTED_WORKFLOWS = ["ci", "main_branch"]

    def test_all_expected_workflows_exist(self, circleci_config):
        workflows = circleci_config.get("workflows", {})
        for wf in self.EXPECTED_WORKFLOWS:
            assert wf in workflows, f"Workflow '{wf}' must be defined"

    def test_ci_workflow_includes_lint(self, circleci_config):
        ci_jobs = circleci_config["workflows"]["ci"]["jobs"]
        job_names = _extract_job_names(ci_jobs)
        assert "lint" in job_names, "ci workflow must include lint job"

    def test_ci_workflow_includes_type_check(self, circleci_config):
        ci_jobs = circleci_config["workflows"]["ci"]["jobs"]
        job_names = _extract_job_names(ci_jobs)
        assert "type_check" in job_names, "ci workflow must include type_check job"

    def test_ci_workflow_includes_test(self, circleci_config):
        ci_jobs = circleci_config["workflows"]["ci"]["jobs"]
        job_names = _extract_job_names(ci_jobs)
        assert "test" in job_names, "ci workflow must include test job"

    def test_ci_workflow_includes_smoke_test(self, circleci_config):
        ci_jobs = circleci_config["workflows"]["ci"]["jobs"]
        job_names = _extract_job_names(ci_jobs)
        assert "smoke_test" in job_names, "ci workflow must include smoke_test job"

    def test_ci_workflow_includes_security_scan(self, circleci_config):
        ci_jobs = circleci_config["workflows"]["ci"]["jobs"]
        job_names = _extract_job_names(ci_jobs)
        assert "security_scan" in job_names, "ci workflow must include security_scan job"

    def test_ci_workflow_test_requires_lint(self, circleci_config):
        """The test job in ci workflow must require lint to pass first."""
        ci_jobs = circleci_config["workflows"]["ci"]["jobs"]
        test_entry = _find_job_entry(ci_jobs, "test")
        assert test_entry is not None
        requires = test_entry.get("requires", [])
        assert "lint" in requires, "test job must require lint in ci workflow"

    def test_ci_workflow_smoke_test_requires_lint(self, circleci_config):
        """The smoke_test job in ci workflow must require lint to pass first."""
        ci_jobs = circleci_config["workflows"]["ci"]["jobs"]
        smoke_entry = _find_job_entry(ci_jobs, "smoke_test")
        assert smoke_entry is not None
        requires = smoke_entry.get("requires", [])
        assert "lint" in requires, "smoke_test job must require lint in ci workflow"

    def test_main_branch_workflow_only_runs_on_main(self, circleci_config):
        """All jobs in main_branch workflow must have branch filter for 'main' only."""
        main_jobs = circleci_config["workflows"]["main_branch"]["jobs"]
        for job_entry in main_jobs:
            assert isinstance(job_entry, dict), "Each main_branch workflow job must be configured as a mapping"
            job_name = list(job_entry.keys())[0]
            job_config = job_entry[job_name]
            assert isinstance(job_config, dict), f"Job '{job_name}' must have a config mapping"
            filters = job_config.get("filters", {})
            branches = filters.get("branches", {})
            only = branches.get("only")
            assert only == "main", (
                f"Job '{job_name}' in main_branch workflow must filter to 'main' branch, "
                f"got: {only!r}"
            )

    def test_main_branch_workflow_includes_all_jobs(self, circleci_config):
        main_jobs = circleci_config["workflows"]["main_branch"]["jobs"]
        job_names = _extract_job_names(main_jobs)
        for expected in ["lint", "type_check", "test", "smoke_test", "security_scan"]:
            assert expected in job_names, (
                f"main_branch workflow must include {expected} job"
            )


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def _extract_job_names(jobs_list: list) -> list[str]:
    """Extract job names from a CircleCI workflow jobs list."""
    names = []
    for entry in jobs_list:
        if isinstance(entry, str):
            names.append(entry)
        elif isinstance(entry, dict):
            names.extend(entry.keys())
    return names


def _find_job_entry(jobs_list: list, job_name: str) -> dict | None:
    """Find and return a job's config dict from a workflow jobs list."""
    for entry in jobs_list:
        if isinstance(entry, dict) and job_name in entry:
            return entry[job_name]
    return None
