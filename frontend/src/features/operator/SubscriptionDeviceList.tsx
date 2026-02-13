import { formatDistanceToNow } from "date-fns";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import type { SubscriptionDevice } from "@/services/api/types";

interface SubscriptionDeviceListProps {
  devices: SubscriptionDevice[];
}

export function SubscriptionDeviceList({ devices }: SubscriptionDeviceListProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm font-medium">
          Devices ({devices.length})
        </CardTitle>
      </CardHeader>
      <CardContent>
        {devices.length > 0 ? (
          <Table aria-label="Subscription devices">
            <TableHeader>
              <TableRow>
                <TableHead>Device ID</TableHead>
                <TableHead>Site</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Last Seen</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {devices.map((device) => (
                <TableRow key={device.device_id}>
                  <TableCell className="font-mono text-sm">
                    {device.device_id}
                  </TableCell>
                  <TableCell>{device.site_id}</TableCell>
                  <TableCell>
                    <Badge
                      variant={device.status === "ACTIVE" ? "default" : "secondary"}
                    >
                      {device.status}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-sm text-muted-foreground">
                    {device.last_seen_at
                      ? formatDistanceToNow(new Date(device.last_seen_at), {
                          addSuffix: true,
                        })
                      : "Never"}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        ) : (
          <p className="text-muted-foreground">
            No devices assigned to this subscription.
          </p>
        )}
      </CardContent>
    </Card>
  );
}
