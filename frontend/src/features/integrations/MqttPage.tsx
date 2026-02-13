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
import { Radio } from "lucide-react";
import { useAuth } from "@/services/auth/AuthProvider";
import {
  useMqttIntegrations,
  useCreateMqtt,
  useUpdateMqtt,
  useDeleteMqtt,
  useTestMqtt,
} from "@/hooks/use-integrations";
import type { MqttIntegration, MqttIntegrationCreate, MqttIntegrationUpdate } from "@/services/api/types";
import { ApiError } from "@/services/api/client";
import { DeleteIntegrationDialog } from "./DeleteIntegrationDialog";
import { TestDeliveryButton } from "./TestDeliveryButton";

type QosValue = "0" | "1" | "2";

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

interface MqttDialogProps {
  open: boolean;
  onClose: () => void;
  integration?: MqttIntegration | null;
}

function MqttDialog({ open, onClose, integration }: MqttDialogProps) {
  const isEditing = !!integration;
  const createMutation = useCreateMqtt();
  const updateMutation = useUpdateMqtt();

  const [name, setName] = useState("");
  const [topic, setTopic] = useState("");
  const [qos, setQos] = useState<QosValue>("0");
  const [retain, setRetain] = useState(false);
  const [enabled, setEnabled] = useState(true);

  useEffect(() => {
    if (!open) return;
    if (integration) {
      setName(integration.name);
      setTopic(integration.mqtt_topic);
      setQos(String(integration.mqtt_qos) as QosValue);
      setRetain(integration.mqtt_retain);
      setEnabled(integration.enabled);
    } else {
      setName("");
      setTopic("");
      setQos("0");
      setRetain(false);
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
    const qosValue = Number(qos);

    if (!isEditing) {
      const payload: MqttIntegrationCreate = {
        name,
        mqtt_topic: topic,
        mqtt_qos: qosValue,
        mqtt_retain: retain,
        enabled,
      };
      await createMutation.mutateAsync(payload);
      onClose();
      return;
    }

    if (!integration) return;
    const updates: MqttIntegrationUpdate = {};
    if (name !== integration.name) updates.name = name;
    if (topic !== integration.mqtt_topic) updates.mqtt_topic = topic;
    if (qosValue !== integration.mqtt_qos) updates.mqtt_qos = qosValue;
    if (retain !== integration.mqtt_retain) updates.mqtt_retain = retain;
    if (enabled !== integration.enabled) updates.enabled = enabled;

    if (Object.keys(updates).length === 0) {
      onClose();
      return;
    }

    await updateMutation.mutateAsync({ id: integration.id, data: updates });
    onClose();
  }

  return (
    <Dialog open={open} onOpenChange={(nextOpen) => !nextOpen && onClose()}>
      <DialogContent id="mqtt-modal">
        <DialogHeader>
          <DialogTitle>{isEditing ? "Edit MQTT Integration" : "Create MQTT Integration"}</DialogTitle>
          <DialogDescription>
            Configure MQTT topics for alert publishing.
          </DialogDescription>
        </DialogHeader>
        <form id="mqtt-form" onSubmit={handleSubmit} className="space-y-4">
          <div className="grid gap-2">
            <Label htmlFor="mqtt-name">Name</Label>
            <Input
              id="mqtt-name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
              placeholder="Critical alerts"
            />
          </div>
          <div className="grid gap-2">
            <Label htmlFor="mqtt-topic">MQTT Topic</Label>
            <Input
              id="mqtt-topic"
              value={topic}
              onChange={(e) => setTopic(e.target.value)}
              required
              placeholder="alerts/tenant-1/critical"
            />
          </div>
          <div className="grid gap-2">
            <Label>QoS</Label>
            <Select value={qos} onValueChange={(v) => setQos(v as QosValue)}>
              <SelectTrigger className="w-full">
                <SelectValue placeholder="Select QoS" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="0">0 - At most once</SelectItem>
                <SelectItem value="1">1 - At least once</SelectItem>
                <SelectItem value="2">2 - Exactly once</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div className="flex items-center justify-between rounded-md border border-border p-3">
            <div>
              <Label className="text-sm">Retain</Label>
              <p className="text-xs text-muted-foreground">
                Retain the last message on the topic.
              </p>
            </div>
            <Switch checked={retain} onCheckedChange={setRetain} />
          </div>
          <div className="flex items-center justify-between rounded-md border border-border p-3">
            <div>
              <Label className="text-sm">Enabled</Label>
              <p className="text-xs text-muted-foreground">
                MQTT messages will be published when enabled.
              </p>
            </div>
            <Switch checked={enabled} onCheckedChange={setEnabled} />
          </div>
          {errorMessage && <div className="text-sm text-destructive">{errorMessage}</div>}
          <DialogFooter>
            <Button id="btn-cancel" type="button" variant="outline" onClick={onClose}>
              Cancel
            </Button>
            <Button type="submit" disabled={isSaving}>
              {isSaving ? "Saving..." : isEditing ? "Save Changes" : "Create MQTT"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

export default function MqttPage() {
  const { user } = useAuth();
  const isAdmin = user?.role === "customer_admin";

  const { data, isLoading, error } = useMqttIntegrations();
  const integrations = data || [];

  const updateMqtt = useUpdateMqtt();
  const deleteMqtt = useDeleteMqtt();
  const testMqtt = useTestMqtt();

  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingIntegration, setEditingIntegration] = useState<MqttIntegration | null>(null);
  const [deletingIntegration, setDeletingIntegration] = useState<MqttIntegration | null>(null);

  return (
    <div className="space-y-6">
      <PageHeader
        title="MQTT"
        description={isLoading ? "Loading..." : `${integrations.length} integrations`}
        action={
          isAdmin ? (
            <Button
              id="btn-add-mqtt"
              onClick={() => {
                setEditingIntegration(null);
                setDialogOpen(true);
              }}
            >
              Add MQTT
            </Button>
          ) : undefined
        }
      />

      {error ? (
        <div className="text-destructive">
          Failed to load MQTT integrations: {(error as Error).message}
        </div>
      ) : isLoading ? (
        <div id="mqtt-list" className="grid gap-4 md:grid-cols-2">
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
          title="No MQTT integrations"
          description="Add MQTT topics to publish alert messages."
          icon={<Radio className="h-12 w-12" />}
          action={
            isAdmin ? (
              <Button
                onClick={() => {
                  setEditingIntegration(null);
                  setDialogOpen(true);
                }}
              >
                Add MQTT
              </Button>
            ) : undefined
          }
        />
      ) : (
        <div id="mqtt-list" className="grid gap-4 md:grid-cols-2">
          {integrations.map((integration) => (
            <Card key={integration.id}>
              <CardHeader className="flex flex-row items-center justify-between">
                <CardTitle className="text-base">{integration.name}</CardTitle>
                <Switch
                  checked={integration.enabled}
                  onCheckedChange={(checked) => {
                    if (!isAdmin) return;
                    updateMqtt.mutate({
                      id: integration.id,
                      data: { enabled: checked },
                    });
                  }}
                  disabled={!isAdmin || updateMqtt.isPending}
                />
              </CardHeader>
              <CardContent className="space-y-2">
                <div className="text-sm text-muted-foreground break-all">
                  {integration.mqtt_topic}
                </div>
                <div className="flex flex-wrap gap-2">
                  <Badge variant="outline">QoS {integration.mqtt_qos}</Badge>
                  <Badge variant="secondary">
                    {integration.mqtt_retain ? "Retain" : "No Retain"}
                  </Badge>
                </div>
              </CardContent>
              <CardFooter className="justify-between">
                {isAdmin ? (
                  <div className="flex items-center gap-2">
                    <TestDeliveryButton
                      onTest={() => testMqtt.mutateAsync(integration.id)}
                      disabled={testMqtt.isPending}
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

      <MqttDialog
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
          deleteMqtt.mutate(deletingIntegration.id, {
            onSuccess: () => setDeletingIntegration(null),
          });
        }}
        isPending={deleteMqtt.isPending}
      />
    </div>
  );
}
