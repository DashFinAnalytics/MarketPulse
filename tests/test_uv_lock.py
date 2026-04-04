"""
Tests for uv.lock changes introduced in this PR.

Validates that urllib3 was correctly bumped from 2.5.0 to 2.6.3 in the lock file.
"""

import re
from pathlib import Path

import pytest

UV_LOCK_PATH = Path(__file__).parent.parent / "uv.lock"


@pytest.fixture(scope="module")
def uv_lock_content() -> str:
    """Return the full text content of uv.lock."""
    return UV_LOCK_PATH.read_text()


@pytest.fixture(scope="module")
def urllib3_block(uv_lock_content: str) -> str:
    """
    Extract the [[package]] block for urllib3 from uv.lock.
    uv.lock uses a TOML-like format; blocks are delimited by [[package]].
    """
    # Split by [[package]] to get individual package blocks
    blocks = re.split(r"\n\[\[package\]\]\n", uv_lock_content)
    for block in blocks:
        lines = block.strip().splitlines()
        for line in lines:
            if re.match(r'^name\s*=\s*"urllib3"', line.strip()):
                return block
    return ""


class TestUvLockExists:
    def test_lock_file_exists(self):
        assert UV_LOCK_PATH.exists(), "uv.lock must exist"

    def test_lock_file_is_non_empty(self, uv_lock_content):
        assert len(uv_lock_content) > 0, "uv.lock must not be empty"

    def test_lock_file_has_package_entries(self, uv_lock_content):
        assert "[[package]]" in uv_lock_content, (
            "uv.lock must contain [[package]] entries"
        )


class TestUrllib3Version:
    def test_urllib3_package_block_exists(self, urllib3_block):
        assert urllib3_block, "urllib3 package block must exist in uv.lock"

    def test_urllib3_version_is_2_6_3(self, urllib3_block):
        """The urllib3 version must be pinned to 2.6.3 (the bumped version)."""
        match = re.search(r'^version\s*=\s*"([^"]+)"', urllib3_block, re.MULTILINE)
        assert match, "urllib3 block must contain a version field"
        assert match.group(1) == "2.6.3", (
            f"urllib3 version must be 2.6.3, found: {match.group(1)!r}"
        )

    def test_urllib3_old_version_not_pinned(self, urllib3_block):
        """Regression: the old version 2.5.0 must no longer be the pinned version."""
        version_match = re.search(r'^version\s*=\s*"([^"]+)"', urllib3_block, re.MULTILINE)
        assert version_match, "urllib3 block must contain a version field"
        assert version_match.group(1) != "2.5.0", (
            "urllib3 version must not be 2.5.0 (old version); it was bumped to 2.6.3"
        )

    def test_urllib3_version_field_format(self, urllib3_block):
        """The version field must follow semantic versioning (MAJOR.MINOR.PATCH)."""
        match = re.search(r'^version\s*=\s*"(\d+\.\d+\.\d+)"', urllib3_block, re.MULTILINE)
        assert match, (
            "urllib3 version must follow MAJOR.MINOR.PATCH format"
        )

    def test_urllib3_source_is_pypi(self, urllib3_block):
        """urllib3 must be sourced from PyPI registry."""
        assert "pypi.org" in urllib3_block, (
            "urllib3 must be sourced from pypi.org"
        )


class TestLockFileIntegrity:
    def test_urllib3_appears_exactly_once_as_package(self, uv_lock_content):
        """urllib3 must appear exactly once as a named [[package]] entry."""
        # Count top-level package name declarations (not dependency references)
        name_pattern = re.compile(r'^\[\[package\]\]\s*\nname\s*=\s*"urllib3"', re.MULTILINE)
        matches = name_pattern.findall(uv_lock_content)
        assert len(matches) == 1, (
            f"urllib3 must appear exactly once as a [[package]] entry, found {len(matches)}"
        )

    def test_lock_file_starts_with_version_header(self, uv_lock_content):
        """uv.lock must start with a version header."""
        first_line = uv_lock_content.lstrip().splitlines()[0]
        assert first_line.startswith("version"), (
            f"uv.lock must start with a version header, got: {first_line!r}"
        )

    def test_urllib3_2_6_3_is_newer_than_2_5_0(self):
        """Sanity check: 2.6.3 > 2.5.0 per semantic versioning."""
        from packaging.version import Version  # type: ignore[import-untyped]

        assert Version("2.6.3") > Version("2.5.0"), (
            "2.6.3 must be a newer version than 2.5.0"
        )

    def test_urllib3_version_satisfies_pyproject_constraint(
        self, uv_lock_content
    ):
        """
        The locked urllib3 version (2.6.3) must satisfy the pyproject.toml
        constraint of >=2.6.3.
        """
        import tomllib

        pyproject_path = UV_LOCK_PATH.parent / "pyproject.toml"
        with open(pyproject_path, "rb") as f:
            pyproject = tomllib.load(f)

        runtime_deps = pyproject["project"]["dependencies"]
        urllib3_constraint = next(
            (d for d in runtime_deps if d.startswith("urllib3")), None
        )
        assert urllib3_constraint is not None, "urllib3 must be in pyproject.toml dependencies"

        # Extract version constraint (e.g. ">=2.6.3")
        constraint_match = re.search(r">=(\d+\.\d+\.\d+)", urllib3_constraint)
        assert constraint_match, f"Could not parse version constraint from: {urllib3_constraint!r}"
        min_version = constraint_match.group(1)

        # Find locked version
        urllib3_blocks = re.split(r"\n\[\[package\]\]\n", uv_lock_content)
        locked_version = None
        for block in urllib3_blocks:
            if re.search(r'^name\s*=\s*"urllib3"', block, re.MULTILINE):
                vm = re.search(r'^version\s*=\s*"([^"]+)"', block, re.MULTILINE)
                if vm:
                    locked_version = vm.group(1)
                    break

        assert locked_version is not None, "Could not find locked urllib3 version"

        try:
            from packaging.version import Version  # type: ignore[import-untyped]
            assert Version(locked_version) >= Version(min_version), (
                f"Locked urllib3 {locked_version} does not satisfy constraint >={min_version}"
            )
        except ImportError:
            # Fall back to simple tuple comparison if packaging is not available
            locked_parts = tuple(int(x) for x in locked_version.split("."))
            min_parts = tuple(int(x) for x in min_version.split("."))
            assert locked_parts >= min_parts, (
                f"Locked urllib3 {locked_version} does not satisfy constraint >={min_version}"
            )