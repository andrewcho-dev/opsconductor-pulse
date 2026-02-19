# Task 3: Frontend Cleanup

## Changes to make

### 1. Update Device List — Show Template Name

## Modify file: `frontend/src/features/devices/DeviceListPage.tsx`

In the device list table, replace the `device_type` column with `template_name`:

- Find the column definition for `device_type` (it may be labeled "Type" or "Device Type")
- Update it to use `device.template?.name` instead of `device.device_type`
- If template is null, show the legacy `device_type` as fallback: `device.template?.name ?? device.device_type ?? "—"`
- Update the column header from "Type" to "Template"

### 2. Remove MetricsPage from Router

## Modify file: `frontend/src/app/router.tsx`

The MetricsPage route should remain but redirect to templates:

```typescript
// Replace:
{ path: "metrics", element: <MetricsPage /> },
// With:
{ path: "metrics", element: <MetricsPage /> },  // Keep for now — has deprecation banner
```

Actually, keep the MetricsPage route alive for now since Task 3 of Phase 172 added a deprecation banner. Users who bookmarked it should still be able to access it. Just remove it from active navigation (sidebar).

### 3. Update Sidebar Links

## Modify file: `frontend/src/components/layout/AppSidebar.tsx`

**Remove** the "Metrics" link from the **Analytics** nav group. The MetricsPage is deprecated and the route still works if accessed directly, but it shouldn't be in the sidebar navigation.

Find the Analytics collapsible section and remove the Metrics entry:

```tsx
// Remove this entry:
{
  label: "Metrics",
  href: "/metrics",
  icon: BarChart3,  // or whatever icon
},
```

**Keep** the "Sensors" link in the Fleet group for now — it still works via the backward-compat view. However, consider marking it with a subtle indicator that the per-device sensors tab is the primary view now.

### 4. Remove SensorListPage from Sidebar (Optional)

If the fleet-wide SensorListPage at `/sensors` is superseded by per-device sensor management in the device detail Sensors & Data tab, consider:
- Keep the route (users may have bookmarked it)
- Remove from sidebar navigation
- Add a note at the top of SensorListPage: "Tip: Manage sensors per-device on the Sensors & Data tab of each device's detail page."

### 5. Update AddDeviceModal — Template Selector

## Modify file: `frontend/src/features/devices/AddDeviceModal.tsx`

Add a template selector to the device provisioning modal:

1. Add a `template_id` field to the provisioning form
2. Add a `Select` dropdown populated from `listTemplates()`
3. When a template is selected, show a preview of required metrics that will be auto-created
4. Pass `template_id` to `provisionDevice()` request

The template selector should:
- Show system templates first, then tenant templates
- Display category badge next to each option
- Allow "None" selection (no template) for maximum flexibility

### 6. Update DeviceOnboardingWizard — Template Step

## Modify file: `frontend/src/features/devices/wizard/Step1DeviceDetails.tsx`

If the onboarding wizard has a "Device Type" dropdown, replace it with a template selector:

1. Replace the free-text or limited dropdown with a template picker
2. Show template name, category, and metric count
3. Set `template_id` on the wizard form data

## Verification

```bash
# Build succeeds
cd frontend && npx tsc --noEmit && npm run build

# Verify sidebar
# - "Device Templates" appears in Fleet group (Phase 170)
# - "Metrics" removed from Analytics group
# - "Sensors" still in Fleet group

# Verify device list shows template names
# Verify MetricsPage is still accessible at /app/metrics (with deprecation banner)
# Verify AddDeviceModal has template selector
```
