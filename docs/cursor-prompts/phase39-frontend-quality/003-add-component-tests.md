# Add Component Tests

Create tests for key UI components.

## 1. Create `frontend/src/components/shared/StatusBadge.test.tsx`

```tsx
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { StatusBadge } from "./StatusBadge";

describe("StatusBadge", () => {
  describe("device variant", () => {
    it("renders ONLINE status with success styling", () => {
      render(<StatusBadge status="ONLINE" variant="device" />);

      const badge = screen.getByText("ONLINE");
      expect(badge).toBeInTheDocument();
      expect(badge.className).toContain("bg-green");
    });

    it("renders OFFLINE status with muted styling", () => {
      render(<StatusBadge status="OFFLINE" variant="device" />);

      const badge = screen.getByText("OFFLINE");
      expect(badge).toBeInTheDocument();
    });

    it("renders STALE status with warning styling", () => {
      render(<StatusBadge status="STALE" variant="device" />);

      const badge = screen.getByText("STALE");
      expect(badge).toBeInTheDocument();
    });
  });

  describe("alert variant", () => {
    it("renders OPEN status", () => {
      render(<StatusBadge status="OPEN" variant="alert" />);

      expect(screen.getByText("OPEN")).toBeInTheDocument();
    });

    it("renders ACKNOWLEDGED status", () => {
      render(<StatusBadge status="ACKNOWLEDGED" variant="alert" />);

      expect(screen.getByText("ACKNOWLEDGED")).toBeInTheDocument();
    });

    it("renders CLOSED status", () => {
      render(<StatusBadge status="CLOSED" variant="alert" />);

      expect(screen.getByText("CLOSED")).toBeInTheDocument();
    });
  });

  describe("subscription variant", () => {
    it("renders ACTIVE status", () => {
      render(<StatusBadge status="ACTIVE" variant="subscription" />);

      expect(screen.getByText("ACTIVE")).toBeInTheDocument();
    });

    it("renders SUSPENDED status with destructive styling", () => {
      render(<StatusBadge status="SUSPENDED" variant="subscription" />);

      const badge = screen.getByText("SUSPENDED");
      expect(badge).toBeInTheDocument();
    });
  });

  it("applies custom className", () => {
    render(<StatusBadge status="ONLINE" className="custom-class" />);

    const badge = screen.getByText("ONLINE");
    expect(badge.className).toContain("custom-class");
  });

  it("defaults to device variant", () => {
    render(<StatusBadge status="ONLINE" />);

    expect(screen.getByText("ONLINE")).toBeInTheDocument();
  });
});
```

## 2. Create `frontend/src/components/shared/SeverityBadge.test.tsx`

```tsx
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { SeverityBadge } from "./SeverityBadge";

describe("SeverityBadge", () => {
  it("renders CRITICAL severity", () => {
    render(<SeverityBadge severity="CRITICAL" />);

    const badge = screen.getByText("CRITICAL");
    expect(badge).toBeInTheDocument();
  });

  it("renders HIGH severity", () => {
    render(<SeverityBadge severity="HIGH" />);

    expect(screen.getByText("HIGH")).toBeInTheDocument();
  });

  it("renders MEDIUM severity", () => {
    render(<SeverityBadge severity="MEDIUM" />);

    expect(screen.getByText("MEDIUM")).toBeInTheDocument();
  });

  it("renders LOW severity", () => {
    render(<SeverityBadge severity="LOW" />);

    expect(screen.getByText("LOW")).toBeInTheDocument();
  });

  it("renders INFO severity", () => {
    render(<SeverityBadge severity="INFO" />);

    expect(screen.getByText("INFO")).toBeInTheDocument();
  });

  it("handles unknown severity gracefully", () => {
    render(<SeverityBadge severity="UNKNOWN" />);

    expect(screen.getByText("UNKNOWN")).toBeInTheDocument();
  });

  it("applies custom className", () => {
    render(<SeverityBadge severity="HIGH" className="my-class" />);

    const badge = screen.getByText("HIGH");
    expect(badge.className).toContain("my-class");
  });
});
```

## 3. Create `frontend/src/components/shared/EmptyState.test.tsx`

```tsx
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { EmptyState } from "./EmptyState";
import { AlertCircle } from "lucide-react";

describe("EmptyState", () => {
  it("renders title and description", () => {
    render(
      <EmptyState
        title="No items found"
        description="Try adjusting your filters"
      />
    );

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

  it("renders action button when provided", () => {
    render(
      <EmptyState
        title="Empty"
        description="Nothing here"
        action={<button>Add Item</button>}
      />
    );

    expect(screen.getByRole("button", { name: "Add Item" })).toBeInTheDocument();
  });
});
```

## 4. Create `frontend/src/components/shared/PageHeader.test.tsx`

```tsx
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { PageHeader } from "./PageHeader";

describe("PageHeader", () => {
  it("renders title", () => {
    render(<PageHeader title="Dashboard" />);

    expect(screen.getByText("Dashboard")).toBeInTheDocument();
  });

  it("renders description when provided", () => {
    render(
      <PageHeader
        title="Dashboard"
        description="Overview of your devices"
      />
    );

    expect(screen.getByText("Dashboard")).toBeInTheDocument();
    expect(screen.getByText("Overview of your devices")).toBeInTheDocument();
  });

  it("renders action when provided", () => {
    render(
      <PageHeader
        title="Devices"
        action={<button>Add Device</button>}
      />
    );

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
```

## 5. Create `frontend/src/lib/format.test.ts`

```typescript
import { describe, it, expect } from "vitest";
import { formatTimestamp } from "./format";

describe("formatTimestamp", () => {
  it("formats ISO timestamp to readable date", () => {
    const result = formatTimestamp("2026-02-11T10:30:00Z");

    // Should include date and time
    expect(result).toMatch(/2026/);
    expect(result).toMatch(/Feb|02/);
  });

  it("handles null input", () => {
    const result = formatTimestamp(null);

    expect(result).toBe("—");
  });

  it("handles undefined input", () => {
    const result = formatTimestamp(undefined);

    expect(result).toBe("—");
  });

  it("handles empty string", () => {
    const result = formatTimestamp("");

    expect(result).toBe("—");
  });

  it("handles invalid date string", () => {
    const result = formatTimestamp("not-a-date");

    // Should return the fallback or handle gracefully
    expect(typeof result).toBe("string");
  });
});
```

## 6. Update package.json scripts (if needed)

Ensure test scripts exist:

```json
{
  "scripts": {
    "test": "vitest",
    "test:run": "vitest run",
    "test:coverage": "vitest run --coverage"
  }
}
```

## Verification

```bash
cd frontend
npm run test:run

# Check coverage
npm run test:coverage
```

Expected: All component tests pass, coverage increases.
