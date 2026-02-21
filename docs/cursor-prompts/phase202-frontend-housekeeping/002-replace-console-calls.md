# Task 2: Replace `console.*` Calls with Structured Logger

## Context

Multiple frontend files use `console.error()`, `console.warn()`, and `console.log()` directly. In production, these clutter the browser console for customers and expose internal details. They should be routed through a logger that is silent in production and structured in development.

## Actions

1. Check if a logger utility already exists in `frontend/src/lib/` or `frontend/src/utils/`. If it does, read it.

2. If no logger exists, create `frontend/src/lib/logger.ts`:

```typescript
const isDev = import.meta.env.DEV;

export const logger = {
  log: (...args: unknown[]) => {
    if (isDev) console.log(...args);
  },
  warn: (...args: unknown[]) => {
    if (isDev) console.warn(...args);
  },
  error: (...args: unknown[]) => {
    // Always log errors — but in production, send to an error tracking service
    // For now: only log in dev. Replace with Sentry/Datadog integration later.
    if (isDev) console.error(...args);
  },
  debug: (...args: unknown[]) => {
    if (isDev) console.debug(...args);
  },
};
```

3. Search for `console.log`, `console.warn`, `console.error`, `console.debug` across all non-test TypeScript files:
   ```bash
   grep -rn 'console\.\(log\|warn\|error\|debug\)' frontend/src/ --include="*.tsx" --include="*.ts" | grep -v '.test.\|.spec.'
   ```

4. For each occurrence:
   - Replace with the equivalent `logger.*` call.
   - Add `import { logger } from "@/lib/logger"` (or the correct relative path) at the top of the file.

5. Do NOT replace `console.*` in test files — tests may use console assertions intentionally.

6. Do NOT replace `console.*` in Vite config files or build scripts.

## Verification

```bash
grep -rn 'console\.\(log\|warn\|error\)' frontend/src/ --include="*.tsx" --include="*.ts" | grep -v '.test.\|.spec.\|vite.config'
# Must return zero results (or only deliberate exceptions with a comment explaining why)
```
