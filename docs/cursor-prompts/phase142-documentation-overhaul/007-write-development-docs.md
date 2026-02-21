# Task 7: Write Development Documentation

## Context

No developer onboarding guide exists. The frontend README is generic Vite boilerplate. Testing docs are a single-page coverage table. This task creates 4 development docs.

## Actions

### File 1: `docs/development/getting-started.md`

```yaml
---
last-verified: 2026-02-17
sources:
  - compose/docker-compose.yml
  - compose/.env.example
  - README.md
phases: [142]
---
```

**Content:**

Walk a new developer from zero to running the full platform locally.

```markdown
# Getting Started
> Clone → configure → run → verify.

## Prerequisites
- Docker + Docker Compose v2
- Node.js 18+ and npm (for frontend development)
- Python 3.10+ (for running tests locally)
- Git

## Clone & Configure
git clone, copy .env.example → .env, explain key vars to customize.

## Start the Platform
docker compose up -d --build (from compose/ directory)

## Verify Everything is Running
- docker compose ps (all services healthy)
- Open https://localhost (accept self-signed cert)
- Login as customer1 / test123
- Login as operator1 / test123
- Check Keycloak admin at https://localhost/admin (admin / admin_dev)
- Check Grafana at http://localhost:3001

## Start the Device Simulator
docker compose --profile simulator up -d

## Frontend Development
cd frontend && npm install && npm run dev
(Vite dev server on http://localhost:5173, proxied through Caddy)

## Running Tests Locally
pip install -r requirements-test.txt (or use virtualenv)
pytest tests/unit/ -m unit -q

## Project Layout
Brief description of top-level directories (link to architecture docs for detail).

## Common Tasks
- Rebuild after backend change: docker compose build ui && docker compose up -d ui
- Rebuild after frontend change: cd frontend && npm run build
- Apply database migrations: python db/migrate.py
- Add a new Python package: update Dockerfile COPY line

## See Also
```

### File 2: `docs/development/testing.md`

```yaml
---
last-verified: 2026-02-17
sources:
  - tests/conftest.py
  - tests/coverage_requirements.md
  - pytest.ini
phases: [9, 40, 100, 140, 141, 142]
---
```

**Content:**

Merge and expand from `tests/coverage_requirements.md` and README testing section.

```markdown
# Testing
> Test strategy, running tests, and coverage requirements.

## Test Structure
- tests/unit/ — Unit tests (pytest, FakeConn/FakePool pattern for DB mocks)
- tests/integration/ — Integration tests (require running PostgreSQL)
- tests/e2e/ — End-to-end browser tests

## Running Tests
### Unit Tests
pytest tests/unit/ -m unit -q

### With Coverage
pytest -o addopts='' tests/unit/ -m unit --cov=services --cov-report=term-missing -q

### Frontend Type Check
cd frontend && npx tsc --noEmit

### Frontend Build
cd frontend && npm run build

## Coverage Requirements
Overall: 70% minimum
Critical paths: 90% minimum

### Critical Path Modules (90%+)
- services/ui_iot/middleware/auth.py
- services/ui_iot/middleware/tenant.py
- services/ui_iot/db/pool.py
- services/ui_iot/utils/url_validator.py

### Exemptions
- */migrations/*
- */tests/*
- */__pycache__/*

## Test Configuration
### conftest.py
Explain what conftest.py does:
- Sets default env vars (PG_PASS, KEYCLOAK_ADMIN_PASSWORD, DATABASE_URL, ADMIN_KEY)
- Adds service paths to sys.path
- Imports the Flask/FastAPI app
- Provides fixtures: db_pool, db_connection, clean_db, client, auth tokens

### pytest markers
- @pytest.mark.unit — fast, no external deps
- @pytest.mark.asyncio — async test functions

## Writing New Tests
- Pattern: FakeConn / FakePool for DB mocking
- Auth fixtures: customer_a_token, operator_token, etc.
- Always use @pytest.mark.unit marker

## CI Enforcement
- CI fails if coverage drops below 70%
- PRs must not decrease coverage
- New code must have tests

## See Also
```

### File 3: `docs/development/frontend.md`

```yaml
---
last-verified: 2026-02-17
sources:
  - frontend/package.json
  - frontend/vite.config.ts
  - frontend/src/app/
  - frontend/src/components/
  - frontend/src/features/
  - frontend/src/hooks/
  - frontend/src/services/
  - frontend/src/stores/
phases: [17, 18, 19, 20, 21, 22, 119, 124, 135, 136, 142]
---
```

**Content:**

Replace the generic Vite boilerplate in `frontend/README.md` with project-specific docs.

```markdown
# Frontend
> React + TypeScript + Vite application architecture and conventions.

## Technology Stack
- React 18 + TypeScript
- Vite (build + dev server)
- TailwindCSS + shadcn/ui component library
- ECharts (gauges, heatmaps, area charts) + uPlot (time-series)
- TanStack Query (server state)
- Zustand (client state — WebSocket live data)
- React Router v6
- keycloak-js (OIDC/PKCE authentication)
- react-hook-form + zod (form validation — Phase 136)

## Directory Structure
frontend/src/
├── app/          — Router, providers, layout
├── components/   — Shared components, shadcn/ui, DataTable
├── features/     — Feature modules (one dir per feature)
├── hooks/        — React Query hooks, WebSocket hooks
├── services/     — API client, auth service, per-domain API modules
├── stores/       — Zustand stores (live telemetry, alerts)
└── lib/          — Chart wrappers, NOC theme tokens

## Feature Modules
List all feature modules from frontend/src/features/ with their pages.
(Read the directory to build this list — match against README.md's "Frontend Feature Modules" table but verify against actual filesystem.)

## Component Patterns
### DataTable
Standard table component (Phase 135) — all list views use this.

### Form Validation
react-hook-form + zod pattern (Phase 136) — all forms use this.

### shadcn/ui
Component library — buttons, cards, dialogs, etc.

## State Management
### Server State (TanStack Query)
API data fetching, caching, invalidation.

### Client State (Zustand)
WebSocket-driven live data (alerts, telemetry).

## Development
npm install
npm run dev (Vite dev server on :5173)
npm run build (production build to dist/)
npx tsc --noEmit (type checking)

## See Also
```

### File 4: `docs/development/conventions.md`

```yaml
---
last-verified: 2026-02-17
sources:
  - .github/pull_request_template.md
  - .github/BRANCH_PROTECTION.md
phases: [142]
---
```

**Content:**

```markdown
# Conventions
> Code style, commit format, and PR process.

## Commit Messages
Format: `type(scope): description`
Types: feat, fix, refactor, test, docs, chore
Example: `feat(phase141): fix 30 broken test files — env var cleanup`

## Branch Strategy
- main: production-ready
- Feature branches: phases-NNN-description or phaseNNN-description

## Pull Requests
- Use the PR template (.github/pull_request_template.md)
- PRs must pass CI (tests + type check + coverage gate)
- Branch protection rules (see .github/BRANCH_PROTECTION.md)

## Python Style
- Python 3.10+ with type hints
- asyncio/await for all I/O
- FastAPI for HTTP services, aiohttp for non-FastAPI services
- asyncpg for PostgreSQL

## Frontend Style
- TypeScript strict mode
- Functional components with hooks
- TanStack Query for data fetching
- shadcn/ui component library
- TailwindCSS for styling

## File Organization
- Backend: services/<service_name>/
- Frontend: frontend/src/features/<feature>/
- Tests: tests/unit/, tests/integration/, tests/e2e/
- Migrations: db/migrations/NNN_description.sql

## See Also
```

## Accuracy Rules

- Read `frontend/src/features/` directory listing to build the actual feature module table — do not copy from README without verifying.
- Read `compose/.env.example` for the getting-started guide.
- Read `tests/conftest.py` to accurately describe what it does and which env vars it sets.
