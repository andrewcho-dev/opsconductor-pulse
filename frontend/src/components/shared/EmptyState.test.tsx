import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { AlertCircle } from "lucide-react";

import { EmptyState } from "./EmptyState";

describe("EmptyState", () => {
  it("renders title and description", () => {
    render(<EmptyState title="No items found" description="Try adjusting your filters" />);

    expect(screen.getByText("No items found")).toBeInTheDocument();
    expect(screen.getByText("Try adjusting your filters")).toBeInTheDocument();
  });

  it("renders custom icon", () => {
    render(
      <EmptyState
        title="Empty"
        description="Nothing here"
        icon={<AlertCircle data-testid="custom-icon" />}
      />
    );

    expect(screen.getByTestId("custom-icon")).toBeInTheDocument();
  });

  it("renders action when provided", () => {
    render(<EmptyState title="Empty" description="Nothing here" action={<button>Add Item</button>} />);
    expect(screen.getByRole("button", { name: "Add Item" })).toBeInTheDocument();
  });
});
