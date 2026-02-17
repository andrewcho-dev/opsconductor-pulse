import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { DataTable } from "@/components/ui/data-table";
import { type ColumnDef } from "@tanstack/react-table";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import {
  listDeviceTokens,
  revokeDeviceToken,
  rotateDeviceToken,
  type ProvisionDeviceResponse,
} from "@/services/api/devices";
import { OneTimeSecretDisplay } from "@/components/shared/OneTimeSecretDisplay";

interface DeviceApiTokensPanelProps {
  deviceId: string;
}

export function DeviceApiTokensPanel({ deviceId }: DeviceApiTokensPanelProps) {
  const queryClient = useQueryClient();
  const [credentials, setCredentials] = useState<ProvisionDeviceResponse | null>(null);
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [confirmRevokeToken, setConfirmRevokeToken] = useState<string | null>(null);

  const { data, isLoading, error } = useQuery({
    queryKey: ["device-tokens", deviceId],
    queryFn: () => listDeviceTokens(deviceId),
    enabled: !!deviceId,
  });

  const revokeMutation = useMutation({
    mutationFn: (tokenId: string) => revokeDeviceToken(deviceId, tokenId),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["device-tokens", deviceId] });
    },
  });

  const rotateMutation = useMutation({
    mutationFn: () => rotateDeviceToken(deviceId),
    onSuccess: async (result) => {
      setCredentials(result);
      await queryClient.invalidateQueries({ queryKey: ["device-tokens", deviceId] });
    },
  });

  const tokens = data?.tokens ?? [];

  type TokenRow = (typeof tokens)[number] & { expires_at?: string; token_prefix?: string };

  const columns: ColumnDef<TokenRow>[] = [
    {
      accessorKey: "label",
      header: "Name",
      cell: ({ row }) => <span className="font-medium">{row.original.label}</span>,
    },
    {
      id: "token_prefix",
      header: "Token",
      enableSorting: false,
      accessorFn: (t) => t.token_prefix ?? t.client_id ?? t.id,
      cell: ({ row }) => {
        const raw = row.original.token_prefix ?? row.original.client_id ?? row.original.id;
        const prefix = raw ? `${String(raw).slice(0, 8)}...` : "—";
        return (
          <span className="font-mono text-sm text-muted-foreground" title={raw}>
            {prefix}
          </span>
        );
      },
    },
    {
      accessorKey: "created_at",
      header: "Created",
      cell: ({ row }) => (
        <span className="text-sm text-muted-foreground">
          {row.original.created_at ? new Date(row.original.created_at).toLocaleString() : "—"}
        </span>
      ),
    },
    {
      id: "expires_at",
      header: "Expires",
      accessorFn: (t) => t.expires_at ?? "",
      cell: ({ row }) => {
        const expiresAt = row.original.expires_at;
        if (!expiresAt) return <span className="text-sm text-muted-foreground">—</span>;
        const ts = new Date(expiresAt).getTime();
        const expired = Number.isFinite(ts) && ts < Date.now();
        return (
          <span className={`text-sm ${expired ? "text-status-critical" : "text-muted-foreground"}`}>
            {new Date(expiresAt).toLocaleString()}
          </span>
        );
      },
    },
    {
      id: "actions",
      enableSorting: false,
      cell: ({ row }) =>
        row.original.revoked_at ? null : (
          <Button
            variant="destructive"
            size="sm"
            onClick={() => setConfirmRevokeToken(row.original.id)}
          >
            Revoke
          </Button>
        ),
    },
  ];

  return (
    <div className="rounded-md border border-border p-3 space-y-3">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-sm font-semibold">API Tokens</h3>
          <p className="text-sm text-muted-foreground">
            Revoking a token will immediately disconnect any device using it.
          </p>
        </div>
        <Button
          size="sm"
          onClick={() => setConfirmOpen(true)}
        >
          {(data?.tokens?.length ?? 0) > 0 ? "Rotate Credentials" : "Create Token"}
        </Button>
      </div>

      {credentials && (
        <OneTimeSecretDisplay
          label="API Token"
          value={credentials.password}
          filename={`device-${deviceId}.env`}
        />
      )}

      {error && <div className="text-sm text-destructive">Failed to load tokens.</div>}
      <DataTable
        columns={columns}
        data={tokens as TokenRow[]}
        isLoading={isLoading}
        emptyState={
          <div className="rounded-md border border-border py-8 text-center text-muted-foreground">
            No API tokens for this device. Create a token to enable programmatic access.
          </div>
        }
        manualPagination={false}
      />

      <AlertDialog open={confirmOpen} onOpenChange={setConfirmOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Rotate API Credentials</AlertDialogTitle>
            <AlertDialogDescription>
              Creating a new token will not automatically revoke existing tokens. Revoke old tokens
              after updating your device configuration.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={async (e) => {
                e.preventDefault();
                await rotateMutation.mutateAsync();
                setConfirmOpen(false);
              }}
            >
              Generate Token
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      <AlertDialog
        open={!!confirmRevokeToken}
        onOpenChange={(open) => !open && setConfirmRevokeToken(null)}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Revoke Token</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to revoke this token? This action cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={async () => {
                if (confirmRevokeToken) await revokeMutation.mutateAsync(confirmRevokeToken);
                setConfirmRevokeToken(null);
              }}
            >
              Revoke
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
