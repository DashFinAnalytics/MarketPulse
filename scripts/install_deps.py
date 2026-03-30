"""Install runtime dependencies declared in pyproject.toml.

This script avoids introducing a second dependency source of truth too early.
It reads `[project].dependencies` from `pyproject.toml` and installs them with
pip into the currently active Python environment.

By default the script refuses to run outside a virtual environment to prevent
accidental pollution of a system or global interpreter.  Set the environment
variable ``INSTALL_DEPS_FORCE=1`` or pass ``--force`` on the command line to
bypass this guard.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover
    raise SystemExit("Python 3.11+ is required to read pyproject.toml with tomllib.")


def _in_virtualenv() -> bool:
    """Return True when running inside a virtual environment."""
    return sys.prefix != sys.base_prefix


def main() -> int:
    force = "--force" in sys.argv[1:] or os.environ.get("INSTALL_DEPS_FORCE") == "1"

    if not _in_virtualenv() and not force:
        print(
            "ERROR: No active virtual environment detected.\n"
            "Activate a venv first (e.g. `source .venv/bin/activate`) to avoid\n"
            "installing packages into the system Python interpreter.\n"
            "\n"
            "To bypass this check, run with --force or set INSTALL_DEPS_FORCE=1.",
            file=sys.stderr,
        )
        return 1

    project_root = Path(__file__).resolve().parents[1]
    pyproject_path = project_root / "pyproject.toml"
    if not pyproject_path.exists():
        print("pyproject.toml not found", file=sys.stderr)
        return 1

    with pyproject_path.open("rb") as handle:
        data = tomllib.load(handle)

    deps = data.get("project", {}).get("dependencies", [])
    if not deps:
        print("No dependencies found in pyproject.toml")
        return 0

    cmd = [sys.executable, "-m", "pip", "install", "--upgrade", "pip"]
    print("Running:", " ".join(cmd))
    subprocess.check_call(cmd)

    install_cmd = [sys.executable, "-m", "pip", "install", *deps]
    print("Running:", " ".join(install_cmd))
    subprocess.check_call(install_cmd)

    print("Dependency installation complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
