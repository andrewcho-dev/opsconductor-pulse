# Task 1: Create DeviceManageTab Component

## File to Create

`frontend/src/features/devices/DeviceManageTab.tsx`

## Purpose

A new component that combines Transport, Twin/Commands, Security, and Plan into a single scrollable page with 4 visually distinct sections. Each section has an icon header with title and description, separated by a bottom border.

## Implementation

```tsx
import { CreditCard, Radio, Shield, Terminal } from "lucide-react";
import { DeviceTransportTab } from "./DeviceTransportTab";
import { DeviceTwinPanel } from "./DeviceTwinPanel";
import { DeviceCommandPanel } from "./DeviceCommandPanel";
import { DeviceApiTokensPanel } from "./DeviceApiTokensPanel";
import { DeviceCertificatesTab } from "./DeviceCertificatesTab";
import { DevicePlanPanel } from "./DevicePlanPanel";

function ManageSection({
  icon,
  title,
  description,
  children,
}: {
  icon: React.ReactNode;
  title: string;
  description: string;
  children: React.ReactNode;
}) {
  return (
    <section className="space-y-4">
      <div className="flex items-center gap-3 border-b border-border pb-3">
        <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-muted">
          {icon}
        </div>
        <div>
          <h3 className="text-sm font-semibold">{title}</h3>
          <p className="text-xs text-muted-foreground">{description}</p>
        </div>
      </div>
      {children}
    </section>
  );
}

interface DeviceManageTabProps {
  deviceId: string;
}

export function DeviceManageTab({ deviceId }: DeviceManageTabProps) {
  return (
    <div className="space-y-8 pt-2">
      <ManageSection
        icon={<Radio className="h-4 w-4 text-muted-foreground" />}
        title="Connectivity"
        description="Protocol configuration and physical connectivity"
      >
        <DeviceTransportTab deviceId={deviceId} />
      </ManageSection>

      <ManageSection
        icon={<Terminal className="h-4 w-4 text-muted-foreground" />}
        title="Control"
        description="Device twin state and remote commands"
      >
        <div className="space-y-4">
          <DeviceTwinPanel deviceId={deviceId} />
          <DeviceCommandPanel deviceId={deviceId} />
        </div>
      </ManageSection>

      <ManageSection
        icon={<Shield className="h-4 w-4 text-muted-foreground" />}
        title="Security"
        description="API tokens and X.509 certificates"
      >
        <div className="space-y-6">
          <div>
            <h4 className="mb-3 text-sm font-semibold">API Tokens</h4>
            <DeviceApiTokensPanel deviceId={deviceId} />
          </div>
          <div>
            <h4 className="mb-3 text-sm font-semibold">mTLS Certificates</h4>
            <DeviceCertificatesTab deviceId={deviceId} />
          </div>
        </div>
      </ManageSection>

      <ManageSection
        icon={<CreditCard className="h-4 w-4 text-muted-foreground" />}
        title="Subscription"
        description="Device plan, limits, and features"
      >
        <DevicePlanPanel deviceId={deviceId} />
      </ManageSection>
    </div>
  );
}
```

### Key design notes:

1. **`ManageSection` wrapper** — each section gets an icon in a muted rounded square, title, description, and a bottom border. This provides strong visual grouping.
2. **`space-y-8`** — generous vertical spacing between sections so they don't blend together.
3. **Sub-components are reused directly** — DeviceTransportTab, DeviceTwinPanel, DeviceCommandPanel, DeviceApiTokensPanel, DeviceCertificatesTab, and DevicePlanPanel are all imported and rendered as-is. They each take just `deviceId`.
4. **Security section keeps the sub-headings** ("API Tokens" and "mTLS Certificates") for internal structure within the section, matching the existing DeviceSecurityTab layout.
5. **NOT collapsible** — all sections are always visible. The section headers provide visual distinction without hiding content.

### Important:

- DeviceTransportTab already has its own header ("Transport" + description + "Add Transport" button). The ManageSection header is the grouping label. The component's internal header will render below it. This is intentional — the ManageSection is the category, the component's header is the specific tool. If you think the double-header looks redundant, you can remove the internal header from DeviceTransportTab by adding an `embedded` boolean prop, but this is **optional** and can be deferred.

## Verification

```bash
cd frontend && npx tsc --noEmit
```

- File compiles cleanly
- All imports resolve (DeviceTransportTab, DeviceTwinPanel, DeviceCommandPanel, DeviceApiTokensPanel, DeviceCertificatesTab, DevicePlanPanel)
