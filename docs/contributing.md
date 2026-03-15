# Contributing to MarketPulse

Thank you for your interest in contributing to MarketPulse. This document describes the contribution process, coding standards, and branching strategy.

---

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Branching Strategy](#branching-strategy)
- [Pull Request Process](#pull-request-process)
- [Commit Message Convention](#commit-message-convention)
- [Coding Standards](#coding-standards)
- [Documentation](#documentation)
- [Reporting Issues](#reporting-issues)

---

## Code of Conduct

All contributors are expected to act professionally and respectfully. Harassment or exclusionary behavior will not be tolerated.

---

## Getting Started

1. Fork the repository (external contributors) or clone directly (team members)
2. Set up your local environment: [docs/getting-started.md](getting-started.md)
3. Pick an issue from the backlog or create one describing your proposed change
4. Assign the issue to yourself before starting work

---

## Branching Strategy

MarketPulse uses a trunk-based development model with short-lived feature branches.

| Branch | Purpose |
|---|---|
| `main` | Stable, deployable code. Protected. Direct pushes blocked. |
| `feature/<short-description>` | Feature development |
| `fix/<short-description>` | Bug fixes |
| `docs/<short-description>` | Documentation-only changes |
| `chore/<short-description>` | Dependency updates, tooling, config |
| `copilot/<description>` | AI-assisted development branches |

### Branch naming examples

```
feature/market-dashboard-api
fix/portfolio-pnl-calculation
docs/architecture-data-flow
chore/upgrade-fastapi-0-111
```

---

## Pull Request Process

1. **Create a branch** from `main` using the naming convention above
2. **Make focused changes** — one PR per logical unit of work
3. **Write or update tests** for your changes
4. **Update documentation** if behavior changes
5. **Open a PR** against `main` with:
   - A clear title following the commit convention (see below)
   - A description of what changed and why
   - Reference to the related issue (`Closes #123`)
6. **Request review** from at least one team member
7. **Address review feedback** — resolve all comments before merging
8. **Squash and merge** — keep `main` history clean

### PR checklist

- [ ] Tests pass locally
- [ ] No new linting errors
- [ ] Documentation updated (if applicable)
- [ ] `.env.example` updated (if new environment variables were added)
- [ ] No secrets committed

---

## Commit Message Convention

MarketPulse follows the [Conventional Commits](https://www.conventionalcommits.org/) specification.

```
<type>(<scope>): <short summary>

[optional body]

[optional footer]
```

### Types

| Type | Description |
|---|---|
| `feat` | A new feature |
| `fix` | A bug fix |
| `docs` | Documentation only |
| `style` | Formatting, whitespace (no logic change) |
| `refactor` | Code restructuring without behavior change |
| `test` | Adding or updating tests |
| `chore` | Build tooling, dependencies, CI config |
| `perf` | Performance improvement |

### Examples

```
feat(market): add global market dashboard endpoint
fix(portfolio): correct unrealized P&L calculation for multi-currency holdings
docs(architecture): add data flow diagram
chore(deps): upgrade fastapi to 0.111.0
```

---

## Coding Standards

### Python (Backend)

- **Style:** Follow [PEP 8](https://peps.python.org/pep-0008/)
- **Formatter:** `black` (line length 88)
- **Linter:** `ruff`
- **Type hints:** Required for all public functions and methods
- **Docstrings:** Google-style docstrings for modules, classes, and public functions

### TypeScript / JavaScript (Frontend)

- **Language:** TypeScript (strict mode)
- **Style:** ESLint + Prettier (project config)
- **Naming:** camelCase for variables/functions; PascalCase for components/types
- **Components:** Functional components with hooks; no class components

### General

- No dead code or commented-out code in PRs
- Prefer explicit over implicit
- Handle errors gracefully — avoid bare `except` or unhandled promise rejections
- Validate all external inputs

---

## Documentation

- Update `docs/` files when making architectural or behavioral changes
- Use Markdown for all documentation
- Add an Architecture Decision Record (ADR) in `docs/adr/` for significant architectural choices (see [docs/adr/0000-adr-template.md](adr/0000-adr-template.md))

---

## Reporting Issues

When opening an issue, provide:

- A clear, concise title
- Steps to reproduce (for bugs)
- Expected vs actual behavior (for bugs)
- The feature request description and motivation (for enhancements)
- Relevant labels (`bug`, `enhancement`, `documentation`, etc.)
