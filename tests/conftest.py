"""pytest configuration — ensures the project root is on sys.path."""

import sys
import os

# Add the project root to sys.path so that all project modules are importable
# when pytest is invoked from any working directory.
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)