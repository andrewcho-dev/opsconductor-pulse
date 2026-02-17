---
last-verified: 2026-02-17
sources:
  - .github/pull_request_template.md
  - .github/BRANCH_PROTECTION.md
phases: [142]
---

# Conventions

> Code style, commit format, and PR process.

## Commit Messages

Format:

- `type(scope): description`

Types:

- `feat`, `fix`, `refactor`, `test`, `docs`, `chore`

Example:

- `test(phase141): fix broken test collection — env var + import cleanup`

## Branch Strategy

- `main`: production-ready
- feature branches: `phaseNNN-description` (preferred)

## Pull Requests

- Use `.github/pull_request_template.md`
- PRs must pass CI (tests, type checks, coverage gate)
- Follow branch protection guidance in `.github/BRANCH_PROTECTION.md`

## Python Style

- Python 3.10+ with type hints where practical
- Async I/O (`asyncio` / `asyncpg`) for service code
- FastAPI for HTTP services

## Frontend Style

- TypeScript strict mode
- Functional components with hooks
- TanStack Query for API data
- shadcn/ui + TailwindCSS for UI patterns

## File Organization

- Backend: `services/<service_name>/`
- Frontend: `frontend/src/features/<feature>/`
- Tests: `tests/unit/`, `tests/integration/`, `tests/e2e/`
- Migrations: `db/migrations/NNN_description.sql`

## See Also

- [Testing](testing.md)
- [Documentation index](../index.md)

