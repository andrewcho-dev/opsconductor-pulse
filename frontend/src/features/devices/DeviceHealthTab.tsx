import { DeviceHealthPanel } from "./DeviceHealthPanel";
import { DeviceUptimePanel } from "./DeviceUptimePanel";

export function DeviceHealthTab({ deviceId }: { deviceId: string }) {
  return (
    <div className="space-y-4 pt-2">
      <section>
        <DeviceHealthPanel deviceId={deviceId} />
      </section>
      <section>
        <DeviceUptimePanel deviceId={deviceId} />
      </section>
    </div>
  );
}

