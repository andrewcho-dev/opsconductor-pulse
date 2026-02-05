import { useParams } from "react-router-dom";

export default function DeviceDetailPage() {
  const { deviceId } = useParams<{ deviceId: string }>();

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Device: {deviceId}</h1>
      <p className="text-muted-foreground">Device detail with charts will be implemented in Phase 20.</p>
    </div>
  );
}
