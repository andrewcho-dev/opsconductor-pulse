"use client";

import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { format } from "date-fns";
import { Pencil, Plus, Trash2 } from "lucide-react";
import { PageHeader } from "@/components/shared";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  createOperatorCarrierIntegration,
  deleteOperatorCarrierIntegration,
  fetchOperatorCarrierIntegrations,
  type OperatorCarrierIntegration,
  updateOperatorCarrierIntegration,
} from "@/services/api/operator";

const CARRIER_OPTIONS = ["ALL", "hologram", "1nce"] as const;

export default function OperatorCarriersPage() {
  const queryClient = useQueryClient();
  const [carrierFilter, setCarrierFilter] = useState<string>("ALL");
  const [tenantFilter, setTenantFilter] = useState("");

  const [createOpen, setCreateOpen] = useState(false);
  const [editRow, setEditRow] = useState<OperatorCarrierIntegration | null>(null);
  const [deleteRow, setDeleteRow] = useState<OperatorCarrierIntegration | null>(null);

  const params = useMemo(() => {
    const p: Record<string, string> = {};
    if (carrierFilter !== "ALL") p.carrier_name = carrierFilter;
    if (tenantFilter.trim()) p.tenant_id = tenantFilter.trim();
    return p;
  }, [carrierFilter, tenantFilter]);

  const { data, isLoading } = useQuery({
    queryKey: ["operator-carrier-integrations", params],
    queryFn: () => fetchOperatorCarrierIntegrations(params),
  });

  const rows: OperatorCarrierIntegration[] = data?.integrations ?? [];

  const invalidate = () =>
    queryClient.invalidateQueries({ queryKey: ["operator-carrier-integrations"] });

  const createMut = useMutation({
    mutationFn: createOperatorCarrierIntegration,
    onSuccess: () => {
      invalidate();
      setCreateOpen(false);
    },
  });

  const updateMut = useMutation({
    mutationFn: ({
      id,
      ...rest
    }: { id: number } & Parameters<typeof updateOperatorCarrierIntegration>[1]) =>
      updateOperatorCarrierIntegration(id, rest),
    onSuccess: () => {
      invalidate();
      setEditRow(null);
    },
  });

  const deleteMut = useMutation({
    mutationFn: deleteOperatorCarrierIntegration,
    onSuccess: () => {
      invalidate();
      setDeleteRow(null);
    },
  });

  return (
    <div className="space-y-4">
      <PageHeader
        title="Carrier Integrations"
        description="Manage carrier integrations across all tenants"
      />

      <div className="flex flex-wrap items-center gap-3">
        <div className="w-44">
          <Select value={carrierFilter} onValueChange={setCarrierFilter}>
            <SelectTrigger>
              <SelectValue placeholder="Carrier" />
            </SelectTrigger>
            <SelectContent>
              {CARRIER_OPTIONS.map((c) => (
                <SelectItem key={c} value={c}>
                  {c}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <Input
          className="w-56"
          placeholder="Filter by tenant ID"
          value={tenantFilter}
          onChange={(e) => setTenantFilter(e.target.value)}
        />

        <div className="ml-auto">
          <Button size="sm" onClick={() => setCreateOpen(true)}>
            <Plus className="mr-1 h-4 w-4" /> Add Integration
          </Button>
        </div>
      </div>

      <div className="rounded-md border">
        <Table aria-label="Carrier integrations list">
          <TableHeader>
            <TableRow>
              <TableHead>ID</TableHead>
              <TableHead>Tenant</TableHead>
              <TableHead>Carrier</TableHead>
              <TableHead>Display Name</TableHead>
              <TableHead>Enabled</TableHead>
              <TableHead>Sync</TableHead>
              <TableHead>Last Sync</TableHead>
              <TableHead>API Key</TableHead>
              <TableHead>Created</TableHead>
              <TableHead className="w-20">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading && (
              <TableRow>
                <TableCell colSpan={10} className="text-sm text-muted-foreground">
                  Loading integrations...
                </TableCell>
              </TableRow>
            )}
            {!isLoading && rows.length === 0 && (
              <TableRow>
                <TableCell colSpan={10} className="text-sm text-muted-foreground">
                  No carrier integrations found.
                </TableCell>
              </TableRow>
            )}
            {rows.map((row) => (
              <TableRow key={row.id}>
                <TableCell className="font-mono text-sm">{row.id}</TableCell>
                <TableCell>
                  <Link
                    className="text-primary hover:underline"
                    to={`/operator/tenants/${row.tenant_id}`}
                  >
                    {row.tenant_id}
                  </Link>
                </TableCell>
                <TableCell>
                  <Badge variant="outline">{row.carrier_name}</Badge>
                </TableCell>
                <TableCell>{row.display_name}</TableCell>
                <TableCell>
                  <Badge variant={row.enabled ? "default" : "secondary"}>
                    {row.enabled ? "Yes" : "No"}
                  </Badge>
                </TableCell>
                <TableCell>
                  <Badge variant={row.sync_enabled ? "default" : "secondary"}>
                    {row.last_sync_status || (row.sync_enabled ? "Enabled" : "Disabled")}
                  </Badge>
                </TableCell>
                <TableCell className="text-sm">
                  {row.last_sync_at
                    ? format(new Date(row.last_sync_at), "MMM d, yyyy HH:mm")
                    : "—"}
                </TableCell>
                <TableCell className="font-mono text-sm">
                  {row.api_key_masked ?? "—"}
                </TableCell>
                <TableCell className="text-sm">
                  {format(new Date(row.created_at), "MMM d, yyyy")}
                </TableCell>
                <TableCell>
                  <div className="flex gap-1">
                    <Button
                      variant="ghost"
                      size="icon"
                      aria-label="Edit carrier integration"
                      onClick={() => setEditRow(row)}
                    >
                      <Pencil className="h-4 w-4" />
                    </Button>
                    <Button
                      variant="ghost"
                      size="icon"
                      aria-label="Delete carrier integration"
                      onClick={() => setDeleteRow(row)}
                    >
                      <Trash2 className="h-4 w-4 text-destructive" />
                    </Button>
                  </div>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>

      <CreateCarrierDialog
        open={createOpen}
        onOpenChange={setCreateOpen}
        onSubmit={(formData) => createMut.mutate(formData)}
        isPending={createMut.isPending}
      />

      {editRow && (
        <EditCarrierDialog
          open={!!editRow}
          onOpenChange={(open) => {
            if (!open) setEditRow(null);
          }}
          integration={editRow}
          onSubmit={(formData) => updateMut.mutate({ id: editRow.id, ...formData })}
          isPending={updateMut.isPending}
        />
      )}

      {deleteRow && (
        <Dialog
          open={!!deleteRow}
          onOpenChange={(open) => {
            if (!open) setDeleteRow(null);
          }}
        >
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Delete Integration</DialogTitle>
              <DialogDescription>
                Delete "{deleteRow.display_name}" ({deleteRow.carrier_name}) for tenant{" "}
                {deleteRow.tenant_id}? This will unlink all associated devices.
              </DialogDescription>
            </DialogHeader>
            <DialogFooter>
              <Button variant="outline" onClick={() => setDeleteRow(null)}>
                Cancel
              </Button>
              <Button
                variant="destructive"
                onClick={() => deleteMut.mutate(deleteRow.id)}
                disabled={deleteMut.isPending}
              >
                {deleteMut.isPending ? "Deleting..." : "Delete"}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      )}
    </div>
  );
}

function CreateCarrierDialog({
  open,
  onOpenChange,
  onSubmit,
  isPending,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSubmit: (data: Parameters<typeof createOperatorCarrierIntegration>[0]) => void;
  isPending: boolean;
}) {
  const [form, setForm] = useState({
    tenant_id: "",
    carrier_name: "hologram",
    display_name: "",
    enabled: true,
    api_key: "",
    account_id: "",
    sync_enabled: true,
    sync_interval_minutes: 60,
  });

  const handleSubmit = () => {
    onSubmit({
      tenant_id: form.tenant_id,
      carrier_name: form.carrier_name,
      display_name: form.display_name,
      enabled: form.enabled,
      api_key: form.api_key || null,
      account_id: form.account_id || null,
      sync_enabled: form.sync_enabled,
      sync_interval_minutes: form.sync_interval_minutes,
    });
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>Add Carrier Integration</DialogTitle>
          <DialogDescription>Create a new carrier integration for a tenant.</DialogDescription>
        </DialogHeader>
        <div className="grid gap-4 py-4">
          <div className="grid gap-2">
            <Label>Tenant ID *</Label>
            <Input
              value={form.tenant_id}
              onChange={(e) => setForm({ ...form, tenant_id: e.target.value })}
            />
          </div>
          <div className="grid gap-2">
            <Label>Carrier *</Label>
            <Select
              value={form.carrier_name}
              onValueChange={(v) => setForm({ ...form, carrier_name: v })}
            >
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="hologram">hologram</SelectItem>
                <SelectItem value="1nce">1nce</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div className="grid gap-2">
            <Label>Display Name *</Label>
            <Input
              value={form.display_name}
              onChange={(e) => setForm({ ...form, display_name: e.target.value })}
            />
          </div>
          <div className="grid gap-2">
            <Label>API Key</Label>
            <Input
              value={form.api_key}
              onChange={(e) => setForm({ ...form, api_key: e.target.value })}
            />
          </div>
          <div className="grid gap-2">
            <Label>Account ID</Label>
            <Input
              value={form.account_id}
              onChange={(e) => setForm({ ...form, account_id: e.target.value })}
            />
          </div>
          <div className="flex items-center gap-3">
            <Switch
              checked={form.enabled}
              onCheckedChange={(v) => setForm({ ...form, enabled: v })}
            />
            <Label>Enabled</Label>
          </div>
          <div className="flex items-center gap-3">
            <Switch
              checked={form.sync_enabled}
              onCheckedChange={(v) => setForm({ ...form, sync_enabled: v })}
            />
            <Label>Sync Enabled</Label>
          </div>
          <div className="grid gap-2">
            <Label>Sync Interval (minutes)</Label>
            <Input
              type="number"
              min={5}
              max={1440}
              value={form.sync_interval_minutes}
              onChange={(e) =>
                setForm({ ...form, sync_interval_minutes: Number(e.target.value) })
              }
            />
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button
            onClick={handleSubmit}
            disabled={isPending || !form.tenant_id || !form.display_name}
          >
            {isPending ? "Creating..." : "Create"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function EditCarrierDialog({
  open,
  onOpenChange,
  integration,
  onSubmit,
  isPending,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  integration: OperatorCarrierIntegration;
  onSubmit: (data: Parameters<typeof updateOperatorCarrierIntegration>[1]) => void;
  isPending: boolean;
}) {
  const [form, setForm] = useState({
    display_name: integration.display_name,
    enabled: integration.enabled,
    api_key: "",
    account_id: integration.account_id ?? "",
    sync_enabled: integration.sync_enabled,
    sync_interval_minutes: integration.sync_interval_minutes,
  });

  const handleSubmit = () => {
    const updates: Record<string, unknown> = {};
    if (form.display_name !== integration.display_name) updates.display_name = form.display_name;
    if (form.enabled !== integration.enabled) updates.enabled = form.enabled;
    if (form.api_key) updates.api_key = form.api_key;
    if (form.account_id !== (integration.account_id ?? "")) updates.account_id = form.account_id || null;
    if (form.sync_enabled !== integration.sync_enabled) updates.sync_enabled = form.sync_enabled;
    if (form.sync_interval_minutes !== integration.sync_interval_minutes) {
      updates.sync_interval_minutes = form.sync_interval_minutes;
    }

    if (Object.keys(updates).length === 0) {
      onOpenChange(false);
      return;
    }
    onSubmit(updates as Parameters<typeof updateOperatorCarrierIntegration>[1]);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>Edit Integration</DialogTitle>
          <DialogDescription>
            {integration.carrier_name} — Tenant {integration.tenant_id}
          </DialogDescription>
        </DialogHeader>
        <div className="grid gap-4 py-4">
          <div className="grid gap-2">
            <Label>Display Name</Label>
            <Input
              value={form.display_name}
              onChange={(e) => setForm({ ...form, display_name: e.target.value })}
            />
          </div>
          <div className="grid gap-2">
            <Label>API Key (leave blank to keep current)</Label>
            <Input
              value={form.api_key}
              onChange={(e) => setForm({ ...form, api_key: e.target.value })}
              placeholder={integration.api_key_masked ?? "Not set"}
            />
          </div>
          <div className="grid gap-2">
            <Label>Account ID</Label>
            <Input
              value={form.account_id}
              onChange={(e) => setForm({ ...form, account_id: e.target.value })}
            />
          </div>
          <div className="flex items-center gap-3">
            <Switch
              checked={form.enabled}
              onCheckedChange={(v) => setForm({ ...form, enabled: v })}
            />
            <Label>Enabled</Label>
          </div>
          <div className="flex items-center gap-3">
            <Switch
              checked={form.sync_enabled}
              onCheckedChange={(v) => setForm({ ...form, sync_enabled: v })}
            />
            <Label>Sync Enabled</Label>
          </div>
          <div className="grid gap-2">
            <Label>Sync Interval (minutes)</Label>
            <Input
              type="number"
              min={5}
              max={1440}
              value={form.sync_interval_minutes}
              onChange={(e) =>
                setForm({ ...form, sync_interval_minutes: Number(e.target.value) })
              }
            />
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button onClick={handleSubmit} disabled={isPending}>
            {isPending ? "Saving..." : "Save Changes"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

