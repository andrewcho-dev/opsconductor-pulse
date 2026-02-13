import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";

import { PageHeader } from "./PageHeader";

describe("PageHeader", () => {
  it("renders title", () => {
    render(<PageHeader title="Dashboard" />);
    expect(screen.getByText("Dashboard")).toBeInTheDocument();
  });

  it("renders description when provided", () => {
    render(<PageHeader title="Dashboard" description="Overview of your devices" />);
    expect(screen.getByText("Overview of your devices")).toBeInTheDocument();
  });

  it("renders action when provided", () => {
    render(<PageHeader title="Devices" action={<button>Add Device</button>} />);
    expect(screen.getByRole("button", { name: "Add Device" })).toBeInTheDocument();
  });

  it("renders breadcrumbs when provided", () => {
    render(
      <PageHeader
        title="Device Details"
        breadcrumbs={[
          { label: "Home", href: "/" },
          { label: "Devices", href: "/devices" },
        ]}
      />
    );
    expect(screen.getByText("Home")).toBeInTheDocument();
    expect(screen.getByText("Devices")).toBeInTheDocument();
  });
});
