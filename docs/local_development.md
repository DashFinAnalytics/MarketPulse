# Local Development

This repository currently favors a simple local workflow:
- **VS Code**
- **Python 3.11**
- **project-local `.venv`**
- **Windows first**, without requiring WSL unless a specific tool later demands it

## Why this setup

The repository still carries visible Replit-era scaffolding, so the safest next
step is a minimal, explicit local workflow rather than a more complex container
or WSL-first setup.

## 1. Install Python

Install Python **3.11** and make sure it is available on your system.

## 2. Clone and open the repo in VS Code

Open the repository root in VS Code.

The committed workspace files provide:
- interpreter guidance
- Streamlit launch configuration
- Python extension recommendations

## 3. Create a virtual environment

From the repository root:

### PowerShell

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### Command Prompt

```bat
py -3.11 -m venv .venv
.\.venv\Scripts\activate.bat
```

## 4. Install dependencies

With the virtual environment activated:

```powershell
python scripts/install_deps.py
```

This installs dependencies directly from `pyproject.toml` so we do not create a
second dependency source of truth too early.

## 5. Configure environment values

Copy `.env.example` to `.env` and fill in only what you need. This file is a
convenience for managing environment variables; the app ultimately reads values
from the environment provided by your shell or editor.

By default, `scripts/install_deps.py` does **not** install `python-dotenv`, so
the app will not automatically load `.env` unless you either:
- configure VS Code to use `.env` as an `envFile`, or
- export the variables from `.env` in your shell, or
- manually install `python-dotenv` in your virtualenv (e.g. `pip install python-dotenv`)
  and enable its use in your local config.
At minimum, the app should be able to run without database or OpenAI keys if
those services are left unconfigured.

## 6. Run the app

### From terminal

```powershell
streamlit run app.py --server.port 8501 --browser.gatherUsageStats false
```

### From VS Code

Use the launch target:
- **Streamlit: MarketPulse**

## 7. CI expectations

A minimal CI smoke check is intended to validate:
- dependency installation
- Python syntax compilation
- basic scaffold importability

CI is not yet a substitute for manual runtime checks.

## 8. WSL guidance

Do **not** make WSL the default for this project yet.

Use WSL only if:
- a package later requires Linux-specific build behavior
- Docker/container workflows become necessary
- Windows-native Python proves insufficient for a specific task

Until then, keeping the workflow to VS Code + local `.venv` reduces moving parts.
