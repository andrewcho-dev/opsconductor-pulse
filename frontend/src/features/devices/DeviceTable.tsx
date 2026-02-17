import { Link } from "react-router-dom";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { formatTimestamp } from "@/lib/format";
import type { Device } from "@/services/api/types";

function StatusText({ status }: { status: string }) {
  const color =
    status === "ONLINE"
      ? "text-status-online"
      : status === "STALE"
      ? "text-status-stale"
      : "text-status-offline";
  return <span className={color}>{status}</span>;
}

function TagsCell({ tags }: { tags?: string[] }) {
  if (!tags || tags.length === 0) {
    return <span className="text-muted-foreground">—</span>;
  }

  const maxShow = 3;
  const visible = tags.slice(0, maxShow);
  const remaining = tags.length - maxShow;

  return (
    <span className="text-muted-foreground">
      {visible.join(", ")}{remaining > 0 && `, +${remaining}`}
    </span>
  );
}

interface DeviceTableProps {
  devices: Device[];
  selectedTagsCount: number;
  onOpenTagFilter: () => void;
  onEdit?: (device: Device) => void;
  onDecommission?: (device: Device) => void;
}

export function DeviceTable({
  devices,
  selectedTagsCount,
  onOpenTagFilter,
  onEdit,
  onDecommission,
}: DeviceTableProps) {
  return (
    <div className="rounded-md border border-border overflow-hidden">
      <Table className="text-sm" aria-label="Device list">
        <TableHeader>
          <TableRow className="hover:bg-transparent">
            <TableHead className="h-7 py-1 px-2">Device ID</TableHead>
            <TableHead className="h-7 py-1 px-2">Site</TableHead>
            <TableHead className="h-7 py-1 px-2">Status</TableHead>
            <TableHead
              className="h-7 py-1 px-2 cursor-pointer hover:bg-muted"
              onClick={onOpenTagFilter}
            >
              Tags {selectedTagsCount > 0 && `(${selectedTagsCount})`}
            </TableHead>
            <TableHead className="h-7 py-1 px-2">Last Seen</TableHead>
            <TableHead className="h-7 py-1 px-2">Actions</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {devices.map((d) => (
            <TableRow key={d.device_id} className="hover:bg-muted/50">
              <TableCell className="py-1 px-2 font-mono">
                <Link to={`/devices/${d.device_id}`} className="text-primary hover:underline">
                  {d.device_id}
                </Link>
              </TableCell>
              <TableCell className="py-1 px-2">{d.site_id}</TableCell>
              <TableCell className="py-1 px-2">
                <StatusText status={d.status} />
              </TableCell>
              <TableCell className="py-1 px-2">
                <TagsCell tags={d.tags} />
              </TableCell>
              <TableCell className="py-1 px-2 text-muted-foreground whitespace-nowrap font-mono">
                {d.last_seen_at ? formatTimestamp(d.last_seen_at) : "—"}
              </TableCell>
              <TableCell className="py-1 px-2">
                <div className="flex items-center gap-2">
                  <button type="button" className="text-sm text-primary hover:underline" onClick={() => onEdit?.(d)}>
                    Edit
                  </button>
                  <button type="button" className="text-sm text-destructive hover:underline" onClick={() => onDecommission?.(d)}>
                    Decommission
                  </button>
                </div>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}
