/**
 * Extract a user-facing error message from common API error shapes.
 */
export function getErrorMessage(error: unknown): string {
  if (!error) return "Unknown error";

  if (typeof error === "object" && error !== null) {
    const err = error as Record<string, unknown>;

    if (err.body && typeof err.body === "object") {
      const body = err.body as Record<string, unknown>;
      if (typeof body.detail === "string") return body.detail;
    }

    if (err.response && typeof err.response === "object") {
      const response = err.response as Record<string, unknown>;
      if (response.data && typeof response.data === "object") {
        const data = response.data as Record<string, unknown>;
        if (typeof data.detail === "string") return data.detail;
      }
    }

    if (typeof err.message === "string") return err.message;
  }

  if (error instanceof Error) return error.message;
  return String(error);
}
