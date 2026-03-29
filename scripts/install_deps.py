"""Install runtime dependencies declared in pyproject.toml.

This script avoids introducing a second dependency source of truth too early.
It reads `[project].dependencies` from `pyproject.toml` and installs them with
pip into the currently active Python environment.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover
    raise SystemExit("Python 3.11+ is required to read pyproject.toml with tomllib.")


def main() -> int:
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
