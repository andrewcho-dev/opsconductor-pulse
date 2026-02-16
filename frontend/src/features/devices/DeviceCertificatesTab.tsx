import { useMemo, useState } from "react";
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
  listCertificates,
  generateCertificate,
  rotateCertificate,
  revokeCertificate,
  type GenerateCertResponse,
  type RotateCertResponse,
} from "@/services/api/certificates";
import { OneTimeSecretDisplay } from "@/components/shared/OneTimeSecretDisplay";

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

function ExpiryBadge({ notAfter }: { notAfter: string }) {
  const expiry = new Date(notAfter);
  const daysUntil = Math.floor((expiry.getTime() - Date.now()) / (24 * 60 * 60 * 1000));

  if (daysUntil < 0) {
    return <Badge variant="destructive">Expired</Badge>;
  }
  if (daysUntil <= 30) {
    return (
      <span className="inline-flex items-center gap-1 rounded border px-2 py-0.5 text-xs text-yellow-700 bg-yellow-50 border-yellow-200 dark:text-yellow-300 dark:bg-yellow-950/30">
        <span className="h-1.5 w-1.5 rounded-full bg-yellow-500" />
        Expires in {daysUntil}d
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1 rounded border px-2 py-0.5 text-xs text-green-600 bg-green-50 border-green-200 dark:text-green-300 dark:bg-green-950/30">
      <span className="h-1.5 w-1.5 rounded-full bg-green-500" />
      {daysUntil}d remaining
    </span>
  );
}

function StatusBadge({ status }: { status: string }) {
  switch (status) {
    case "ACTIVE":
      return <Badge variant="default">Active</Badge>;
    case "REVOKED":
      return <Badge variant="destructive">Revoked</Badge>;
    case "EXPIRED":
      return <Badge variant="outline">Expired</Badge>;
    default:
      return <Badge variant="secondary">{status}</Badge>;
  }
}

export function DeviceCertificatesTab({ deviceId }: DeviceCertificatesTabProps) {
  const queryClient = useQueryClient();
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

      {isLoading ? (
        <div className="text-xs text-muted-foreground">Loading certificates...</div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border text-left">
                <th className="py-2 pr-2">Fingerprint</th>
                <th className="py-2 pr-2">Common Name</th>
                <th className="py-2 pr-2">Status</th>
                <th className="py-2 pr-2">Valid From</th>
                <th className="py-2 pr-2">Valid Until</th>
                <th className="py-2 pr-2">Expiry</th>
                <th className="py-2">Actions</th>
              </tr>
            </thead>
            <tbody>
              {(data?.certificates ?? []).length === 0 ? (
                <tr>
                  <td colSpan={7} className="py-4 text-center text-xs text-muted-foreground">
                    No certificates found. Generate one to enable mTLS authentication.
                  </td>
                </tr>
              ) : (
                (data?.certificates ?? []).map((cert) => (
                  <tr key={cert.id} className="border-b border-border/50">
                    <td className="py-2 pr-2 font-mono text-xs" title={cert.fingerprint_sha256}>
                      {cert.fingerprint_sha256.slice(0, 16)}...
                    </td>
                    <td className="py-2 pr-2 text-xs">{cert.common_name}</td>
                    <td className="py-2 pr-2">
                      <StatusBadge status={cert.status} />
                    </td>
                    <td className="py-2 pr-2 text-xs">
                      {new Date(cert.not_before).toLocaleDateString()}
                    </td>
                    <td className="py-2 pr-2 text-xs">
                      {new Date(cert.not_after).toLocaleDateString()}
                    </td>
                    <td className="py-2 pr-2">
                      {cert.status === "ACTIVE" && <ExpiryBadge notAfter={cert.not_after} />}
                      {cert.status === "REVOKED" && (
                        <span className="text-xs text-muted-foreground">
                          Revoked: {cert.revoked_reason || "—"}
                        </span>
                      )}
                    </td>
                    <td className="py-2">
                      {cert.status === "ACTIVE" && (
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={async () => {
                            if (
                              !window.confirm(
                                "Revoke this certificate? The device will no longer be able to authenticate with it."
                              )
                            )
                              return;
                            await revokeMutation.mutateAsync(cert.id);
                          }}
                        >
                          Revoke
                        </Button>
                      )}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      )}

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
    </div>
  );
}

