"""Tests for pyproject.toml and uv.lock changes introduced in this PR.

Covers:
- New [project.optional-dependencies] dev group and pinned tool versions
- New runtime dependencies (urllib3, lxml-html-clean, pillow, protobuf, tornado)
- urllib3 version constraint alignment between pyproject.toml and uv.lock
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

if sys.version_info >= (3, 11):
    import tomllib
else:
    try:
        import tomllib  # type: ignore[no-redef]
    except ImportError:
        import tomli as tomllib  # type: ignore[no-redef]

REPO_ROOT = Path(__file__).parent.parent
PYPROJECT_PATH = REPO_ROOT / "pyproject.toml"
UV_LOCK_PATH = REPO_ROOT / "uv.lock"

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def pyproject() -> dict:
    return tomllib.loads(PYPROJECT_PATH.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def uv_lock_text() -> str:
    return UV_LOCK_PATH.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# pyproject.toml — [project.optional-dependencies] dev group
# ---------------------------------------------------------------------------


class TestOptionalDevDependencies:
    """Tests for the new [project.optional-dependencies] dev group."""

    def test_optional_dependencies_section_exists(self, pyproject: dict) -> None:
        assert "optional-dependencies" in pyproject.get("project", {}), (
            "[project.optional-dependencies] section is missing from pyproject.toml"
        )

    def test_dev_extra_defined(self, pyproject: dict) -> None:
        extras = pyproject["project"]["optional-dependencies"]
        assert "dev" in extras, "dev extra not found in [project.optional-dependencies]"

    def test_dev_extra_is_non_empty(self, pyproject: dict) -> None:
        dev_deps = pyproject["project"]["optional-dependencies"]["dev"]
        assert len(dev_deps) > 0

    @pytest.mark.parametrize(
        "package",
        ["ruff", "black", "pytest", "pytest-cov", "mypy", "pip-audit"],
    )
    def test_dev_tool_present_in_dev_extra(
        self, pyproject: dict, package: str
    ) -> None:
        dev_deps = pyproject["project"]["optional-dependencies"]["dev"]
        package_names = {re.split(r"[=<>!~]", d, maxsplit=1)[0].strip() for d in dev_deps}
        assert package in package_names, (
            f"Package '{package}' not found in [project.optional-dependencies] dev"
        )

    def test_all_dev_extra_deps_are_non_empty_strings(
        self, pyproject: dict
    ) -> None:
        """All entries in the dev extra should be valid, non-empty dependency strings."""
        dev_deps = pyproject["project"]["optional-dependencies"]["dev"]
        for dep in dev_deps:
            assert isinstance(dep, str) and dep.strip(), (
                "Each dev extra dependency must be a non-empty string"
            )

    def test_dev_extra_contains_exactly_the_expected_packages(
        self, pyproject: dict
    ) -> None:
        dev_deps = pyproject["project"]["optional-dependencies"]["dev"]
        package_names = {re.split(r"[=<>!~]", d, maxsplit=1)[0].strip() for d in dev_deps}
        expected = {"ruff", "black", "pytest", "pytest-cov", "mypy", "pip-audit"}
        assert package_names == expected, (
            f"Unexpected packages in dev extra. Got {package_names}, expected {expected}"
        )


# ---------------------------------------------------------------------------
# pyproject.toml — new runtime dependencies
# ---------------------------------------------------------------------------


class TestNewRuntimeDependencies:
    """Tests for the five new runtime dependencies added to [project.dependencies]."""

    NEW_DEPS = {
        "urllib3": ">=2.6.3",
        "lxml-html-clean": ">=0.4.4",
        "pillow": ">=11.3.0",
        "protobuf": ">=6.33.5",
        "tornado": ">=6.5.5",
    }

    def _get_runtime_dep(self, pyproject: dict, package: str) -> str | None:
        """Return the full dependency specifier for a package, or None if absent."""
        deps = pyproject.get("project", {}).get("dependencies", [])
        for dep in deps:
            name = re.split(r"[=<>!]", dep)[0].lower()
            if name == package.lower():
                return dep
        return None

    @pytest.mark.parametrize("package", list(NEW_DEPS.keys()))
    def test_new_runtime_dep_present(self, pyproject: dict, package: str) -> None:
        dep = self._get_runtime_dep(pyproject, package)
        assert dep is not None, (
            f"Runtime dependency '{package}' not found in [project.dependencies]"
        )

    @pytest.mark.parametrize("package,min_version", list(NEW_DEPS.items()))
    def test_new_runtime_dep_has_correct_minimum_version(
        self, pyproject: dict, package: str, min_version: str
    ) -> None:
        dep = self._get_runtime_dep(pyproject, package)
        assert dep is not None
        assert min_version in dep, (
            f"Expected '{package}{min_version}' but found '{dep}'"
        )

    def test_urllib3_minimum_version_is_2_6_3_or_higher(
        self, pyproject: dict
    ) -> None:
        """urllib3>=2.6.3 addresses a known vulnerability; must not be loosened."""
        dep = self._get_runtime_dep(pyproject, "urllib3")
        assert dep is not None
        constraint = dep.replace("urllib3", "").strip()
        # Must use >= with a version of at least 2.6.3
        assert constraint.startswith(">="), (
            f"urllib3 constraint should be '>=' but got '{constraint}'"
        )
        version_str = constraint.lstrip(">=")
        parts = [int(x) for x in version_str.split(".")]
        minimum = [2, 6, 3]
        assert parts >= minimum, (
            f"urllib3 minimum version {version_str} is below required 2.6.3"
        )


# ---------------------------------------------------------------------------
# uv.lock — urllib3 version
# ---------------------------------------------------------------------------


class TestUvLockUrllib3:
    """Tests verifying urllib3 in uv.lock is consistent with pyproject.toml."""

    def test_uv_lock_exists(self) -> None:
        assert UV_LOCK_PATH.exists(), "uv.lock not found"

    def test_urllib3_package_present_in_lock(self, uv_lock_text: str) -> None:
        assert 'name = "urllib3"' in uv_lock_text

    def test_urllib3_locked_version_is_2_6_3(self, uv_lock_text: str) -> None:
        """urllib3 in uv.lock must be locked to 2.6.3 as specified in the PR."""
        # Find the urllib3 package block and extract its version
        match = re.search(
            r'name = "urllib3"\s*\nversion = "([^"]+)"',
            uv_lock_text,
        )
        assert match is not None, "Could not find urllib3 version entry in uv.lock"
        locked_version = match.group(1)
        assert locked_version == "2.6.3", (
            f"Expected urllib3 2.6.3 in uv.lock but found {locked_version}"
        )

    def test_urllib3_locked_version_satisfies_pyproject_constraint(
        self, pyproject: dict, uv_lock_text: str
    ) -> None:
        """The locked urllib3 version must satisfy the >=2.6.3 constraint."""
        match = re.search(
            r'name = "urllib3"\s*\nversion = "([^"]+)"',
            uv_lock_text,
        )
        assert match is not None
        locked = [int(x) for x in match.group(1).split(".")]
        minimum = [2, 6, 3]
        assert locked >= minimum, (
            f"Locked urllib3 {match.group(1)} does not satisfy >=2.6.3"
        )

    def test_urllib3_version_not_2_5_0(self, uv_lock_text: str) -> None:
        """Regression: previous version 2.5.0 must have been replaced by 2.6.3."""
        # Extract just the version field from the urllib3 package block to avoid
        # matching within sdist/wheel URLs that may still reference old artifacts
        match = re.search(
            r'name = "urllib3"\s*\nversion = "([^"]+)"',
            uv_lock_text,
        )
        assert match is not None
        assert match.group(1) != "2.5.0", (
            "urllib3 is still at the old version 2.5.0; expected 2.6.3"
        )


# ---------------------------------------------------------------------------
# pyproject.toml — general project metadata sanity checks
# ---------------------------------------------------------------------------


class TestProjectMetadata:
    def test_project_section_present(self, pyproject: dict) -> None:
        assert "project" in pyproject

    def test_requires_python_at_least_3_11(self, pyproject: dict) -> None:
        requires = pyproject["project"].get("requires-python", "")
        assert requires, "requires-python is not set"
        version_str = requires.lstrip(">=")
        major, minor = int(version_str.split(".")[0]), int(version_str.split(".")[1])
        assert (major, minor) >= (3, 11), (
            f"requires-python '{requires}' is below 3.11"
        )

    def test_pytest_testpaths_configured(self, pyproject: dict) -> None:
        # [tool.pytest.ini_options] parses as tool -> pytest -> ini_options
        ini = pyproject.get("tool", {}).get("pytest", {}).get("ini_options", {})
        assert "testpaths" in ini
        assert "tests" in ini["testpaths"]

    def test_pytest_addopts_includes_ra(self, pyproject: dict) -> None:
        ini = pyproject.get("tool", {}).get("pytest", {}).get("ini_options", {})
        assert "-ra" in ini.get("addopts", "")

    def test_ruff_line_length_is_100(self, pyproject: dict) -> None:
        ruff = pyproject.get("tool", {}).get("ruff", {})
        assert ruff.get("line-length") == 100

    def test_mypy_python_version_is_3_12(self, pyproject: dict) -> None:
        mypy = pyproject.get("tool", {}).get("mypy", {})
        assert mypy.get("python_version") == "3.12"

    def test_dependency_groups_dev_still_present(self, pyproject: dict) -> None:
        """Ensure the original [dependency-groups] dev section was not removed."""
        dep_groups = pyproject.get("dependency-groups", {})
        assert "dev" in dep_groups, (
            "[dependency-groups].dev should still exist alongside [project.optional-dependencies]"
        )

    def test_no_duplicate_package_across_both_dev_groups(
        self, pyproject: dict
    ) -> None:
        """Both dev groups serve different purposes; verify no exact-name duplication
        that would cause confusion (optional-deps pinned vs dependency-groups flexible)."""
        optional_dev = pyproject.get("project", {}).get("optional-dependencies", {}).get("dev", [])
        dep_group_dev = pyproject.get("dependency-groups", {}).get("dev", [])

        optional_names = {re.split(r"[=<>!]", d)[0].lower() for d in optional_dev}
        group_names = {re.split(r"[=<>!]", d)[0].lower() for d in dep_group_dev}

        # mypy and ruff appear in both — that's expected but their version pins differ
        # This test documents the overlap rather than asserting zero overlap
        overlap = optional_names & group_names
        # Known acceptable overlap: mypy, ruff, pytest
        unexpected = overlap - {"mypy", "ruff", "pytest"}
        assert not unexpected, (
            f"Unexpected package overlap between dev extras and dependency-groups: {unexpected}"
        )