import { describe, it, expect, vi, beforeEach } from "vitest";
import { apiGet, apiPost } from "./client";

describe("API Client", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("apiGet", () => {
    it("makes GET request with auth header", async () => {
      globalThis.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve({ data: "test" }),
      } as Response);

      const result = await apiGet("/test");

      expect(result).toEqual({ data: "test" });
      expect(fetch).toHaveBeenCalledWith(
        "/test",
        expect.objectContaining({
          headers: expect.objectContaining({ "Content-Type": "application/json" }),
        })
      );
    });

    it("throws on non-200 response", async () => {
      globalThis.fetch = vi.fn().mockResolvedValue({
        ok: false,
        status: 404,
        json: () => Promise.resolve({ detail: "Not found" }),
      } as Response);

      await expect(apiGet("/not-found")).rejects.toThrow();
    });
  });

  describe("apiPost", () => {
    it("sends JSON body", async () => {
      globalThis.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve({ id: 1 }),
      } as Response);

      await apiPost("/create", { name: "test" });

      expect(fetch).toHaveBeenCalledWith(
        expect.any(String),
        expect.objectContaining({
          method: "POST",
          body: JSON.stringify({ name: "test" }),
        })
      );
    });
  });
});
