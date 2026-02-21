import type { ReactNode } from "react";
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
  icon: ReactNode;
  title: string;
  description: string;
  children: ReactNode;
}) {
  return (
    <section className="space-y-4">
      <div className="flex items-center gap-3 border-b border-border pb-3">
        <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-muted">{icon}</div>
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
