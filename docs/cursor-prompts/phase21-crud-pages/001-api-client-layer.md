# Task 001: API Client Layer — Types, Functions, Hooks

> **CURSOR: EXECUTE THIS TASK**
>
> Read the instructions below and implement them exactly.
> Create only the files listed in "Files to Create/Modify".
> RUN THE TESTS in the Test section. Do not proceed if tests fail.
> IMPORTANT: Do not commit until all tests pass.

---

## Context

Phase 18 created API client functions for devices, alerts, and telemetry. Phase 21 needs CRUD operations for alert rules, four integration types (webhook, SNMP, email, MQTT), and read-only operator data. This task creates the entire API client layer that Tasks 2-4 will consume.

**Read first**:
- `frontend/src/services/api/types.ts` — existing types (AlertRule already defined)
- `frontend/src/services/api/client.ts` — apiGet/apiPost/apiPatch/apiDelete functions
- `frontend/src/services/api/alerts.ts` — existing pattern for API functions
- `frontend/src/hooks/use-alerts.ts` — existing TanStack Query hook pattern
- `frontend/src/services/auth/AuthProvider.tsx` — useAuth() context

---

## Task

### 1.1 Install additional shadcn components

The CRUD pages need form components that don't exist yet.

```bash
cd /home/opsconductor/simcloud/frontend
npx shadcn@latest add switch
npx shadcn@latest add label
npx shadcn@latest add textarea
```

### 1.2 Extend types.ts

**File**: `frontend/src/services/api/types.ts` (MODIFY)

Add the following types at the end of the file, after the existing TelemetryResponse interface:

```typescript
// Alert rule mutation types
export interface AlertRuleCreate {
  name: string;
  metric_name: string;
  operator: "GT" | "LT" | "GTE" | "LTE";
  threshold: number;
  severity?: number;
  description?: string | null;
  site_ids?: string[] | null;
  enabled?: boolean;
}

export interface AlertRuleUpdate {
  name?: string;
  metric_name?: string;
  operator?: "GT" | "LT" | "GTE" | "LTE";
  threshold?: number;
  severity?: number;
  description?: string | null;
  site_ids?: string[] | null;
  enabled?: boolean;
}

// Webhook integration types
export interface WebhookIntegration {
  integration_id: string;
  tenant_id: string;
  name: string;
  url: string;
  enabled: boolean;
  created_at: string;
}

export interface WebhookIntegrationCreate {
  name: string;
  webhook_url: string;
  enabled?: boolean;
}

export interface WebhookIntegrationUpdate {
  name?: string;
  webhook_url?: string;
  enabled?: boolean;
}

export interface WebhookListResponse {
  tenant_id: string;
  integrations: WebhookIntegration[];
}

// SNMP integration types
export interface SnmpIntegration {
  id: string;
  tenant_id: string;
  name: string;
  snmp_host: string;
  snmp_port: number;
  snmp_version: "2c" | "3";
  snmp_oid_prefix: string;
  enabled: boolean;
  created_at: string;
  updated_at: string;
}

export interface SnmpIntegrationCreate {
  name: string;
  snmp_host: string;
  snmp_port?: number;
  snmp_config: SnmpV2cConfig | SnmpV3Config;
  snmp_oid_prefix?: string;
  enabled?: boolean;
}

export interface SnmpV2cConfig {
  version: "2c";
  community: string;
}

export interface SnmpV3Config {
  version: "3";
  username: string;
  auth_protocol: "MD5" | "SHA" | "SHA224" | "SHA256" | "SHA384" | "SHA512";
  auth_password: string;
  priv_protocol?: "DES" | "AES" | "AES192" | "AES256";
  priv_password?: string;
}

export interface SnmpIntegrationUpdate {
  name?: string;
  snmp_host?: string;
  snmp_port?: number;
  snmp_config?: SnmpV2cConfig | SnmpV3Config;
  snmp_oid_prefix?: string;
  enabled?: boolean;
}

// Email integration types
export interface EmailIntegration {
  id: string;
  tenant_id: string;
  name: string;
  smtp_host: string;
  smtp_port: number;
  smtp_tls: boolean;
  from_address: string;
  recipient_count: number;
  template_format: "html" | "text";
  enabled: boolean;
  created_at: string;
  updated_at: string;
}

export interface EmailSmtpConfig {
  smtp_host: string;
  smtp_port?: number;
  smtp_user?: string | null;
  smtp_password?: string | null;
  smtp_tls?: boolean;
  from_address: string;
  from_name?: string | null;
}

export interface EmailRecipients {
  to: string[];
  cc?: string[];
  bcc?: string[];
}

export interface EmailTemplate {
  subject_template?: string;
  body_template?: string | null;
  format?: "html" | "text";
}

export interface EmailIntegrationCreate {
  name: string;
  smtp_config: EmailSmtpConfig;
  recipients: EmailRecipients;
  template?: EmailTemplate;
  enabled?: boolean;
}

export interface EmailIntegrationUpdate {
  name?: string;
  smtp_config?: EmailSmtpConfig;
  recipients?: EmailRecipients;
  template?: EmailTemplate;
  enabled?: boolean;
}

// MQTT integration types
export interface MqttIntegration {
  id: string;
  tenant_id: string;
  name: string;
  mqtt_topic: string;
  mqtt_qos: number;
  mqtt_retain: boolean;
  enabled: boolean;
  created_at: string;
  updated_at: string;
}

export interface MqttIntegrationCreate {
  name: string;
  mqtt_topic: string;
  mqtt_qos?: number;
  mqtt_retain?: boolean;
  enabled?: boolean;
}

export interface MqttIntegrationUpdate {
  name?: string;
  mqtt_topic?: string;
  mqtt_qos?: number;
  mqtt_retain?: boolean;
  enabled?: boolean;
}

// Test delivery response (shared across integration types)
export interface TestDeliveryResult {
  success: boolean;
  integration_id?: string;
  integration_name?: string;
  destination?: string;
  error?: string;
  duration_ms?: number;
  latency_ms?: number;
}

// Operator types
export interface AuditLogEntry {
  id: number;
  user_id: string;
  action: string;
  tenant_filter: string | null;
  resource_type: string | null;
  resource_id: string | null;
  ip_address: string;
  user_agent: string | null;
  rls_bypassed: boolean;
  created_at: string;
}

export interface AuditLogResponse {
  entries: AuditLogEntry[];
  limit: number;
  user_id: string | null;
  action: string | null;
  since: string | null;
}

export interface OperatorDevicesResponse {
  devices: Device[];
  tenant_filter: string | null;
  limit: number;
  offset: number;
}

export interface OperatorAlertsResponse {
  alerts: Alert[];
  tenant_filter: string | null;
  status: string;
  limit: number;
}

export interface QuarantineEvent {
  ingested_at: string;
  tenant_id: string;
  site_id: string | null;
  device_id: string;
  msg_type: string;
  reason: string;
}

export interface QuarantineResponse {
  minutes: number;
  events: QuarantineEvent[];
  limit: number;
}

export interface OperatorIntegrationsResponse {
  integrations: WebhookIntegration[];
  tenant_filter: string | null;
}
```

### 1.3 Create alert rules API functions

**File**: `frontend/src/services/api/alert-rules.ts` (NEW)

```typescript
import { apiGet, apiPost, apiPatch, apiDelete } from "./client";
import type {
  AlertRule,
  AlertRuleListResponse,
  AlertRuleCreate,
  AlertRuleUpdate,
} from "./types";

export async function fetchAlertRules(limit = 100): Promise<AlertRuleListResponse> {
  return apiGet(`/api/v2/alert-rules?limit=${limit}`);
}

export async function fetchAlertRule(ruleId: string): Promise<AlertRule> {
  return apiGet(`/customer/alert-rules/${encodeURIComponent(ruleId)}`);
}

export async function createAlertRule(data: AlertRuleCreate): Promise<AlertRule> {
  return apiPost("/customer/alert-rules", data);
}

export async function updateAlertRule(
  ruleId: string,
  data: AlertRuleUpdate
): Promise<AlertRule> {
  return apiPatch(`/customer/alert-rules/${encodeURIComponent(ruleId)}`, data);
}

export async function deleteAlertRule(ruleId: string): Promise<void> {
  return apiDelete(`/customer/alert-rules/${encodeURIComponent(ruleId)}`);
}
```

### 1.4 Create integrations API functions

**File**: `frontend/src/services/api/integrations.ts` (NEW)

```typescript
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
  return apiGet("/customer/integrations");
}

export async function createWebhook(data: WebhookIntegrationCreate): Promise<WebhookIntegration> {
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

export async function createSnmpIntegration(data: SnmpIntegrationCreate): Promise<SnmpIntegration> {
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

export async function testSnmpIntegration(id: string): Promise<TestDeliveryResult> {
  return apiPost(`/customer/integrations/snmp/${encodeURIComponent(id)}/test`, {});
}

// --- Email ---
export async function fetchEmailIntegrations(): Promise<EmailIntegration[]> {
  return apiGet("/customer/integrations/email");
}

export async function createEmailIntegration(data: EmailIntegrationCreate): Promise<EmailIntegration> {
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

export async function testEmailIntegration(id: string): Promise<TestDeliveryResult> {
  return apiPost(`/customer/integrations/email/${encodeURIComponent(id)}/test`, {});
}

// --- MQTT ---
export async function fetchMqttIntegrations(): Promise<MqttIntegration[]> {
  return apiGet("/customer/integrations/mqtt");
}

export async function createMqttIntegration(data: MqttIntegrationCreate): Promise<MqttIntegration> {
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

export async function testMqttIntegration(id: string): Promise<TestDeliveryResult> {
  return apiPost(`/customer/integrations/mqtt/${encodeURIComponent(id)}/test`, {});
}
```

### 1.5 Create operator API functions

**File**: `frontend/src/services/api/operator.ts` (NEW)

```typescript
import { apiGet, apiPost } from "./client";
import type {
  OperatorDevicesResponse,
  OperatorAlertsResponse,
  QuarantineResponse,
  OperatorIntegrationsResponse,
  AuditLogResponse,
} from "./types";

export async function fetchOperatorDevices(
  tenantFilter?: string,
  limit = 100,
  offset = 0
): Promise<OperatorDevicesResponse> {
  let url = `/operator/devices?limit=${limit}&offset=${offset}`;
  if (tenantFilter) url += `&tenant_filter=${encodeURIComponent(tenantFilter)}`;
  return apiGet(url);
}

export async function fetchOperatorAlerts(
  status = "OPEN",
  tenantFilter?: string,
  limit = 100
): Promise<OperatorAlertsResponse> {
  let url = `/operator/alerts?status=${status}&limit=${limit}`;
  if (tenantFilter) url += `&tenant_filter=${encodeURIComponent(tenantFilter)}`;
  return apiGet(url);
}

export async function fetchQuarantine(
  minutes = 60,
  limit = 100
): Promise<QuarantineResponse> {
  return apiGet(`/operator/quarantine?minutes=${minutes}&limit=${limit}`);
}

export async function fetchOperatorIntegrations(
  tenantFilter?: string
): Promise<OperatorIntegrationsResponse> {
  let url = "/operator/integrations";
  if (tenantFilter) url += `?tenant_filter=${encodeURIComponent(tenantFilter)}`;
  return apiGet(url);
}

export async function fetchAuditLog(
  userId?: string,
  action?: string,
  since?: string,
  limit = 100
): Promise<AuditLogResponse> {
  const params = new URLSearchParams();
  params.set("limit", String(limit));
  if (userId) params.set("user_id", userId);
  if (action) params.set("action", action);
  if (since) params.set("since", since);
  return apiGet(`/operator/audit-log?${params.toString()}`);
}

export async function updateOperatorSettings(data: {
  mode: string;
  store_rejects: string;
  mirror_rejects: string;
}): Promise<void> {
  // Backend expects form data for settings POST
  return apiPost("/operator/settings", data);
}
```

### 1.6 Create alert rules hook

**File**: `frontend/src/hooks/use-alert-rules.ts` (NEW)

```typescript
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  fetchAlertRules,
  createAlertRule,
  updateAlertRule,
  deleteAlertRule,
} from "@/services/api/alert-rules";
import type { AlertRuleCreate, AlertRuleUpdate } from "@/services/api/types";

export function useAlertRules(limit = 100) {
  return useQuery({
    queryKey: ["alert-rules", limit],
    queryFn: () => fetchAlertRules(limit),
  });
}

export function useCreateAlertRule() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: AlertRuleCreate) => createAlertRule(data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["alert-rules"] }),
  });
}

export function useUpdateAlertRule() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ ruleId, data }: { ruleId: string; data: AlertRuleUpdate }) =>
      updateAlertRule(ruleId, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["alert-rules"] }),
  });
}

export function useDeleteAlertRule() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (ruleId: string) => deleteAlertRule(ruleId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["alert-rules"] }),
  });
}
```

### 1.7 Create integrations hooks

**File**: `frontend/src/hooks/use-integrations.ts` (NEW)

```typescript
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
```

### 1.8 Create operator hooks

**File**: `frontend/src/hooks/use-operator.ts` (NEW)

```typescript
import { useQuery } from "@tanstack/react-query";
import {
  fetchOperatorDevices,
  fetchOperatorAlerts,
  fetchQuarantine,
  fetchAuditLog,
} from "@/services/api/operator";

export function useOperatorDevices(tenantFilter?: string, limit = 100, offset = 0) {
  return useQuery({
    queryKey: ["operator-devices", tenantFilter, limit, offset],
    queryFn: () => fetchOperatorDevices(tenantFilter, limit, offset),
  });
}

export function useOperatorAlerts(status = "OPEN", tenantFilter?: string, limit = 100) {
  return useQuery({
    queryKey: ["operator-alerts", status, tenantFilter, limit],
    queryFn: () => fetchOperatorAlerts(status, tenantFilter, limit),
  });
}

export function useQuarantine(minutes = 60, limit = 100) {
  return useQuery({
    queryKey: ["quarantine", minutes, limit],
    queryFn: () => fetchQuarantine(minutes, limit),
  });
}

export function useAuditLog(
  userId?: string,
  action?: string,
  since?: string,
  limit = 100
) {
  return useQuery({
    queryKey: ["audit-log", userId, action, since, limit],
    queryFn: () => fetchAuditLog(userId, action, since, limit),
  });
}
```

### 1.9 Update API index exports

**File**: `frontend/src/services/api/index.ts` (MODIFY)

Add exports for the new modules. Find the existing exports and add:

```typescript
export * from "./alert-rules";
export * from "./integrations";
export * from "./operator";
```

---

## Files to Create/Modify

| Action | Path | What |
|--------|------|------|
| MODIFY | `frontend/src/services/api/types.ts` | Add integration + operator types |
| CREATE | `frontend/src/services/api/alert-rules.ts` | Alert rule CRUD functions |
| CREATE | `frontend/src/services/api/integrations.ts` | Integration CRUD functions (4 types) |
| CREATE | `frontend/src/services/api/operator.ts` | Operator data fetch functions |
| CREATE | `frontend/src/hooks/use-alert-rules.ts` | Alert rule TanStack Query hooks |
| CREATE | `frontend/src/hooks/use-integrations.ts` | Integration TanStack Query hooks (4 types) |
| CREATE | `frontend/src/hooks/use-operator.ts` | Operator TanStack Query hooks |
| MODIFY | `frontend/src/services/api/index.ts` | Add new module exports |

---

## Test

### Step 1: Verify build

```bash
cd /home/opsconductor/simcloud/frontend && npm run build
```

### Step 2: Verify TypeScript

```bash
cd /home/opsconductor/simcloud/frontend && npx tsc --noEmit
```

### Step 3: Verify files exist

```bash
ls frontend/src/services/api/alert-rules.ts
ls frontend/src/services/api/integrations.ts
ls frontend/src/services/api/operator.ts
ls frontend/src/hooks/use-alert-rules.ts
ls frontend/src/hooks/use-integrations.ts
ls frontend/src/hooks/use-operator.ts
ls frontend/src/components/ui/switch.tsx
ls frontend/src/components/ui/label.tsx
ls frontend/src/components/ui/textarea.tsx
```

### Step 4: Verify backend tests

```bash
cd /home/opsconductor/simcloud && python3 -m pytest tests/unit/ -v -x
```

All 395 tests must pass.

---

## Acceptance Criteria

- [ ] shadcn switch, label, textarea components added
- [ ] Integration types defined for webhook, SNMP, email, MQTT
- [ ] Operator types defined for devices, alerts, quarantine, audit log
- [ ] Alert rule CRUD API functions (GET from /api/v2, mutations via /customer)
- [ ] Integration CRUD + test delivery API functions for all 4 types
- [ ] Operator API functions for devices, alerts, quarantine, audit log
- [ ] TanStack Query hooks with mutations for alert rules
- [ ] TanStack Query hooks with mutations for all 4 integration types
- [ ] Mutations invalidate query cache on success
- [ ] Operator query hooks for read-only data
- [ ] `npm run build` succeeds
- [ ] All Python tests pass

---

## Commit

```
Add API client layer for alert rules, integrations, and operator

Types, fetch functions, and TanStack Query hooks for alert
rule CRUD, webhook/SNMP/email/MQTT integration CRUD with
test delivery, and operator data endpoints.

Phase 21 Task 1: API Client Layer
```
