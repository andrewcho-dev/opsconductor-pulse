import { useState } from "react";
import { Link } from "react-router-dom";
import { Copy, Pencil, X } from "lucide-react";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { toast } from "sonner";
import type { Device } from "@/services/api/types";
import { formatTimestamp } from "@/lib/format";

interface DeviceInfoCardProps {
  device: Device | undefined;
  isLoading: boolean;
  tags: string[];
  onTagsChange: (tags: string[]) => void;
  notesValue: string;
  onNotesChange: (value: string) => void;
  onNotesBlur?: () => void;
  onEdit: () => void;
}

function Prop({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex gap-2 py-1 text-sm">
      <span className="w-20 shrink-0 text-muted-foreground">{label}</span>
      <span className="min-w-0 truncate">{children}</span>
    </div>
  );
}

function PropMono({ label, value }: { label: string; value?: string | null }) {
  if (!value) return null;
  return (
    <div className="flex gap-2 py-1 text-sm">
      <span className="w-20 shrink-0 text-muted-foreground">{label}</span>
      <span className="min-w-0 truncate font-mono">{value}</span>
    </div>
  );
}

function SectionCard({
  title,
  action,
  children,
}: {
  title: string;
  action?: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <div className="rounded-md border border-border p-3">
      <div className="mb-2 flex items-center justify-between">
        <h4 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">{title}</h4>
        {action}
      </div>
      {children}
    </div>
  );
}

export function DeviceInfoCard({
  device,
  isLoading,
  tags,
  onTagsChange,
  notesValue,
  onNotesChange,
  onNotesBlur,
  onEdit,
}: DeviceInfoCardProps) {
  const [tagInput, setTagInput] = useState("");

  if (isLoading) {
    return (
      <div className="col-span-full grid gap-3 sm:grid-cols-3">
        {[1, 2, 3].map((n) => (
          <div key={n} className="space-y-2 rounded-md border border-border p-3">
            <Skeleton className="h-3 w-20" />
            <Skeleton className="h-3 w-32" />
            <Skeleton className="h-3 w-28" />
          </div>
        ))}
      </div>
    );
  }

  if (!device) {
    return (
      <div className="col-span-full rounded-md border border-border p-4">
        <p className="text-sm text-muted-foreground">Device not found.</p>
      </div>
    );
  }

  const hasHardware =
    device.model || device.manufacturer || device.serial_number || device.mac_address || device.hw_revision || device.fw_version;
  const hasNetwork = device.imei || device.iccid;
  const hasLocation = device.latitude != null || device.address;

  return (
    <>
      <div className="col-span-full grid gap-3 sm:grid-cols-3">
        <SectionCard
          title="Identity"
          action={
            <Button
              type="button"
              onClick={onEdit}
              variant="ghost"
              size="sm"
              className="h-6 text-xs text-muted-foreground hover:text-foreground"
            >
              <Pencil className="mr-1 h-3 w-3" />
              Edit
            </Button>
          }
        >
          <div className="flex gap-2 py-1 text-sm">
            <span className="w-20 shrink-0 text-muted-foreground">Device ID</span>
            <code className="min-w-0 truncate font-mono">{device.device_id}</code>
            <Button
              variant="ghost"
              size="icon-sm"
              className="ml-auto h-5 w-5 shrink-0"
              onClick={() => {
                void navigator.clipboard.writeText(device.device_id);
                toast.success("Copied");
              }}
            >
              <Copy className="h-3 w-3" />
            </Button>
          </div>
          <Prop label="Site">{device.site_id || "—"}</Prop>
          {device.template ? (
            <div className="flex gap-2 py-1 text-sm">
              <span className="w-20 shrink-0 text-muted-foreground">Template</span>
              <Link to={`/templates/${device.template.id}`} className="min-w-0 truncate text-primary hover:underline">
                {device.template.name}
              </Link>
            </div>
          ) : null}
          <Prop label="Last Seen">{formatTimestamp(device.last_seen_at) || "never"}</Prop>
        </SectionCard>

        {hasHardware ? (
          <SectionCard title="Hardware">
            <Prop label="Model">{device.model || "—"}</Prop>
            <Prop label="Mfr">{device.manufacturer || "—"}</Prop>
            <PropMono label="Serial" value={device.serial_number} />
            <PropMono label="MAC" value={device.mac_address} />
            <Prop label="HW Rev">{device.hw_revision || "—"}</Prop>
            <PropMono label="FW Ver" value={device.fw_version} />
          </SectionCard>
        ) : (
          <div />
        )}

        <div className="space-y-3">
          {hasNetwork && (
            <SectionCard title="Network">
              <PropMono label="IMEI" value={device.imei} />
              <PropMono label="SIM" value={device.iccid} />
            </SectionCard>
          )}
          {hasLocation && (
            <SectionCard title="Location">
              {device.latitude != null && device.longitude != null && (
                <PropMono label="Coords" value={`${device.latitude.toFixed(4)}, ${device.longitude.toFixed(4)}`} />
              )}
              {device.address && <Prop label="Address">{device.address}</Prop>}
            </SectionCard>
          )}
        </div>
      </div>

      <div className="col-span-full grid gap-3 sm:grid-cols-2">
        <SectionCard title="Tags">
          <div className="flex flex-wrap items-center gap-1.5">
            {tags.map((tag) => (
              <Badge key={tag} variant="secondary" className="gap-1 pr-1">
                {tag}
                <Button
                  type="button"
                  onClick={() => onTagsChange(tags.filter((t) => t !== tag))}
                  variant="ghost"
                  size="icon-sm"
                  className="h-4 w-4 hover:text-destructive"
                >
                  <X className="h-3 w-3" />
                </Button>
              </Badge>
            ))}
            <Input
              type="text"
              placeholder="Add tag..."
              value={tagInput}
              onChange={(e) => setTagInput(e.target.value)}
              className="h-7 w-24 text-sm"
              onKeyDown={(e) => {
                if (e.key === "Enter") {
                  e.preventDefault();
                  const next = tagInput.trim();
                  if (!next) return;
                  if (tags.some((t) => t.toLowerCase() === next.toLowerCase())) {
                    setTagInput("");
                    return;
                  }
                  onTagsChange([...tags, next]);
                  setTagInput("");
                } else if (e.key === "Backspace" && !tagInput && tags.length > 0) {
                  onTagsChange(tags.slice(0, -1));
                }
              }}
            />
            {tags.length === 0 && !tagInput && <span className="text-sm text-muted-foreground">No tags</span>}
          </div>
        </SectionCard>

        <SectionCard title="Notes">
          <Textarea
            value={notesValue}
            onChange={(e) => onNotesChange(e.target.value)}
            onBlur={onNotesBlur}
            placeholder="Add notes about this device..."
            rows={2}
            className="text-sm"
          />
        </SectionCard>
      </div>
    </>
  );
}
