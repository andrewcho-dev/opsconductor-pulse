import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";

import { StatusBadge } from "./StatusBadge";

describe("StatusBadge", () => {
  describe("device variant", () => {
    it("renders ONLINE status", () => {
      render(<StatusBadge status="ONLINE" variant="device" />);
      expect(screen.getByText("ONLINE")).toBeInTheDocument();
    });

    it("renders OFFLINE status", () => {
      render(<StatusBadge status="OFFLINE" variant="device" />);
      expect(screen.getByText("OFFLINE")).toBeInTheDocument();
    });

    it("renders STALE status", () => {
      render(<StatusBadge status="STALE" variant="device" />);
      expect(screen.getByText("STALE")).toBeInTheDocument();
    });
  });

  describe("subscription variant", () => {
    it("renders ACTIVE status", () => {
      render(<StatusBadge status="ACTIVE" variant="subscription" />);
      expect(screen.getByText("ACTIVE")).toBeInTheDocument();
    });

    it("renders SUSPENDED status", () => {
      render(<StatusBadge status="SUSPENDED" variant="subscription" />);
      expect(screen.getByText("SUSPENDED")).toBeInTheDocument();
    });
  });

  it("applies custom className", () => {
    render(<StatusBadge status="ONLINE" className="custom-class" />);
    expect(screen.getByText("ONLINE").className).toContain("custom-class");
  });

  it("defaults to device variant", () => {
    render(<StatusBadge status="ONLINE" />);
    expect(screen.getByText("ONLINE")).toBeInTheDocument();
  });
});
