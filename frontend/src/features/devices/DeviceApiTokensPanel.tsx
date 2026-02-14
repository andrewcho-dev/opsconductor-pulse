import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
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

function TokenAgeChip({ createdAt }: { createdAt: string }) {
  const created = new Date(createdAt);
  const ageDays = Number.isNaN(created.getTime())
    ? 0
    : Math.floor((Date.now() - created.getTime()) / (24 * 60 * 60 * 1000));
  const tone =
    ageDays < 30
      ? "text-green-600 bg-green-50 border-green-200 dark:text-green-300 dark:bg-green-950/30"
      : ageDays <= 90
        ? "text-yellow-700 bg-yellow-50 border-yellow-200 dark:text-yellow-300 dark:bg-yellow-950/30"
        : "text-red-700 bg-red-50 border-red-200 dark:text-red-300 dark:bg-red-950/30";
  return (
    <span className={`inline-flex items-center gap-1 rounded border px-2 py-0.5 text-xs ${tone}`}>
      <span
        className={`h-1.5 w-1.5 rounded-full ${
          ageDays < 30 ? "bg-green-500" : ageDays <= 90 ? "bg-yellow-500" : "bg-red-500"
        }`}
      />
      {ageDays} days old
      {ageDays > 90 ? " (consider rotating)" : ""}
    </span>
  );
}

export function DeviceApiTokensPanel({ deviceId }: DeviceApiTokensPanelProps) {
  const queryClient = useQueryClient();
  const [credentials, setCredentials] = useState<ProvisionDeviceResponse | null>(null);
  const [confirmOpen, setConfirmOpen] = useState(false);

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

  return (
    <div className="rounded-md border border-border p-3 space-y-3">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-sm font-semibold">API Tokens</h3>
          <p className="text-xs text-muted-foreground">
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
      {isLoading ? (
        <div className="text-xs text-muted-foreground">Loading tokens...</div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border text-left">
                <th className="py-2 pr-2">Client ID</th>
                <th className="py-2 pr-2">Label</th>
                <th className="py-2 pr-2">Created</th>
                <th className="py-2 pr-2">Age</th>
                <th className="py-2 pr-2">Status</th>
                <th className="py-2">Actions</th>
              </tr>
            </thead>
            <tbody>
              {(data?.tokens ?? []).map((token) => (
                <tr key={token.id} className="border-b border-border/50">
                  <td className="py-2 pr-2 font-mono text-xs">{token.client_id}</td>
                  <td className="py-2 pr-2">{token.label}</td>
                  <td className="py-2 pr-2 text-xs">{new Date(token.created_at).toLocaleString()}</td>
                  <td className="py-2 pr-2">
                    <TokenAgeChip createdAt={token.created_at} />
                  </td>
                  <td className="py-2 pr-2">
                    <Badge variant={token.revoked_at ? "outline" : "default"}>
                      {token.revoked_at ? "Revoked" : "Active"}
                    </Badge>
                  </td>
                  <td className="py-2">
                    {!token.revoked_at && (
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={async () => {
                          if (!window.confirm("Revoke this token?")) return;
                          await revokeMutation.mutateAsync(token.id);
                        }}
                      >
                        Revoke
                      </Button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

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
    </div>
  );
}
