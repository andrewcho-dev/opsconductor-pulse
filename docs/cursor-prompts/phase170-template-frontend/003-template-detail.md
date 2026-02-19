# Task 3: Template Detail Page

## Create file: `frontend/src/features/templates/TemplateDetailPage.tsx`

Build a tabbed detail page for viewing and editing a device template.

### Component Structure

```
TemplateDetailPage
├── Page header
│   ├── Breadcrumb: Templates > {template.name}
│   ├── Source badge (System/Custom)
│   └── Edit button (if not locked)
├── Tabs
│   ├── Overview — template identity and config
│   ├── Metrics — DataTable of template_metrics
│   ├── Commands — DataTable of template_commands
│   └── Slots — DataTable of template_slots
```

### Data Fetching

```typescript
const { templateId } = useParams<{ templateId: string }>();
const { data: template, isLoading } = useQuery({
  queryKey: ["templates", Number(templateId)],
  queryFn: () => getTemplate(Number(templateId)),
});
```

### Tab 1: Overview

Display template fields in a card layout (2-column grid):
- **Name** / **Slug** / **Category** / **Source** / **Manufacturer** / **Model**
- **Description** (full width)
- **Firmware Version Pattern** / **Transport Defaults** (formatted JSON)
- **Image URL** (if present, show thumbnail)
- **Metadata** (formatted JSON)

If the template is editable (not locked, owned by tenant):
- "Edit" button → opens edit form (inline or Dialog)
- Edit form uses same fields as TemplateCreate but pre-populated

### Tab 2: Metrics

DataTable with columns:
| Column | Content |
|--------|---------|
| Sort Order | Number |
| Metric Key | `metric_key` |
| Display Name | `display_name` |
| Data Type | Badge |
| Unit | `unit` |
| Range | `{min_value} – {max_value}` |
| Required | Checkbox/icon |
| Actions | Edit, Delete (if editable) |

**Add Metric button**: Opens a dialog with form fields matching `TemplateMetricPayload`. On submit, calls `createTemplateMetric()` and invalidates the template query.

**Edit**: Opens same dialog pre-populated. Calls `updateTemplateMetric()`.

**Delete**: Confirmation dialog. Calls `deleteTemplateMetric()`.

If the template is locked (system), show the table as read-only (no Add/Edit/Delete buttons).

### Tab 3: Commands

DataTable with columns:
| Column | Content |
|--------|---------|
| Sort Order | Number |
| Command Key | `command_key` |
| Display Name | `display_name` |
| Description | Truncated |
| Parameters | "View Schema" button → Dialog showing JSON |
| Actions | Edit, Delete (if editable) |

**Add Command button**: Dialog with form fields. The `parameters_schema` and `response_schema` fields should use a JSON textarea (or a simple code editor).

### Tab 4: Slots

DataTable with columns:
| Column | Content |
|--------|---------|
| Sort Order | Number |
| Slot Key | `slot_key` |
| Display Name | `display_name` |
| Type | `slot_type` badge |
| Interface | `interface_type` badge |
| Max Devices | Number or "Unlimited" |
| Required | Checkbox/icon |
| Compatible | Count or list of template names |
| Actions | Edit, Delete (if editable) |

**Compatible Templates display**: For each ID in `compatible_templates`, show the template name. May need a secondary query or pre-fetched lookup from the templates list.

**Add Slot button**: Dialog with form fields. The `compatible_templates` field should be a multi-select picker showing available expansion_module templates.

### Locked Template Banner

If `template.is_locked`, show a banner at the top:
```
This is a system template and cannot be edited. Clone it to create a customizable copy.
[Clone Template] button
```

### Tab Component

Use the `Tabs`, `TabsList`, `TabsTrigger`, `TabsContent` components from `@/components/ui/tabs`.

```typescript
<Tabs defaultValue="overview">
  <TabsList>
    <TabsTrigger value="overview">Overview</TabsTrigger>
    <TabsTrigger value="metrics">Metrics ({template.metrics.length})</TabsTrigger>
    <TabsTrigger value="commands">Commands ({template.commands.length})</TabsTrigger>
    <TabsTrigger value="slots">Slots ({template.slots.length})</TabsTrigger>
  </TabsList>
  <TabsContent value="overview">...</TabsContent>
  <TabsContent value="metrics">...</TabsContent>
  <TabsContent value="commands">...</TabsContent>
  <TabsContent value="slots">...</TabsContent>
</Tabs>
```

## Verification

1. System template shows all data, read-only, with "Clone" banner
2. Tenant template shows all data with edit/add/delete controls
3. Adding a metric persists and table updates
4. Editing a slot updates the data
5. Deleting a command with confirmation works
