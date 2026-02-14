import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  listDeviceTokens,
  revokeDeviceToken,
  rotateDeviceToken,
  type ProvisionDeviceResponse,
} from "@/services/api/devices";
import { CredentialModal } from "./CredentialModal";

interface DeviceApiTokensPanelProps {
  deviceId: string;
}

export function DeviceApiTokensPanel({ deviceId }: DeviceApiTokensPanelProps) {
  const queryClient = useQueryClient();
  const [credentials, setCredentials] = useState<ProvisionDeviceResponse | null>(null);
  const [credentialsOpen, setCredentialsOpen] = useState(false);

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
      setCredentialsOpen(true);
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
          onClick={async () => {
            if (!window.confirm("Rotate credentials and revoke existing active tokens?")) return;
            await rotateMutation.mutateAsync();
          }}
        >
          Rotate Credentials
        </Button>
      </div>

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

      <CredentialModal
        open={credentialsOpen}
        credentials={credentials}
        deviceName={deviceId}
        onClose={() => setCredentialsOpen(false)}
      />
    </div>
  );
}
