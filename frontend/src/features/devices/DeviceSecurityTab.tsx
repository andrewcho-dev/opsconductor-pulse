import { DeviceApiTokensPanel } from "./DeviceApiTokensPanel";
import { DeviceCertificatesTab } from "./DeviceCertificatesTab";

export function DeviceSecurityTab({ deviceId }: { deviceId: string }) {
  return (
    <div className="space-y-8 pt-2">
      <section>
        <h3 className="mb-3 text-sm font-semibold">API Tokens</h3>
        <DeviceApiTokensPanel deviceId={deviceId} />
      </section>
      <section>
        <h3 className="mb-3 text-sm font-semibold">mTLS Certificates</h3>
        <DeviceCertificatesTab deviceId={deviceId} />
      </section>
    </div>
  );
}

