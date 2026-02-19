# Task 1: Template API Service Functions + Types

## Create file: `frontend/src/services/api/templates.ts`

Follow the exact patterns from `sensors.ts` — import `apiGet`, `apiPost`, `apiPut`, `apiDelete` from `./client`.

### TypeScript Types

Define these types either in `templates.ts` or in `types.ts` (follow whichever pattern the project uses — if types are centralized in `types.ts`, add them there):

```typescript
// ─── Template Types ────────────────────────────────────

export interface DeviceTemplate {
  id: number;
  tenant_id: string | null;
  name: string;
  slug: string;
  description: string | null;
  category: "gateway" | "edge_device" | "standalone_sensor" | "controller" | "expansion_module";
  manufacturer: string | null;
  model: string | null;
  firmware_version_pattern: string | null;
  is_locked: boolean;
  source: "system" | "tenant";
  transport_defaults: Record<string, unknown> | null;
  metadata: Record<string, unknown>;
  image_url: string | null;
  created_at: string;
  updated_at: string;
}

export interface TemplateMetric {
  id: number;
  template_id: number;
  metric_key: string;
  display_name: string;
  data_type: "float" | "integer" | "boolean" | "string" | "enum";
  unit: string | null;
  min_value: number | null;
  max_value: number | null;
  precision_digits: number;
  is_required: boolean;
  description: string | null;
  enum_values: string[] | null;
  sort_order: number;
}

export interface TemplateCommand {
  id: number;
  template_id: number;
  command_key: string;
  display_name: string;
  description: string | null;
  parameters_schema: Record<string, unknown> | null;
  response_schema: Record<string, unknown> | null;
  sort_order: number;
}

export interface TemplateSlot {
  id: number;
  template_id: number;
  slot_key: string;
  display_name: string;
  slot_type: "expansion" | "sensor" | "accessory";
  interface_type: string;
  max_devices: number | null;
  compatible_templates: number[] | null;
  is_required: boolean;
  description: string | null;
  sort_order: number;
}

export interface TemplateDetail extends DeviceTemplate {
  metrics: TemplateMetric[];
  commands: TemplateCommand[];
  slots: TemplateSlot[];
}

// ─── Create/Update payloads ────────────────────────────

export interface TemplateCreatePayload {
  name: string;
  slug: string;
  description?: string;
  category: string;
  manufacturer?: string;
  model?: string;
  firmware_version_pattern?: string;
  transport_defaults?: Record<string, unknown>;
  metadata?: Record<string, unknown>;
  image_url?: string;
}

export interface TemplateUpdatePayload {
  name?: string;
  description?: string;
  category?: string;
  manufacturer?: string;
  model?: string;
  firmware_version_pattern?: string;
  transport_defaults?: Record<string, unknown>;
  metadata?: Record<string, unknown>;
  image_url?: string;
}

// Similar Create/Update types for metrics, commands, slots...
export interface TemplateMetricPayload {
  metric_key: string;
  display_name: string;
  data_type: string;
  unit?: string;
  min_value?: number;
  max_value?: number;
  precision_digits?: number;
  is_required?: boolean;
  description?: string;
  enum_values?: string[];
  sort_order?: number;
}

export interface TemplateCommandPayload {
  command_key: string;
  display_name: string;
  description?: string;
  parameters_schema?: Record<string, unknown>;
  response_schema?: Record<string, unknown>;
  sort_order?: number;
}

export interface TemplateSlotPayload {
  slot_key: string;
  display_name: string;
  slot_type: string;
  interface_type: string;
  max_devices?: number;
  compatible_templates?: number[];
  is_required?: boolean;
  description?: string;
  sort_order?: number;
}
```

### API Functions

```typescript
const BASE = "/api/v1/customer/templates";

// ─── Templates ─────────────────────────────────────────

export async function listTemplates(params?: {
  category?: string;
  source?: string;
  search?: string;
}): Promise<DeviceTemplate[]> {
  const search = new URLSearchParams();
  if (params?.category) search.set("category", params.category);
  if (params?.source) search.set("source", params.source);
  if (params?.search) search.set("search", params.search);
  const qs = search.toString();
  return apiGet(`${BASE}${qs ? `?${qs}` : ""}`);
}

export async function getTemplate(templateId: number): Promise<TemplateDetail> {
  return apiGet(`${BASE}/${templateId}`);
}

export async function createTemplate(data: TemplateCreatePayload): Promise<DeviceTemplate> {
  return apiPost(BASE, data);
}

export async function updateTemplate(templateId: number, data: TemplateUpdatePayload): Promise<DeviceTemplate> {
  return apiPut(`${BASE}/${templateId}`, data);
}

export async function deleteTemplate(templateId: number): Promise<void> {
  return apiDelete(`${BASE}/${templateId}`);
}

export async function cloneTemplate(templateId: number): Promise<TemplateDetail> {
  return apiPost(`${BASE}/${templateId}/clone`, {});
}

// ─── Template Metrics ──────────────────────────────────

export async function createTemplateMetric(templateId: number, data: TemplateMetricPayload): Promise<TemplateMetric> {
  return apiPost(`${BASE}/${templateId}/metrics`, data);
}

export async function updateTemplateMetric(templateId: number, metricId: number, data: Partial<TemplateMetricPayload>): Promise<TemplateMetric> {
  return apiPut(`${BASE}/${templateId}/metrics/${metricId}`, data);
}

export async function deleteTemplateMetric(templateId: number, metricId: number): Promise<void> {
  return apiDelete(`${BASE}/${templateId}/metrics/${metricId}`);
}

// ─── Template Commands ─────────────────────────────────

export async function createTemplateCommand(templateId: number, data: TemplateCommandPayload): Promise<TemplateCommand> {
  return apiPost(`${BASE}/${templateId}/commands`, data);
}

export async function updateTemplateCommand(templateId: number, commandId: number, data: Partial<TemplateCommandPayload>): Promise<TemplateCommand> {
  return apiPut(`${BASE}/${templateId}/commands/${commandId}`, data);
}

export async function deleteTemplateCommand(templateId: number, commandId: number): Promise<void> {
  return apiDelete(`${BASE}/${templateId}/commands/${commandId}`);
}

// ─── Template Slots ────────────────────────────────────

export async function createTemplateSlot(templateId: number, data: TemplateSlotPayload): Promise<TemplateSlot> {
  return apiPost(`${BASE}/${templateId}/slots`, data);
}

export async function updateTemplateSlot(templateId: number, slotId: number, data: Partial<TemplateSlotPayload>): Promise<TemplateSlot> {
  return apiPut(`${BASE}/${templateId}/slots/${slotId}`, data);
}

export async function deleteTemplateSlot(templateId: number, slotId: number): Promise<void> {
  return apiDelete(`${BASE}/${templateId}/slots/${slotId}`);
}
```

## Verification

```bash
cd frontend && npx tsc --noEmit
# Should compile without errors
```
