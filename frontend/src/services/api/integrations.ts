import { apiGet, apiPost, apiPatch, apiDelete } from "./client";
import type {
  WebhookIntegration,
  WebhookListResponse,
  WebhookIntegrationCreate,
  WebhookIntegrationUpdate,
  SnmpIntegration,
  SnmpIntegrationCreate,
  SnmpIntegrationUpdate,
  EmailIntegration,
  EmailIntegrationCreate,
  EmailIntegrationUpdate,
  MqttIntegration,
  MqttIntegrationCreate,
  MqttIntegrationUpdate,
  TestDeliveryResult,
} from "./types";

// --- Webhook ---
export async function fetchWebhooks(): Promise<WebhookListResponse> {
  return apiGet("/customer/integrations?type=webhook");
}

export async function createWebhook(
  data: WebhookIntegrationCreate
): Promise<WebhookIntegration> {
  return apiPost("/customer/integrations", data);
}

export async function updateWebhook(
  id: string,
  data: WebhookIntegrationUpdate
): Promise<WebhookIntegration> {
  return apiPatch(`/customer/integrations/${encodeURIComponent(id)}`, data);
}

export async function deleteWebhook(id: string): Promise<void> {
  return apiDelete(`/customer/integrations/${encodeURIComponent(id)}`);
}

export async function testWebhook(id: string): Promise<TestDeliveryResult> {
  return apiPost(`/customer/integrations/${encodeURIComponent(id)}/test`, {});
}

// --- SNMP ---
export async function fetchSnmpIntegrations(): Promise<SnmpIntegration[]> {
  return apiGet("/customer/integrations/snmp");
}

export async function createSnmpIntegration(
  data: SnmpIntegrationCreate
): Promise<SnmpIntegration> {
  return apiPost("/customer/integrations/snmp", data);
}

export async function updateSnmpIntegration(
  id: string,
  data: SnmpIntegrationUpdate
): Promise<SnmpIntegration> {
  return apiPatch(`/customer/integrations/snmp/${encodeURIComponent(id)}`, data);
}

export async function deleteSnmpIntegration(id: string): Promise<void> {
  return apiDelete(`/customer/integrations/snmp/${encodeURIComponent(id)}`);
}

export async function testSnmpIntegration(
  id: string
): Promise<TestDeliveryResult> {
  return apiPost(`/customer/integrations/snmp/${encodeURIComponent(id)}/test`, {});
}

// --- Email ---
export async function fetchEmailIntegrations(): Promise<EmailIntegration[]> {
  return apiGet("/customer/integrations/email");
}

export async function createEmailIntegration(
  data: EmailIntegrationCreate
): Promise<EmailIntegration> {
  return apiPost("/customer/integrations/email", data);
}

export async function updateEmailIntegration(
  id: string,
  data: EmailIntegrationUpdate
): Promise<EmailIntegration> {
  return apiPatch(`/customer/integrations/email/${encodeURIComponent(id)}`, data);
}

export async function deleteEmailIntegration(id: string): Promise<void> {
  return apiDelete(`/customer/integrations/email/${encodeURIComponent(id)}`);
}

export async function testEmailIntegration(
  id: string
): Promise<TestDeliveryResult> {
  return apiPost(`/customer/integrations/email/${encodeURIComponent(id)}/test`, {});
}

// --- MQTT ---
export async function fetchMqttIntegrations(): Promise<MqttIntegration[]> {
  return apiGet("/customer/integrations/mqtt");
}

export async function createMqttIntegration(
  data: MqttIntegrationCreate
): Promise<MqttIntegration> {
  return apiPost("/customer/integrations/mqtt", data);
}

export async function updateMqttIntegration(
  id: string,
  data: MqttIntegrationUpdate
): Promise<MqttIntegration> {
  return apiPatch(`/customer/integrations/mqtt/${encodeURIComponent(id)}`, data);
}

export async function deleteMqttIntegration(id: string): Promise<void> {
  return apiDelete(`/customer/integrations/mqtt/${encodeURIComponent(id)}`);
}

export async function testMqttIntegration(
  id: string
): Promise<TestDeliveryResult> {
  return apiPost(`/customer/integrations/mqtt/${encodeURIComponent(id)}/test`, {});
}
