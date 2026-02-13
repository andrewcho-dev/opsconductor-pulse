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
import { Mail } from "lucide-react";
import { useAuth } from "@/services/auth/AuthProvider";
import {
  useEmailIntegrations,
  useCreateEmail,
  useUpdateEmail,
  useDeleteEmail,
  useTestEmail,
} from "@/hooks/use-integrations";
import type {
  EmailIntegration,
  EmailIntegrationCreate,
  EmailIntegrationUpdate,
} from "@/services/api/types";
import { ApiError } from "@/services/api/client";
import { DeleteIntegrationDialog } from "./DeleteIntegrationDialog";
import { TestDeliveryButton } from "./TestDeliveryButton";

type EmailFormat = "html" | "text";

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

function parseRecipients(value: string): string[] {
  return value
    .split(",")
    .map((v) => v.trim())
    .filter(Boolean);
}

interface EmailDialogProps {
  open: boolean;
  onClose: () => void;
  integration?: EmailIntegration | null;
}

function EmailDialog({ open, onClose, integration }: EmailDialogProps) {
  const isEditing = !!integration;
  const createMutation = useCreateEmail();
  const updateMutation = useUpdateEmail();

  const [name, setName] = useState("");
  const [smtpHost, setSmtpHost] = useState("");
  const [smtpPort, setSmtpPort] = useState("587");
  const [smtpTls, setSmtpTls] = useState(true);
  const [smtpUser, setSmtpUser] = useState("");
  const [smtpPassword, setSmtpPassword] = useState("");
  const [fromAddress, setFromAddress] = useState("");
  const [fromName, setFromName] = useState("OpsConductor Alerts");
  const [toRecipients, setToRecipients] = useState("");
  const [ccRecipients, setCcRecipients] = useState("");
  const [subjectTemplate, setSubjectTemplate] = useState(
    "[{severity}] {alert_type}: {device_id}"
  );
  const [format, setFormat] = useState<EmailFormat>("html");
  const [enabled, setEnabled] = useState(true);

  useEffect(() => {
    if (!open) return;
    if (integration) {
      setName(integration.name);
      setSmtpHost(integration.smtp_host);
      setSmtpPort(String(integration.smtp_port));
      setSmtpTls(integration.smtp_tls);
      setSmtpUser("");
      setSmtpPassword("");
      setFromAddress(integration.from_address);
      setFromName("OpsConductor Alerts");
      setToRecipients("");
      setCcRecipients("");
      setSubjectTemplate("[{severity}] {alert_type}: {device_id}");
      setFormat(integration.template_format);
      setEnabled(integration.enabled);
    } else {
      setName("");
      setSmtpHost("");
      setSmtpPort("587");
      setSmtpTls(true);
      setSmtpUser("");
      setSmtpPassword("");
      setFromAddress("");
      setFromName("OpsConductor Alerts");
      setToRecipients("");
      setCcRecipients("");
      setSubjectTemplate("[{severity}] {alert_type}: {device_id}");
      setFormat("html");
      setEnabled(true);
    }
  }, [open, integration]);

  const errorMessage = useMemo(
    () => formatError(createMutation.error || updateMutation.error),
    [createMutation.error, updateMutation.error]
  );

  const isSaving = createMutation.isPending || updateMutation.isPending;

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const portValue = Number(smtpPort);
    if (Number.isNaN(portValue)) return;

    const toList = parseRecipients(toRecipients);
    const ccList = parseRecipients(ccRecipients);

    if (!isEditing) {
      const payload: EmailIntegrationCreate = {
        name,
        smtp_config: {
          smtp_host: smtpHost,
          smtp_port: portValue,
          smtp_user: smtpUser.trim() || null,
          smtp_password: smtpPassword.trim() || null,
          smtp_tls: smtpTls,
          from_address: fromAddress,
          from_name: fromName.trim() || null,
        },
        recipients: {
          to: toList,
          cc: ccList.length ? ccList : undefined,
        },
        template: {
          subject_template: subjectTemplate,
          format,
        },
        enabled,
      };
      await createMutation.mutateAsync(payload);
      onClose();
      return;
    }

    if (!integration) return;
    const updates: EmailIntegrationUpdate = {};
    if (name !== integration.name) updates.name = name;
    if (smtpHost !== integration.smtp_host || portValue !== integration.smtp_port) {
      updates.smtp_config = {
        smtp_host: smtpHost,
        smtp_port: portValue,
        smtp_user: smtpUser.trim() || null,
        smtp_password: smtpPassword.trim() || null,
        smtp_tls: smtpTls,
        from_address: fromAddress,
        from_name: fromName.trim() || null,
      };
    } else if (smtpUser || smtpPassword || fromName !== "OpsConductor Alerts") {
      updates.smtp_config = {
        smtp_host: smtpHost,
        smtp_port: portValue,
        smtp_user: smtpUser.trim() || null,
        smtp_password: smtpPassword.trim() || null,
        smtp_tls: smtpTls,
        from_address: fromAddress,
        from_name: fromName.trim() || null,
      };
    }
    if (fromAddress !== integration.from_address) {
      updates.smtp_config = {
        smtp_host: smtpHost,
        smtp_port: portValue,
        smtp_user: smtpUser.trim() || null,
        smtp_password: smtpPassword.trim() || null,
        smtp_tls: smtpTls,
        from_address: fromAddress,
        from_name: fromName.trim() || null,
      };
    }
    if (toList.length > 0 || ccList.length > 0) {
      updates.recipients = {
        to: toList,
        cc: ccList.length ? ccList : undefined,
      };
    }
    if (subjectTemplate || format !== integration.template_format) {
      updates.template = {
        subject_template: subjectTemplate,
        format,
      };
    }
    if (enabled !== integration.enabled) updates.enabled = enabled;

    await updateMutation.mutateAsync({ id: integration.id, data: updates });
    onClose();
  }

  return (
    <Dialog open={open} onOpenChange={(nextOpen) => !nextOpen && onClose()}>
      <DialogContent id="email-modal" className="max-w-3xl">
        <DialogHeader>
          <DialogTitle>{isEditing ? "Edit Email Integration" : "Create Email Integration"}</DialogTitle>
          <DialogDescription>
            Configure SMTP delivery and recipient lists for alert emails.
          </DialogDescription>
        </DialogHeader>
        <form id="email-form" onSubmit={handleSubmit} className="space-y-4">
          <div className="grid gap-2">
            <Label htmlFor="email-name">Name</Label>
            <Input
              id="email-name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
              placeholder="Primary email channel"
            />
          </div>

          <div className="grid gap-2 md:grid-cols-2">
            <div className="grid gap-2">
              <Label htmlFor="smtp-host">SMTP Host</Label>
              <Input
                id="smtp-host"
                value={smtpHost}
                onChange={(e) => setSmtpHost(e.target.value)}
                required
                placeholder="smtp.example.com"
              />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="smtp-port">SMTP Port</Label>
              <Input
                id="smtp-port"
                type="number"
                value={smtpPort}
                onChange={(e) => setSmtpPort(e.target.value)}
                required
              />
            </div>
          </div>

          <div className="grid gap-2 md:grid-cols-2">
            <div className="grid gap-2">
              <Label htmlFor="smtp-user">SMTP Username (optional)</Label>
              <Input
                id="smtp-user"
                value={smtpUser}
                onChange={(e) => setSmtpUser(e.target.value)}
              />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="smtp-pass">SMTP Password (optional)</Label>
              <Input
                id="smtp-pass"
                type="password"
                value={smtpPassword}
                onChange={(e) => setSmtpPassword(e.target.value)}
              />
            </div>
          </div>

          <div className="grid gap-2 md:grid-cols-2">
            <div className="grid gap-2">
              <Label htmlFor="from-address">From Address</Label>
              <Input
                id="from-address"
                type="email"
                value={fromAddress}
                onChange={(e) => setFromAddress(e.target.value)}
                required
                placeholder="alerts@example.com"
              />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="from-name">From Name</Label>
              <Input
                id="from-name"
                value={fromName}
                onChange={(e) => setFromName(e.target.value)}
                placeholder="OpsConductor Alerts"
              />
            </div>
          </div>

          <div className="grid gap-2">
            <Label htmlFor="recipients-to">To Recipients</Label>
            <Input
              id="recipients-to"
              value={toRecipients}
              onChange={(e) => setToRecipients(e.target.value)}
              required
              placeholder="alerts@example.com, ops@example.com"
            />
          </div>
          <div className="grid gap-2">
            <Label htmlFor="cc-recipients">CC Recipients (optional)</Label>
            <Input
              id="cc-recipients"
              value={ccRecipients}
              onChange={(e) => setCcRecipients(e.target.value)}
              placeholder="team@example.com"
            />
          </div>

          <div className="grid gap-2 md:grid-cols-2">
            <div className="grid gap-2">
              <Label htmlFor="subject-template">Subject Template</Label>
              <Input
                id="subject-template"
                value={subjectTemplate}
                onChange={(e) => setSubjectTemplate(e.target.value)}
                placeholder="[{severity}] {alert_type}: {device_id}"
              />
            </div>
            <div className="grid gap-2">
              <Label>Format</Label>
              <Select value={format} onValueChange={(v) => setFormat(v as EmailFormat)}>
                <SelectTrigger className="w-full">
                  <SelectValue placeholder="Select format" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="html">HTML</SelectItem>
                  <SelectItem value="text">Text</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>

          <div className="flex items-center justify-between rounded-md border border-border p-3">
            <div>
              <Label className="text-sm">SMTP TLS</Label>
              <p className="text-xs text-muted-foreground">
                Require TLS when connecting to the SMTP server.
              </p>
            </div>
            <Switch checked={smtpTls} onCheckedChange={setSmtpTls} />
          </div>

          <div className="flex items-center justify-between rounded-md border border-border p-3">
            <div>
              <Label className="text-sm">Enabled</Label>
              <p className="text-xs text-muted-foreground">
                Email notifications will be sent when enabled.
              </p>
            </div>
            <Switch checked={enabled} onCheckedChange={setEnabled} />
          </div>

          <div className="rounded-md border border-border p-3">
            <Label className="text-sm">Template variables</Label>
            <p className="text-xs text-muted-foreground">
              Use variables like {"{severity}"}, {"{alert_type}"}, {"{device_id}"}, {"{message}"}, {"{timestamp}"}.
            </p>
          </div>

          {errorMessage && <div className="text-sm text-destructive">{errorMessage}</div>}

          <DialogFooter>
            <Button id="btn-cancel" type="button" variant="outline" onClick={onClose}>
              Cancel
            </Button>
            <Button type="submit" disabled={isSaving}>
              {isSaving ? "Saving..." : isEditing ? "Save Changes" : "Create Email"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

export default function EmailPage() {
  const { user } = useAuth();
  const isAdmin = user?.role === "customer_admin";

  const { data, isLoading, error } = useEmailIntegrations();
  const integrations = data || [];

  const updateEmail = useUpdateEmail();
  const deleteEmail = useDeleteEmail();
  const testEmail = useTestEmail();

  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingIntegration, setEditingIntegration] = useState<EmailIntegration | null>(null);
  const [deletingIntegration, setDeletingIntegration] = useState<EmailIntegration | null>(null);

  return (
    <div className="space-y-6">
      <PageHeader
        title="Email"
        description={isLoading ? "Loading..." : `${integrations.length} integrations`}
        action={
          isAdmin ? (
            <Button
              id="btn-add-email"
              onClick={() => {
                setEditingIntegration(null);
                setDialogOpen(true);
              }}
            >
              Add Email
            </Button>
          ) : undefined
        }
      />

      {error ? (
        <div className="text-destructive">
          Failed to load email integrations: {(error as Error).message}
        </div>
      ) : isLoading ? (
        <div id="email-list" className="grid gap-4 md:grid-cols-2">
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
          title="No email integrations"
          description="Add an email channel to receive alert notifications."
          icon={<Mail className="h-12 w-12" />}
          action={
            isAdmin ? (
              <Button
                onClick={() => {
                  setEditingIntegration(null);
                  setDialogOpen(true);
                }}
              >
                Add Email
              </Button>
            ) : undefined
          }
        />
      ) : (
        <div id="email-list" className="grid gap-4 md:grid-cols-2">
          {integrations.map((integration) => (
            <Card key={integration.id}>
              <CardHeader className="flex flex-row items-center justify-between">
                <CardTitle className="text-base">{integration.name}</CardTitle>
                <Switch
                  checked={integration.enabled}
                  onCheckedChange={(checked) => {
                    if (!isAdmin) return;
                    updateEmail.mutate({
                      id: integration.id,
                      data: { enabled: checked },
                    });
                  }}
                  disabled={!isAdmin || updateEmail.isPending}
                />
              </CardHeader>
              <CardContent className="space-y-2">
                <div className="text-sm text-muted-foreground">
                  {integration.smtp_host}:{integration.smtp_port}
                </div>
                <div className="text-sm text-muted-foreground">
                  From: {integration.from_address}
                </div>
                <div className="flex flex-wrap gap-2">
                  <Badge variant="outline">{integration.recipient_count} recipients</Badge>
                  <Badge variant="secondary">{integration.template_format.toUpperCase()}</Badge>
                </div>
              </CardContent>
              <CardFooter className="justify-between">
                {isAdmin ? (
                  <div className="flex items-center gap-2">
                    <TestDeliveryButton
                      onTest={() => testEmail.mutateAsync(integration.id)}
                      disabled={testEmail.isPending}
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

      <EmailDialog
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
          deleteEmail.mutate(deletingIntegration.id, {
            onSuccess: () => setDeletingIntegration(null),
          });
        }}
        isPending={deleteEmail.isPending}
      />
    </div>
  );
}
