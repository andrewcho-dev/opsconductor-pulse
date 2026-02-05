import { useEffect, useMemo, useState } from "react";
import { PageHeader, EmptyState } from "@/components/shared";
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Switch } from "@/components/ui/switch";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Network } from "lucide-react";
import { useAuth } from "@/services/auth/AuthProvider";
import {
  useSnmpIntegrations,
  useCreateSnmp,
  useUpdateSnmp,
  useDeleteSnmp,
  useTestSnmp,
} from "@/hooks/use-integrations";
import type {
  SnmpIntegration,
  SnmpIntegrationCreate,
  SnmpIntegrationUpdate,
  SnmpV2cConfig,
  SnmpV3Config,
} from "@/services/api/types";
import { ApiError } from "@/services/api/client";
import { DeleteIntegrationDialog } from "./DeleteIntegrationDialog";
import { TestDeliveryButton } from "./TestDeliveryButton";

type SnmpVersion = "2c" | "3";
type AuthProtocol = "MD5" | "SHA" | "SHA256";
type PrivProtocol = "DES" | "AES" | "AES256";

function formatError(error: unknown): string {
  if (!error) return "";
  if (error instanceof ApiError) {
    if (typeof error.body === "string") return error.body;
    if (error.body && typeof error.body === "object") {
      const detail = (error.body as { detail?: string }).detail;
      if (detail) return detail;
    }
    return error.message;
  }
  if (error instanceof Error) return error.message;
  return "Unknown error";
}

interface SnmpDialogProps {
  open: boolean;
  onClose: () => void;
  integration?: SnmpIntegration | null;
}

function SnmpDialog({ open, onClose, integration }: SnmpDialogProps) {
  const isEditing = !!integration;
  const createMutation = useCreateSnmp();
  const updateMutation = useUpdateSnmp();

  const [name, setName] = useState("");
  const [host, setHost] = useState("");
  const [port, setPort] = useState("162");
  const [version, setVersion] = useState<SnmpVersion>("2c");
  const [oidPrefix, setOidPrefix] = useState("1.3.6.1.4.1.99999");
  const [enabled, setEnabled] = useState(true);

  const [community, setCommunity] = useState("");
  const [username, setUsername] = useState("");
  const [authProtocol, setAuthProtocol] = useState<AuthProtocol>("SHA");
  const [authPassword, setAuthPassword] = useState("");
  const [privProtocol, setPrivProtocol] = useState<PrivProtocol>("AES");
  const [privPassword, setPrivPassword] = useState("");

  useEffect(() => {
    if (!open) return;
    if (integration) {
      setName(integration.name);
      setHost(integration.snmp_host);
      setPort(String(integration.snmp_port));
      setVersion(integration.snmp_version);
      setOidPrefix(integration.snmp_oid_prefix);
      setEnabled(integration.enabled);
      setCommunity("");
      setUsername("");
      setAuthProtocol("SHA");
      setAuthPassword("");
      setPrivProtocol("AES");
      setPrivPassword("");
    } else {
      setName("");
      setHost("");
      setPort("162");
      setVersion("2c");
      setOidPrefix("1.3.6.1.4.1.99999");
      setEnabled(true);
      setCommunity("");
      setUsername("");
      setAuthProtocol("SHA");
      setAuthPassword("");
      setPrivProtocol("AES");
      setPrivPassword("");
    }
  }, [open, integration]);

  const errorMessage = useMemo(
    () => formatError(createMutation.error || updateMutation.error),
    [createMutation.error, updateMutation.error]
  );

  const isSaving = createMutation.isPending || updateMutation.isPending;

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const portValue = Number(port);
    if (Number.isNaN(portValue)) return;

    const snmpConfig = (
      version === "2c"
        ? { version: "2c", community }
        : {
            version: "3",
            username,
            auth_protocol: authProtocol,
            auth_password: authPassword,
            priv_protocol: privPassword ? privProtocol : undefined,
            priv_password: privPassword || undefined,
          }
    ) as SnmpV2cConfig | SnmpV3Config;

    if (!isEditing) {
      const payload: SnmpIntegrationCreate = {
        name,
        snmp_host: host,
        snmp_port: portValue,
        snmp_config: snmpConfig,
        snmp_oid_prefix: oidPrefix,
        enabled,
      };
      await createMutation.mutateAsync(payload);
      onClose();
      return;
    }

    if (!integration) return;
    const updates: SnmpIntegrationUpdate = {};
    if (name !== integration.name) updates.name = name;
    if (host !== integration.snmp_host) updates.snmp_host = host;
    if (portValue !== integration.snmp_port) updates.snmp_port = portValue;
    if (oidPrefix !== integration.snmp_oid_prefix) updates.snmp_oid_prefix = oidPrefix;
    if (enabled !== integration.enabled) updates.enabled = enabled;
    updates.snmp_config = snmpConfig;

    await updateMutation.mutateAsync({ id: integration.id, data: updates });
    onClose();
  }

  return (
    <Dialog open={open} onOpenChange={(nextOpen) => !nextOpen && onClose()}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle>{isEditing ? "Edit SNMP Integration" : "Create SNMP Integration"}</DialogTitle>
          <DialogDescription>
            Configure SNMP trap destinations for alert delivery.
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="grid gap-2">
            <Label htmlFor="snmp-name">Name</Label>
            <Input
              id="snmp-name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
              placeholder="Primary SNMP destination"
            />
          </div>
          <div className="grid gap-2 md:grid-cols-2">
            <div className="grid gap-2">
              <Label htmlFor="snmp-host">SNMP Host</Label>
              <Input
                id="snmp-host"
                value={host}
                onChange={(e) => setHost(e.target.value)}
                required
                placeholder="snmp.example.com"
              />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="snmp-port">SNMP Port</Label>
              <Input
                id="snmp-port"
                type="number"
                value={port}
                onChange={(e) => setPort(e.target.value)}
                required
              />
            </div>
          </div>
          <div className="grid gap-2 md:grid-cols-2">
            <div className="grid gap-2">
              <Label>SNMP Version</Label>
              <Select value={version} onValueChange={(v) => setVersion(v as SnmpVersion)}>
                <SelectTrigger className="w-full">
                  <SelectValue placeholder="Select version" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="2c">v2c</SelectItem>
                  <SelectItem value="3">v3</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="grid gap-2">
              <Label htmlFor="snmp-oid">OID Prefix</Label>
              <Input
                id="snmp-oid"
                value={oidPrefix}
                onChange={(e) => setOidPrefix(e.target.value)}
                placeholder="1.3.6.1.4.1.99999"
              />
            </div>
          </div>

          {version === "2c" ? (
            <div className="grid gap-2">
              <Label htmlFor="snmp-community">Community String</Label>
              <Input
                id="snmp-community"
                value={community}
                onChange={(e) => setCommunity(e.target.value)}
                required
              />
            </div>
          ) : (
            <div className="space-y-4 rounded-md border border-border p-4">
              <div className="grid gap-2 md:grid-cols-2">
                <div className="grid gap-2">
                  <Label htmlFor="snmp-username">Username</Label>
                  <Input
                    id="snmp-username"
                    value={username}
                    onChange={(e) => setUsername(e.target.value)}
                    required
                  />
                </div>
                <div className="grid gap-2">
                  <Label>Auth Protocol</Label>
                  <Select
                    value={authProtocol}
                    onValueChange={(v) => setAuthProtocol(v as AuthProtocol)}
                  >
                    <SelectTrigger className="w-full">
                      <SelectValue placeholder="Select protocol" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="MD5">MD5</SelectItem>
                      <SelectItem value="SHA">SHA</SelectItem>
                      <SelectItem value="SHA256">SHA256</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>
              <div className="grid gap-2 md:grid-cols-2">
                <div className="grid gap-2">
                  <Label htmlFor="snmp-auth-password">Auth Password</Label>
                  <Input
                    id="snmp-auth-password"
                    type="password"
                    value={authPassword}
                    onChange={(e) => setAuthPassword(e.target.value)}
                    required
                  />
                </div>
                <div className="grid gap-2">
                  <Label>Privacy Protocol</Label>
                  <Select
                    value={privProtocol}
                    onValueChange={(v) => setPrivProtocol(v as PrivProtocol)}
                  >
                    <SelectTrigger className="w-full">
                      <SelectValue placeholder="Select protocol" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="DES">DES</SelectItem>
                      <SelectItem value="AES">AES</SelectItem>
                      <SelectItem value="AES256">AES256</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>
              <div className="grid gap-2">
                <Label htmlFor="snmp-priv-password">Privacy Password (optional)</Label>
                <Input
                  id="snmp-priv-password"
                  type="password"
                  value={privPassword}
                  onChange={(e) => setPrivPassword(e.target.value)}
                />
              </div>
            </div>
          )}

          <div className="flex items-center justify-between rounded-md border border-border p-3">
            <div>
              <Label className="text-sm">Enabled</Label>
              <p className="text-xs text-muted-foreground">
                SNMP traps will be sent when enabled.
              </p>
            </div>
            <Switch checked={enabled} onCheckedChange={setEnabled} />
          </div>

          {errorMessage && <div className="text-sm text-destructive">{errorMessage}</div>}

          <DialogFooter>
            <Button type="button" variant="outline" onClick={onClose}>
              Cancel
            </Button>
            <Button type="submit" disabled={isSaving}>
              {isSaving ? "Saving..." : isEditing ? "Save Changes" : "Create SNMP"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

export default function SnmpPage() {
  const { user } = useAuth();
  const isAdmin = user?.role === "customer_admin";

  const { data, isLoading, error } = useSnmpIntegrations();
  const integrations = data || [];

  const updateSnmp = useUpdateSnmp();
  const deleteSnmp = useDeleteSnmp();
  const testSnmp = useTestSnmp();

  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingIntegration, setEditingIntegration] = useState<SnmpIntegration | null>(null);
  const [deletingIntegration, setDeletingIntegration] = useState<SnmpIntegration | null>(null);

  return (
    <div className="space-y-6">
      <PageHeader
        title="SNMP"
        description={isLoading ? "Loading..." : `${integrations.length} integrations`}
        action={
          isAdmin ? (
            <Button
              onClick={() => {
                setEditingIntegration(null);
                setDialogOpen(true);
              }}
            >
              Add SNMP
            </Button>
          ) : undefined
        }
      />

      {error ? (
        <div className="text-destructive">
          Failed to load SNMP integrations: {(error as Error).message}
        </div>
      ) : isLoading ? (
        <div className="grid gap-4 md:grid-cols-2">
          {[1, 2, 3].map((i) => (
            <Card key={i}>
              <CardHeader>
                <Skeleton className="h-5 w-40" />
              </CardHeader>
              <CardContent>
                <Skeleton className="h-4 w-64" />
              </CardContent>
              <CardFooter>
                <Skeleton className="h-8 w-24" />
              </CardFooter>
            </Card>
          ))}
        </div>
      ) : integrations.length === 0 ? (
        <EmptyState
          title="No SNMP integrations"
          description="Add an SNMP destination to receive traps."
          icon={<Network className="h-12 w-12" />}
          action={
            isAdmin ? (
              <Button
                onClick={() => {
                  setEditingIntegration(null);
                  setDialogOpen(true);
                }}
              >
                Add SNMP
              </Button>
            ) : undefined
          }
        />
      ) : (
        <div className="grid gap-4 md:grid-cols-2">
          {integrations.map((integration) => (
            <Card key={integration.id}>
              <CardHeader className="flex flex-row items-center justify-between">
                <CardTitle className="text-base">{integration.name}</CardTitle>
                <Switch
                  checked={integration.enabled}
                  onCheckedChange={(checked) => {
                    if (!isAdmin) return;
                    updateSnmp.mutate({
                      id: integration.id,
                      data: { enabled: checked },
                    });
                  }}
                  disabled={!isAdmin || updateSnmp.isPending}
                />
              </CardHeader>
              <CardContent className="space-y-2">
                <div className="text-sm text-muted-foreground">
                  {integration.snmp_host}:{integration.snmp_port}
                </div>
                <div className="flex flex-wrap gap-2">
                  <Badge variant="outline">v{integration.snmp_version}</Badge>
                  <Badge variant="secondary">{integration.snmp_oid_prefix}</Badge>
                </div>
              </CardContent>
              <CardFooter className="justify-between">
                {isAdmin ? (
                  <div className="flex items-center gap-2">
                    <TestDeliveryButton
                      onTest={() => testSnmp.mutateAsync(integration.id)}
                      disabled={testSnmp.isPending}
                    />
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => {
                        setEditingIntegration(integration);
                        setDialogOpen(true);
                      }}
                    >
                      Edit
                    </Button>
                    <Button
                      variant="destructive"
                      size="sm"
                      onClick={() => setDeletingIntegration(integration)}
                    >
                      Delete
                    </Button>
                  </div>
                ) : (
                  <span className="text-xs text-muted-foreground">View only</span>
                )}
              </CardFooter>
            </Card>
          ))}
        </div>
      )}

      <SnmpDialog
        open={dialogOpen}
        integration={editingIntegration}
        onClose={() => {
          setDialogOpen(false);
          setEditingIntegration(null);
        }}
      />

      <DeleteIntegrationDialog
        name={deletingIntegration?.name || "integration"}
        open={!!deletingIntegration}
        onClose={() => setDeletingIntegration(null)}
        onConfirm={() => {
          if (!deletingIntegration) return;
          deleteSnmp.mutate(deletingIntegration.id, {
            onSuccess: () => setDeletingIntegration(null),
          });
        }}
        isPending={deleteSnmp.isPending}
      />
    </div>
  );
}
