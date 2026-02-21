Install the Sentry React SDK.

```bash
cd /home/opsconductor/simcloud/frontend && npm install @sentry/react
```

Then read `frontend/src/main.tsx`. Initialize Sentry at the very top of the app — before React renders anything — so it captures errors from startup:

```typescript
import * as Sentry from "@sentry/react";

const sentryDsn = import.meta.env.VITE_SENTRY_DSN;

if (sentryDsn) {
  Sentry.init({
    dsn: sentryDsn,
    environment: import.meta.env.MODE,
    // Only send errors in production — not in dev
    enabled: import.meta.env.PROD,
    // Don't send PII
    sendDefaultPii: false,
    // Sample rate: send 100% of errors, 0% of performance traces for now
    tracesSampleRate: 0,
  });
}
```

Add `VITE_SENTRY_DSN` to `frontend/.env.example`:
```
# Sentry DSN for frontend error tracking (optional — errors are dropped if unset)
VITE_SENTRY_DSN=
```

Do not add a real DSN to any committed file.
