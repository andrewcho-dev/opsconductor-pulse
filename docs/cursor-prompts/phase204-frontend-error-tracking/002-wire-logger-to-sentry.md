Read `frontend/src/lib/logger.ts`. Update it so `error()` and `warn()` send to Sentry in production:

```typescript
import * as Sentry from "@sentry/react";

const isDev = import.meta.env.DEV;
const sentryEnabled = import.meta.env.PROD && !!import.meta.env.VITE_SENTRY_DSN;

export const logger = {
  log: (...args: unknown[]) => {
    if (isDev) console.log(...args);
  },
  debug: (...args: unknown[]) => {
    if (isDev) console.debug(...args);
  },
  warn: (...args: unknown[]) => {
    if (isDev) console.warn(...args);
    if (sentryEnabled) {
      Sentry.captureMessage(String(args[0]), { level: "warning", extra: { args } });
    }
  },
  error: (message: unknown, ...args: unknown[]) => {
    if (isDev) console.error(message, ...args);
    if (sentryEnabled) {
      if (message instanceof Error) {
        Sentry.captureException(message, { extra: { args } });
      } else {
        Sentry.captureMessage(String(message), { level: "error", extra: { args } });
      }
    }
  },
};
```

The key rules:
- `log` and `debug` are never sent to Sentry — too noisy
- `warn` sends as a Sentry message at warning level
- `error` with an Error object uses `captureException` (includes stack trace), string errors use `captureMessage`
- Everything is gated on `sentryEnabled` so a missing DSN is a silent no-op
