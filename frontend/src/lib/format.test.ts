import { describe, it, expect } from "vitest";

import { formatTimestamp } from "./format";

describe("formatTimestamp", () => {
  it("formats ISO timestamp to readable date", () => {
    const result = formatTimestamp("2026-02-11T10:30:00Z");
    expect(result).toMatch(/2026/);
  });

  it("handles null input", () => {
    expect(formatTimestamp(null)).toBe("N/A");
  });

  it("handles undefined input", () => {
    expect(formatTimestamp(undefined)).toBe("N/A");
  });

  it("handles empty string", () => {
    expect(formatTimestamp("")).toBe("N/A");
  });

  it("handles invalid date string", () => {
    expect(formatTimestamp("not-a-date")).toBe("Invalid date");
  });
});
