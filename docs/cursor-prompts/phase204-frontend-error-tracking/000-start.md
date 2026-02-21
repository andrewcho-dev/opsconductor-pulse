# Phase 204 — Frontend Error Tracking

## Goal

Wire up a real error tracking service to the `logger` utility created in phase 202. Right now `logger.error()` is a no-op in production — frontend errors are completely invisible. This phase connects the logger to Sentry so production errors are captured and searchable.

## Current State (problem)

`frontend/src/lib/logger.ts` only logs to `console.*` in development mode. In production (`import.meta.env.PROD`) all calls are silently dropped. When a user hits an error in production, there is no record of it.

## Target State

- `logger.error()` and `logger.warn()` send events to Sentry in production.
- `logger.log()` and `logger.debug()` remain console-only (not sent to Sentry — too noisy).
- Sentry DSN is configured via `VITE_SENTRY_DSN` environment variable.
- If `VITE_SENTRY_DSN` is not set, the logger falls back to the current no-op behavior (don't crash the app over missing observability config).
- React error boundaries (`ErrorBoundary.tsx`, `WidgetErrorBoundary.tsx`) report caught errors to Sentry automatically.

## Execution Order

| Step | File | What | Depends On |
|------|------|------|------------|
| 1 | `001-install-sentry.md` | Add Sentry SDK dependency | — |
| 2 | `002-wire-logger-to-sentry.md` | Update logger.ts to send to Sentry | Step 1 |
| 3 | `003-error-boundary-sentry.md` | Connect error boundaries to Sentry | Step 2 |
| 4 | `004-update-documentation.md` | Update docs | Steps 1–3 |

## Verification

```bash
# Sentry SDK installed
grep '@sentry/react' frontend/package.json

# DSN env var documented
grep 'VITE_SENTRY_DSN' frontend/.env.example

# Logger sends to Sentry in prod
grep -n 'Sentry\|captureException\|captureMessage' frontend/src/lib/logger.ts
```

## Documentation Impact

- `docs/operations/monitoring.md` — Add frontend error tracking section
- `docs/development/getting-started.md` — Add VITE_SENTRY_DSN to env setup
