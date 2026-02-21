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
