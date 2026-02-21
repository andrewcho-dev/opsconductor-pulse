Read `frontend/src/components/ErrorBoundary.tsx` and `frontend/src/components/shared/WidgetErrorBoundary.tsx`.

In each error boundary's `componentDidCatch` method (or equivalent), add a Sentry report. The Sentry React SDK provides a ready-made error boundary wrapper — use it:

For `ErrorBoundary.tsx`, wrap your existing boundary with `Sentry.withErrorBoundary` or call `Sentry.captureException` inside `componentDidCatch`:

```typescript
componentDidCatch(error: Error, info: React.ErrorInfo) {
  logger.error(error);
  // Sentry.captureException is called inside logger.error if error is an Error instance
  // But also add component context:
  if (import.meta.env.PROD && import.meta.env.VITE_SENTRY_DSN) {
    Sentry.withScope((scope) => {
      scope.setExtra("componentStack", info.componentStack);
      Sentry.captureException(error);
    });
  }
}
```

Apply the same pattern to `WidgetErrorBoundary.tsx`.

Do not change any UI rendering logic in the error boundaries — only add the Sentry reporting call inside `componentDidCatch`.
