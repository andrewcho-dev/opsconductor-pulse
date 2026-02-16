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

export interface TemplateVariable {
  name: string;
  type: string;
  description: string;
}

// --- Webhook ---
export async function fetchWebhooks(): Promise<WebhookListResponse> {
  return apiGet("/api/v1/customer/integrations?type=webhook");
}

export async function createWebhook(
  data: WebhookIntegrationCreate
): Promise<WebhookIntegration> {
  return apiPost("/api/v1/customer/integrations", data);
}

export async function updateWebhook(
  id: string,
  data: WebhookIntegrationUpdate
): Promise<WebhookIntegration> {
  return apiPatch(`/api/v1/customer/integrations/${encodeURIComponent(id)}`, data);
}

export async function deleteWebhook(id: string): Promise<void> {
  return apiDelete(`/api/v1/customer/integrations/${encodeURIComponent(id)}`);
}

export async function testWebhook(id: string): Promise<TestDeliveryResult> {
  return apiPost(`/api/v1/customer/integrations/${encodeURIComponent(id)}/test-send`, {});
}

export async function testSendIntegration(id: string): Promise<TestDeliveryResult> {
  return apiPost(`/api/v1/customer/integrations/${encodeURIComponent(id)}/test-send`, {});
}

export async function fetchTemplateVariables(integrationId: string): Promise<{
  variables: TemplateVariable[];
  syntax: string;
  example: string;
}> {
  return apiGet(
    `/api/v1/customer/integrations/${encodeURIComponent(integrationId)}/template-variables`
  );
}

// --- SNMP ---
export async function fetchSnmpIntegrations(): Promise<SnmpIntegration[]> {
  return apiGet("/api/v1/customer/integrations/snmp");
}

export async function createSnmpIntegration(
  data: SnmpIntegrationCreate
): Promise<SnmpIntegration> {
  return apiPost("/api/v1/customer/integrations/snmp", data);
}

export async function updateSnmpIntegration(
  id: string,
  data: SnmpIntegrationUpdate
): Promise<SnmpIntegration> {
  return apiPatch(`/api/v1/customer/integrations/snmp/${encodeURIComponent(id)}`, data);
}

export async function deleteSnmpIntegration(id: string): Promise<void> {
  return apiDelete(`/api/v1/customer/integrations/snmp/${encodeURIComponent(id)}`);
}

export async function testSnmpIntegration(
  id: string
): Promise<TestDeliveryResult> {
  return apiPost(`/api/v1/customer/integrations/snmp/${encodeURIComponent(id)}/test`, {});
}

// --- Email ---
export async function fetchEmailIntegrations(): Promise<EmailIntegration[]> {
  return apiGet("/api/v1/customer/integrations/email");
}

export async function createEmailIntegration(
  data: EmailIntegrationCreate
): Promise<EmailIntegration> {
  return apiPost("/api/v1/customer/integrations/email", data);
}

export async function updateEmailIntegration(
  id: string,
  data: EmailIntegrationUpdate
): Promise<EmailIntegration> {
  return apiPatch(`/api/v1/customer/integrations/email/${encodeURIComponent(id)}`, data);
}

export async function deleteEmailIntegration(id: string): Promise<void> {
  return apiDelete(`/api/v1/customer/integrations/email/${encodeURIComponent(id)}`);
}

export async function testEmailIntegration(
  id: string
): Promise<TestDeliveryResult> {
  return apiPost(`/api/v1/customer/integrations/email/${encodeURIComponent(id)}/test`, {});
}

// --- MQTT ---
export async function fetchMqttIntegrations(): Promise<MqttIntegration[]> {
  return apiGet("/api/v1/customer/integrations/mqtt");
}

export async function createMqttIntegration(
  data: MqttIntegrationCreate
): Promise<MqttIntegration> {
  return apiPost("/api/v1/customer/integrations/mqtt", data);
}

export async function updateMqttIntegration(
  id: string,
  data: MqttIntegrationUpdate
): Promise<MqttIntegration> {
  return apiPatch(`/api/v1/customer/integrations/mqtt/${encodeURIComponent(id)}`, data);
}

export async function deleteMqttIntegration(id: string): Promise<void> {
  return apiDelete(`/api/v1/customer/integrations/mqtt/${encodeURIComponent(id)}`);
}

export async function testMqttIntegration(
  id: string
): Promise<TestDeliveryResult> {
  return apiPost(`/api/v1/customer/integrations/mqtt/${encodeURIComponent(id)}/test`, {});
}
