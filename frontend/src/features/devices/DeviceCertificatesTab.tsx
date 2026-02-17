import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
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
  listCertificates,
  generateCertificate,
  rotateCertificate,
  revokeCertificate,
  type DeviceCertificate,
  type GenerateCertResponse,
  type RotateCertResponse,
} from "@/services/api/certificates";
import { OneTimeSecretDisplay } from "@/components/shared/OneTimeSecretDisplay";
import { ConfirmDialog } from "@/components/shared/ConfirmDialog";

interface DeviceCertificatesTabProps {
  deviceId: string;
}

function downloadTextFile(filename: string, text: string, mime = "text/plain;charset=utf-8") {
  const blob = new Blob([text], { type: mime });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

function statusVariant(status: string): "default" | "destructive" | "secondary" {
  switch (status) {
    case "ACTIVE":
      return "default";
    case "REVOKED":
      return "destructive";
    case "EXPIRED":
      return "secondary";
    default:
      return "secondary";
  }
}

export function DeviceCertificatesTab({ deviceId }: DeviceCertificatesTabProps) {
  const queryClient = useQueryClient();
  const [revokeTarget, setRevokeTarget] = useState<DeviceCertificate | null>(null);
  const [generatedCert, setGeneratedCert] = useState<
    GenerateCertResponse | RotateCertResponse | null
  >(null);
  const [generateDialogOpen, setGenerateDialogOpen] = useState(false);
  const [rotateDialogOpen, setRotateDialogOpen] = useState(false);

  const { data, isLoading, error } = useQuery({
    queryKey: ["device-certificates", deviceId],
    queryFn: () => listCertificates({ device_id: deviceId }),
    enabled: !!deviceId,
  });

  const generateMutation = useMutation({
    mutationFn: () => generateCertificate(deviceId),
    onSuccess: async (result) => {
      setGeneratedCert(result);
      await queryClient.invalidateQueries({ queryKey: ["device-certificates", deviceId] });
    },
  });

  const rotateMutation = useMutation({
    mutationFn: () => rotateCertificate(deviceId),
    onSuccess: async (result) => {
      setGeneratedCert(result);
      await queryClient.invalidateQueries({ queryKey: ["device-certificates", deviceId] });
    },
  });

  const revokeMutation = useMutation({
    mutationFn: (certId: number) => revokeCertificate(certId),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["device-certificates", deviceId] });
    },
  });

  const activeCerts = useMemo(
    () => data?.certificates?.filter((c) => c.status === "ACTIVE") ?? [],
    [data?.certificates]
  );
  const hasActiveCerts = activeCerts.length > 0;

  const privateKeyPem = generatedCert ? generatedCert.private_key_pem : "";
  const certPem = generatedCert ? generatedCert.cert_pem : "";
  const caPem = generatedCert ? generatedCert.ca_cert_pem : "";

  const columns: ColumnDef<DeviceCertificate>[] = [
    {
      accessorKey: "common_name",
      header: "Common Name",
      cell: ({ row }) => <span className="text-xs">{row.original.common_name}</span>,
    },
    {
      accessorKey: "fingerprint_sha256",
      header: "Fingerprint",
      enableSorting: false,
      cell: ({ row }) => (
        <span
          className="font-mono text-xs text-muted-foreground"
          title={row.original.fingerprint_sha256}
        >
          {row.original.fingerprint_sha256.slice(0, 16)}...
        </span>
      ),
    },
    {
      accessorKey: "status",
      header: "Status",
      cell: ({ row }) => (
        <Badge variant={statusVariant(row.original.status)}>{row.original.status}</Badge>
      ),
    },
    {
      accessorKey: "not_before",
      header: "Valid From",
      cell: ({ row }) => (
        <span className="text-xs text-muted-foreground">
          {new Date(row.original.not_before).toLocaleDateString()}
        </span>
      ),
    },
    {
      accessorKey: "not_after",
      header: "Valid Until",
      cell: ({ row }) => {
        const ts = new Date(row.original.not_after).getTime();
        const expired = Number.isFinite(ts) && ts < Date.now();
        return (
          <span className={`text-xs ${expired ? "text-red-600" : "text-muted-foreground"}`}>
            {new Date(row.original.not_after).toLocaleDateString()}
          </span>
        );
      },
    },
    {
      id: "actions",
      enableSorting: false,
      cell: ({ row }) =>
        row.original.status === "ACTIVE" ? (
          <Button variant="destructive" size="sm" onClick={() => setRevokeTarget(row.original)}>
            Revoke
          </Button>
        ) : null,
    },
  ];

  return (
    <div className="rounded-md border border-border p-3 space-y-3">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-sm font-semibold">X.509 Certificates</h3>
          <p className="text-xs text-muted-foreground">
            Manage device certificates for mutual TLS authentication on MQTT port 8883.
          </p>
        </div>
        <div className="flex gap-2">
          {hasActiveCerts && (
            <Button size="sm" variant="outline" onClick={() => setRotateDialogOpen(true)}>
              Rotate Certificate
            </Button>
          )}
          <Button size="sm" onClick={() => setGenerateDialogOpen(true)}>
            {hasActiveCerts ? "Generate Additional" : "Generate Certificate"}
          </Button>
        </div>
      </div>

      {/* One-time secret display for newly generated cert */}
      {generatedCert && (
        <div className="space-y-2 rounded border border-yellow-300 bg-yellow-50 p-3 dark:border-yellow-700 dark:bg-yellow-950/20">
          <p className="text-sm font-medium text-yellow-800 dark:text-yellow-200">
            {generatedCert.warning}
          </p>

          <OneTimeSecretDisplay label="Private Key (PEM)" value={privateKeyPem} />
          <OneTimeSecretDisplay label="Certificate (PEM)" value={certPem} />
          <OneTimeSecretDisplay label="CA Certificate (PEM)" value={caPem} />

          <div className="flex flex-wrap gap-2">
            <Button
              size="sm"
              variant="outline"
              onClick={() => downloadTextFile(`device-${deviceId}.key`, privateKeyPem)}
            >
              Download Key
            </Button>
            <Button
              size="sm"
              variant="outline"
              onClick={() => downloadTextFile(`device-${deviceId}.crt`, certPem)}
            >
              Download Cert
            </Button>
            <Button size="sm" variant="outline" onClick={() => downloadTextFile("device-ca.crt", caPem)}>
              Download CA
            </Button>
            <Button size="sm" variant="outline" onClick={() => setGeneratedCert(null)}>
              Dismiss
            </Button>
          </div>
        </div>
      )}

      {error && <div className="text-sm text-destructive">Failed to load certificates.</div>}

      <DataTable
        columns={columns}
        data={data?.certificates ?? []}
        isLoading={isLoading}
        emptyState={
          <div className="rounded-md border border-border py-8 text-center text-muted-foreground">
            No certificates uploaded for this device.
          </div>
        }
        manualPagination={false}
      />

      {/* Generate Certificate Dialog */}
      <AlertDialog open={generateDialogOpen} onOpenChange={setGenerateDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Generate Device Certificate</AlertDialogTitle>
            <AlertDialogDescription>
              This will generate a new X.509 certificate for this device, signed by the platform
              Device CA. The private key will be shown once -- save it immediately.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={async (e) => {
                e.preventDefault();
                await generateMutation.mutateAsync();
                setGenerateDialogOpen(false);
              }}
            >
              Generate
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* Rotate Certificate Dialog */}
      <AlertDialog open={rotateDialogOpen} onOpenChange={setRotateDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Rotate Device Certificate</AlertDialogTitle>
            <AlertDialogDescription>
              This generates a new certificate while keeping the existing one active for a grace
              period (24 hours by default). Update the device with the new certificate, then revoke
              the old one.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={async (e) => {
                e.preventDefault();
                await rotateMutation.mutateAsync();
                setRotateDialogOpen(false);
              }}
            >
              Rotate
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      <ConfirmDialog
        open={!!revokeTarget}
        onOpenChange={(open) => {
          if (!open) setRevokeTarget(null);
        }}
        title="Revoke Certificate"
        description="Are you sure you want to revoke this certificate? The device will no longer be able to authenticate with it. This action cannot be undone."
        confirmText="Revoke Certificate"
        variant="destructive"
        onConfirm={() => {
          if (revokeTarget) {
            void revokeMutation.mutateAsync(revokeTarget.id);
            setRevokeTarget(null);
          }
        }}
        isPending={revokeMutation.isPending}
      />
    </div>
  );
}

