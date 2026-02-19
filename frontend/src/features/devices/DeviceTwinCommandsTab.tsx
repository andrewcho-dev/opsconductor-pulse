import { DeviceTwinPanel } from "./DeviceTwinPanel";
import { DeviceCommandPanel } from "./DeviceCommandPanel";

export function DeviceTwinCommandsTab({
  deviceId,
  templateId,
}: {
  deviceId: string;
  templateId?: number | null;
}) {
  // Template-aware command UX can be layered on top of DeviceCommandPanel later;
  // for Phase 171, consolidate twin + commands into a single tab.
  void templateId;

  return (
    <div className="space-y-4 pt-2">
      <section>
        <DeviceTwinPanel deviceId={deviceId} />
      </section>
      <section>
        <DeviceCommandPanel deviceId={deviceId} />
      </section>
    </div>
  );
}

