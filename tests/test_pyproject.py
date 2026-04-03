"""
Tests for pyproject.toml changes introduced in this PR:
- Added [project.optional-dependencies] dev section
- Added new runtime dependencies: urllib3, lxml-html-clean, pillow, protobuf, tornado
"""

import tomllib
from pathlib import Path

import pytest

PYPROJECT_PATH = Path(__file__).parent.parent / "pyproject.toml"


@pytest.fixture(scope="module")
def pyproject() -> dict:
    """Parse and return the pyproject.toml as a dict."""
    with open(PYPROJECT_PATH, "rb") as f:
        return tomllib.load(f)


class TestPyprojectValidity:
    def test_file_exists(self):
        assert PYPROJECT_PATH.exists(), "pyproject.toml must exist"

    def test_parses_as_valid_toml(self, pyproject):
        assert isinstance(pyproject, dict)

    def test_has_project_section(self, pyproject):
        assert "project" in pyproject

    def test_requires_python_311_or_greater(self, pyproject):
        requires = pyproject["project"]["requires-python"]
        assert requires == ">=3.11"


class TestNewRuntimeDependencies:
    """Tests for the 5 new runtime dependencies added in this PR."""

    @pytest.fixture(scope="class")
    def runtime_deps(self, pyproject) -> list[str]:
        return pyproject["project"]["dependencies"]

    def test_urllib3_present(self, runtime_deps):
        matching = [d for d in runtime_deps if d.startswith("urllib3")]
        assert matching, "urllib3 must be listed as a runtime dependency"

    def test_urllib3_minimum_version(self, runtime_deps):
        matching = [d for d in runtime_deps if d.startswith("urllib3")]
        assert any("2.6.3" in dep for dep in matching), (
            "urllib3 must require >= 2.6.3"
        )

    def test_lxml_html_clean_present(self, runtime_deps):
        matching = [d for d in runtime_deps if d.startswith("lxml-html-clean")]
        assert matching, "lxml-html-clean must be listed as a runtime dependency"

    def test_lxml_html_clean_minimum_version(self, runtime_deps):
        matching = [d for d in runtime_deps if d.startswith("lxml-html-clean")]
        assert any("0.4.4" in dep for dep in matching), (
            "lxml-html-clean must require >= 0.4.4"
        )

    def test_pillow_present(self, runtime_deps):
        matching = [d for d in runtime_deps if d.lower().startswith("pillow")]
        assert matching, "pillow must be listed as a runtime dependency"

    def test_pillow_minimum_version(self, runtime_deps):
        matching = [d for d in runtime_deps if d.lower().startswith("pillow")]
        assert any("11.3.0" in dep for dep in matching), (
            "pillow must require >= 11.3.0"
        )

    def test_protobuf_present(self, runtime_deps):
        matching = [d for d in runtime_deps if d.startswith("protobuf")]
        assert matching, "protobuf must be listed as a runtime dependency"

    def test_protobuf_minimum_version(self, runtime_deps):
        matching = [d for d in runtime_deps if d.startswith("protobuf")]
        assert any("6.33.5" in dep for dep in matching), (
            "protobuf must require >= 6.33.5"
        )

    def test_tornado_present(self, runtime_deps):
        matching = [d for d in runtime_deps if d.startswith("tornado")]
        assert matching, "tornado must be listed as a runtime dependency"

    def test_tornado_minimum_version(self, runtime_deps):
        matching = [d for d in runtime_deps if d.startswith("tornado")]
        assert any("6.5.5" in dep for dep in matching), (
            "tornado must require >= 6.5.5"
        )

    def test_all_new_deps_use_gte_constraint(self, runtime_deps):
        new_deps = ["urllib3", "lxml-html-clean", "pillow", "protobuf", "tornado"]
        for dep_name in new_deps:
            match = next((d for d in runtime_deps if d.lower().startswith(dep_name.lower())), None)
            assert match is not None, f"{dep_name} not found in dependencies"
            assert ">=" in match, (
                f"{dep_name} should use >= version constraint, got: {match!r}"
            )


class TestOptionalDevDependencies:
    """Tests for the new [project.optional-dependencies] dev section added in this PR."""

    @pytest.fixture(scope="class")
    def dev_extras(self, pyproject) -> list[str]:
        optional = pyproject.get("project", {}).get("optional-dependencies", {})
        return optional.get("dev", [])

    def test_optional_dependencies_section_exists(self, pyproject):
        assert "optional-dependencies" in pyproject["project"], (
            "[project.optional-dependencies] section must exist"
        )

    def test_dev_extra_exists(self, pyproject):
        dev = pyproject["project"]["optional-dependencies"].get("dev")
        assert dev is not None, "[project.optional-dependencies] must have a 'dev' key"
        assert isinstance(dev, list)
        assert len(dev) > 0

    def test_ruff_pinned_version(self, dev_extras):
        matching = [d for d in dev_extras if d.startswith("ruff")]
        assert matching, "ruff must be in dev extras"
        assert "ruff==0.6.9" in matching, f"Expected ruff==0.6.9, found: {matching}"

    def test_black_pinned_version(self, dev_extras):
        matching = [d for d in dev_extras if d.startswith("black")]
        assert matching, "black must be in dev extras"
        assert "black==24.10.0" in matching, f"Expected black==24.10.0, found: {matching}"

    def test_pytest_pinned_version(self, dev_extras):
        matching = [d for d in dev_extras if d.startswith("pytest==")]
        assert matching, "pytest must be in dev extras"
        assert "pytest==8.0.0" in matching, f"Expected pytest==8.0.0, found: {matching}"

    def test_pytest_cov_pinned_version(self, dev_extras):
        matching = [d for d in dev_extras if d.startswith("pytest-cov")]
        assert matching, "pytest-cov must be in dev extras"
        assert "pytest-cov==5.0.0" in matching, f"Expected pytest-cov==5.0.0, found: {matching}"

    def test_mypy_pinned_version(self, dev_extras):
        matching = [d for d in dev_extras if d.startswith("mypy")]
        assert matching, "mypy must be in dev extras"
        assert "mypy==1.11.0" in matching, f"Expected mypy==1.11.0, found: {matching}"

    def test_pip_audit_pinned_version(self, dev_extras):
        matching = [d for d in dev_extras if d.startswith("pip-audit")]
        assert matching, "pip-audit must be in dev extras"
        assert "pip-audit==2.8.0" in matching, f"Expected pip-audit==2.8.0, found: {matching}"

    def test_dev_extras_all_use_exact_pins(self, dev_extras):
        """All dev extras should use exact pins (==) for reproducibility."""
        for dep in dev_extras:
            assert "==" in dep, (
                f"Dev extra dependency should use exact pin (==), got: {dep!r}"
            )

    def test_dev_extras_count(self, dev_extras):
        """Exactly 6 dev extra dependencies should be declared."""
        assert len(dev_extras) == 6, (
            f"Expected 6 dev extras, found {len(dev_extras)}: {dev_extras}"
        )

    def test_no_pytest_plugin_duplicates(self, dev_extras):
        """pytest-cov should appear exactly once (no duplicates)."""
        cov_entries = [d for d in dev_extras if "pytest-cov" in d]
        assert len(cov_entries) == 1, f"pytest-cov should appear exactly once, found: {cov_entries}"