import { useEffect, useMemo, useState } from "react";
import { PageHeader, EmptyState } from "@/components/shared";
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Switch } from "@/components/ui/switch";
import { Button } from "@/components/ui/button";
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
import { Webhook } from "lucide-react";
import { useAuth } from "@/services/auth/AuthProvider";
import {
  useWebhooks,
  useCreateWebhook,
  useUpdateWebhook,
  useDeleteWebhook,
  useTestWebhook,
} from "@/hooks/use-integrations";
import type { WebhookIntegration, WebhookIntegrationCreate, WebhookIntegrationUpdate } from "@/services/api/types";
import { ApiError } from "@/services/api/client";
import { DeleteIntegrationDialog } from "./DeleteIntegrationDialog";
import { TestDeliveryButton } from "./TestDeliveryButton";

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

interface WebhookDialogProps {
  open: boolean;
  onClose: () => void;
  webhook?: WebhookIntegration | null;
}

function WebhookDialog({ open, onClose, webhook }: WebhookDialogProps) {
  const isEditing = !!webhook;
  const createMutation = useCreateWebhook();
  const updateMutation = useUpdateWebhook();

  const [name, setName] = useState("");
  const [url, setUrl] = useState("");
  const [enabled, setEnabled] = useState(true);

  useEffect(() => {
    if (!open) return;
    if (webhook) {
      setName(webhook.name);
      setUrl(webhook.url);
      setEnabled(webhook.enabled);
    } else {
      setName("");
      setUrl("");
      setEnabled(true);
    }
  }, [open, webhook]);

  const errorMessage = useMemo(
    () => formatError(createMutation.error || updateMutation.error),
    [createMutation.error, updateMutation.error]
  );

  const isSaving = createMutation.isPending || updateMutation.isPending;

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!isEditing) {
      const payload: WebhookIntegrationCreate = {
        name,
        webhook_url: url,
        enabled,
      };
      await createMutation.mutateAsync(payload);
      onClose();
      return;
    }

    if (!webhook) return;
    const updates: WebhookIntegrationUpdate = {};
    if (name !== webhook.name) updates.name = name;
    if (url !== webhook.url) updates.webhook_url = url;
    if (enabled !== webhook.enabled) updates.enabled = enabled;

    if (Object.keys(updates).length === 0) {
      onClose();
      return;
    }

    await updateMutation.mutateAsync({
      id: webhook.integration_id,
      data: updates,
    });
    onClose();
  }

  return (
    <Dialog open={open} onOpenChange={(nextOpen) => !nextOpen && onClose()}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{isEditing ? "Edit Webhook" : "Create Webhook"}</DialogTitle>
          <DialogDescription>
            Webhook integrations receive alert payloads via HTTP POST.
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="grid gap-2">
            <Label htmlFor="webhook-name">Name</Label>
            <Input
              id="webhook-name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
              placeholder="Primary webhook"
            />
          </div>
          <div className="grid gap-2">
            <Label htmlFor="webhook-url">Webhook URL</Label>
            <Input
              id="webhook-url"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              required
              placeholder="https://example.com/hook"
            />
          </div>
          <div className="flex items-center justify-between rounded-md border border-border p-3">
            <div>
              <Label className="text-sm">Enabled</Label>
              <p className="text-xs text-muted-foreground">
                Webhook deliveries will be sent when enabled.
              </p>
            </div>
            <Switch checked={enabled} onCheckedChange={setEnabled} />
          </div>
          {errorMessage && (
            <div className="text-sm text-destructive">{errorMessage}</div>
          )}
          <DialogFooter>
            <Button type="button" variant="outline" onClick={onClose}>
              Cancel
            </Button>
            <Button type="submit" disabled={isSaving}>
              {isSaving ? "Saving..." : isEditing ? "Save Changes" : "Create Webhook"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

export default function WebhookPage() {
  const { user } = useAuth();
  const isAdmin = user?.role === "customer_admin";

  const { data, isLoading, error } = useWebhooks();
  const createDialogLabel = isLoading ? "Loading..." : `${data?.integrations?.length || 0} webhooks`;

  const updateWebhook = useUpdateWebhook();
  const deleteWebhook = useDeleteWebhook();
  const testWebhook = useTestWebhook();

  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingWebhook, setEditingWebhook] = useState<WebhookIntegration | null>(null);
  const [deletingWebhook, setDeletingWebhook] = useState<WebhookIntegration | null>(null);

  const webhooks = data?.integrations || [];

  return (
    <div className="space-y-6">
      <PageHeader
        title="Webhooks"
        description={createDialogLabel}
        action={
          isAdmin ? (
            <Button
              onClick={() => {
                setEditingWebhook(null);
                setDialogOpen(true);
              }}
            >
              Add Webhook
            </Button>
          ) : undefined
        }
      />

      {error ? (
        <div className="text-destructive">
          Failed to load webhooks: {(error as Error).message}
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
      ) : webhooks.length === 0 ? (
        <EmptyState
          title="No webhooks configured"
          description="Add a webhook to receive alert payloads."
          icon={<Webhook className="h-12 w-12" />}
          action={
            isAdmin ? (
              <Button
                onClick={() => {
                  setEditingWebhook(null);
                  setDialogOpen(true);
                }}
              >
                Add Webhook
              </Button>
            ) : undefined
          }
        />
      ) : (
        <div className="grid gap-4 md:grid-cols-2">
          {webhooks.map((webhook) => (
            <Card key={webhook.integration_id}>
              <CardHeader className="flex flex-row items-center justify-between">
                <CardTitle className="text-base">{webhook.name}</CardTitle>
                <Switch
                  checked={webhook.enabled}
                  onCheckedChange={(checked) => {
                    if (!isAdmin) return;
                    updateWebhook.mutate({
                      id: webhook.integration_id,
                      data: { enabled: checked },
                    });
                  }}
                  disabled={!isAdmin || updateWebhook.isPending}
                />
              </CardHeader>
              <CardContent>
                <p className="text-sm text-muted-foreground break-all">
                  {webhook.url}
                </p>
              </CardContent>
              <CardFooter className="justify-between">
                {isAdmin ? (
                  <div className="flex items-center gap-2">
                    <TestDeliveryButton
                      onTest={() => testWebhook.mutateAsync(webhook.integration_id)}
                      disabled={testWebhook.isPending}
                    />
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => {
                        setEditingWebhook(webhook);
                        setDialogOpen(true);
                      }}
                    >
                      Edit
                    </Button>
                    <Button
                      variant="destructive"
                      size="sm"
                      onClick={() => setDeletingWebhook(webhook)}
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

      <WebhookDialog
        open={dialogOpen}
        webhook={editingWebhook}
        onClose={() => {
          setDialogOpen(false);
          setEditingWebhook(null);
        }}
      />

      <DeleteIntegrationDialog
        name={deletingWebhook?.name || "integration"}
        open={!!deletingWebhook}
        onClose={() => setDeletingWebhook(null)}
        onConfirm={() => {
          if (!deletingWebhook) return;
          deleteWebhook.mutate(deletingWebhook.integration_id, {
            onSuccess: () => setDeletingWebhook(null),
          });
        }}
        isPending={deleteWebhook.isPending}
      />
    </div>
  );
}
