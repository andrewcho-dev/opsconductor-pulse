import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  fetchWebhooks,
  createWebhook,
  updateWebhook,
  deleteWebhook,
  testWebhook,
  fetchSnmpIntegrations,
  createSnmpIntegration,
  updateSnmpIntegration,
  deleteSnmpIntegration,
  testSnmpIntegration,
  fetchEmailIntegrations,
  createEmailIntegration,
  updateEmailIntegration,
  deleteEmailIntegration,
  testEmailIntegration,
  fetchMqttIntegrations,
  createMqttIntegration,
  updateMqttIntegration,
  deleteMqttIntegration,
  testMqttIntegration,
} from "@/services/api/integrations";
import type {
  WebhookIntegrationCreate,
  WebhookIntegrationUpdate,
  SnmpIntegrationCreate,
  SnmpIntegrationUpdate,
  EmailIntegrationCreate,
  EmailIntegrationUpdate,
  MqttIntegrationCreate,
  MqttIntegrationUpdate,
} from "@/services/api/types";

// --- Webhook hooks ---
export function useWebhooks() {
  return useQuery({
    queryKey: ["webhooks"],
    queryFn: fetchWebhooks,
  });
}

export function useCreateWebhook() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: WebhookIntegrationCreate) => createWebhook(data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["webhooks"] }),
  });
}

export function useUpdateWebhook() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: WebhookIntegrationUpdate }) =>
      updateWebhook(id, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["webhooks"] }),
  });
}

export function useDeleteWebhook() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => deleteWebhook(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["webhooks"] }),
  });
}

export function useTestWebhook() {
  return useMutation({
    mutationFn: (id: string) => testWebhook(id),
  });
}

// --- SNMP hooks ---
export function useSnmpIntegrations() {
  return useQuery({
    queryKey: ["snmp-integrations"],
    queryFn: fetchSnmpIntegrations,
  });
}

export function useCreateSnmp() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: SnmpIntegrationCreate) => createSnmpIntegration(data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["snmp-integrations"] }),
  });
}

export function useUpdateSnmp() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: SnmpIntegrationUpdate }) =>
      updateSnmpIntegration(id, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["snmp-integrations"] }),
  });
}

export function useDeleteSnmp() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => deleteSnmpIntegration(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["snmp-integrations"] }),
  });
}

export function useTestSnmp() {
  return useMutation({
    mutationFn: (id: string) => testSnmpIntegration(id),
  });
}

// --- Email hooks ---
export function useEmailIntegrations() {
  return useQuery({
    queryKey: ["email-integrations"],
    queryFn: fetchEmailIntegrations,
  });
}

export function useCreateEmail() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: EmailIntegrationCreate) => createEmailIntegration(data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["email-integrations"] }),
  });
}

export function useUpdateEmail() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: EmailIntegrationUpdate }) =>
      updateEmailIntegration(id, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["email-integrations"] }),
  });
}

export function useDeleteEmail() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => deleteEmailIntegration(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["email-integrations"] }),
  });
}

export function useTestEmail() {
  return useMutation({
    mutationFn: (id: string) => testEmailIntegration(id),
  });
}

// --- MQTT hooks ---
export function useMqttIntegrations() {
  return useQuery({
    queryKey: ["mqtt-integrations"],
    queryFn: fetchMqttIntegrations,
  });
}

export function useCreateMqtt() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: MqttIntegrationCreate) => createMqttIntegration(data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["mqtt-integrations"] }),
  });
}

export function useUpdateMqtt() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: MqttIntegrationUpdate }) =>
      updateMqttIntegration(id, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["mqtt-integrations"] }),
  });
}

export function useDeleteMqtt() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => deleteMqttIntegration(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["mqtt-integrations"] }),
  });
}

export function useTestMqtt() {
  return useMutation({
    mutationFn: (id: string) => testMqttIntegration(id),
  });
}
