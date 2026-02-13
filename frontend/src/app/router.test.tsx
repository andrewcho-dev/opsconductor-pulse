import { describe, it, expect } from "vitest";

import { router } from "./router";

describe("router", () => {
  it("uses /app basename", () => {
    expect(router.basename).toBe("/app");
  });

  it("contains customer and operator route groups", () => {
    const root = router.routes[0];
    const paths: string[] = [];
    const walk = (routes: Array<{ path?: string; children?: Array<{ path?: string; children?: unknown[] }> }>) => {
      for (const r of routes) {
        if (r.path) paths.push(r.path);
        if (r.children) walk(r.children as Array<{ path?: string; children?: unknown[] }>);
      }
    };
    walk([root]);

    expect(root.path).toBe("/");
    expect(paths).toContain("dashboard");
    expect(paths).toContain("devices");
    expect(paths).toContain("operator");
  });
});
