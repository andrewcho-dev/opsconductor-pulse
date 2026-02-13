import { format, formatDistanceToNow, parseISO, isValid } from "date-fns";

export function formatTimestamp(
  timestamp: string | Date | null | undefined,
  formatString: string = "MMM d, yyyy HH:mm"
): string {
  if (!timestamp) return "N/A";

  const date = typeof timestamp === "string" ? parseISO(timestamp) : timestamp;
  if (!isValid(date)) return "Invalid date";

  return format(date, formatString);
}

export function formatRelativeTime(
  timestamp: string | Date | null | undefined,
  options?: { addSuffix?: boolean }
): string {
  if (!timestamp) return "N/A";

  const date = typeof timestamp === "string" ? parseISO(timestamp) : timestamp;
  if (!isValid(date)) return "Invalid date";

  return formatDistanceToNow(date, { addSuffix: options?.addSuffix ?? true });
}

export function formatNumber(value: number, decimals: number = 2): string {
  return value.toLocaleString(undefined, {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  });
}
