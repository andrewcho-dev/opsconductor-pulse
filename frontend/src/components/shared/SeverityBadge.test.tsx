import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";

import { SeverityBadge } from "./SeverityBadge";

describe("SeverityBadge", () => {
  it("renders critical style label for severity >= 5", () => {
    render(<SeverityBadge severity={5} />);
    expect(screen.getByText("5 Critical")).toBeInTheDocument();
  });

  it("renders warning style label for severity 3-4", () => {
    render(<SeverityBadge severity={3} />);
    expect(screen.getByText("3 Warning")).toBeInTheDocument();
  });

  it("renders info style label for severity <= 2", () => {
    render(<SeverityBadge severity={1} />);
    expect(screen.getByText("1 Info")).toBeInTheDocument();
  });

  it("applies custom className", () => {
    render(<SeverityBadge severity={4} className="my-class" />);
    expect(screen.getByText("4 Warning").className).toContain("my-class");
  });
});
